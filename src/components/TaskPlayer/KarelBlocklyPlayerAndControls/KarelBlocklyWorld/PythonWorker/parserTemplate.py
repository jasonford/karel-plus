"""
Python AST parser to generate JavaScript code compatible with Karel.
"""

import ast
import copy
from inspect import getmembers, isfunction
import sys
import traceback
from types import ModuleType

from js import blocks
limits = blocks.to_py()
for key in limits:
    limits[key]['count'] = 0


class KarelError(Exception):
    def __init__(self, message, lineno):
        super().__init__(message)
        self.lineno = lineno


# Provide karel module
karel_code = '''
### KAREL_FUNCS ###
'''
sys.modules['karel'] = None
mod = ModuleType('karel')
exec(karel_code, mod.__dict__)
sys.modules['karel'] = mod

import karel
karel_functions = getmembers(karel, isfunction)

python_code = '''
### KAREL_CODE ###
'''

bool_ops = {
    ast.And: '&&',
    ast.Or: '||',
    ast.Not: '!'
}

bool_comps = {
    ast.Lt: '<',
    ast.LtE: '<=',
    ast.Eq: '===',
    ast.NotEq: '!==',
    ast.Gt: '>',
    ast.GtE: '>=',
}

bin_ops = {
    ast.Add: '+',
    ast.Sub: '-',
    ast.Mult: '*',
    ast.Div: '/',
    ast.Mod: '%',
    ast.Pow: '**',
    ast.FloorDiv: '//',
}

reserved_functions = ['karel_main', 'done', 'highlight', 'step', 'appendText']


def check_limit(name, display_name, lineno):
    if name in limits:
        if not limits[name]['active']:
            raise KarelError(f'You are not allowed to use {display_name} in this problem.', lineno)
        
        limits[name]['count'] += 1
        if limits[name]['limit'] >= 0 and limits[name]['count'] > limits[name]['limit']:
            raise KarelError(f'You have exceeded the number of {display_name} allowed in this problem ({limits[name]['limit']}).', lineno)


def parse_rec(node, context, indent):
    indent_str = '  ' * indent

    # Module
    if isinstance(node, ast.Module):
        for child in node.body:
            parse_rec(child, context, indent)

    # Import
    elif isinstance(node, ast.Import):
        pass

    # Import from
    elif isinstance(node, ast.ImportFrom):
        pass

    # Function definition
    elif isinstance(node, ast.FunctionDef):
        check_limit('karel_define', 'functions', node.lineno)

        if node.name in reserved_functions:
            raise KarelError(f'Function {node.name} is reserved', node.lineno)

        for function in context['functions']:
            if function == node.name:
                raise KarelError(f'Function {node.name} is already defined', node.lineno)
        else: 
            context['functions'].append(node.name)

        # Function header
        context['code'] += indent_str
        context['code'] += f'async function {node.name} ('
        for i, arg in enumerate(node.args.args):
            context['code'] += arg.arg
            if i != len(node.args.args) - 1:
                context['code'] += ', '
        context['code'] += ') {\n'

        # Function body
        for child in node.body:
            parse_rec(child, context, indent + 1)

        # Function end
        context['code'] += indent_str
        context['code'] += '}\n'

    # While loop
    elif isinstance(node, ast.While):
        check_limit('karel_while', 'while loops', node.lineno)

        # While loop header
        context['code'] += indent_str
        context['code'] += 'while ('
        parse_rec(node.test, context, 0)
        context['code'] += ') {\n'

        # While loop body
        for child in node.body:
            parse_rec(child, context, indent + 1)

        # While loop end
        context['code'] += indent_str
        context['code'] += '}\n'

        if node.orelse:
            raise KarelError('While-Else is not supported in JavaScript', node.lineno)

    # For loop
    elif isinstance(node, ast.For):
        check_limit('karel_repeat', 'for loops', node.lineno)

        # For loop header
        context['code'] += indent_str
        context['code'] += 'for ('
        if not isinstance(node.iter, ast.Call) or not isinstance(node.iter.func, ast.Name) or node.iter.func.id != 'range':
            raise KarelError('Only range function is supported in JavaScript', node.lineno)
        context['code'] += f'let {node.target.id} = 0; {node.target.id} < {node.iter.args[0].id if isinstance(node.iter.args[0], ast.Name) else node.iter.args[0].value}; {node.target.id}++) '
        context['code'] += '{\n'

        context['code'] += indent_str
        context['code'] += f'highlight({node.lineno - 1});\n'
        context['code'] += indent_str
        context['code'] += 'await step();\n'

        # For loop body
        for child in node.body:
            parse_rec(child, context, indent + 1)

        # For loop end
        context['code'] += indent_str
        context['code'] += '}\n'

        if node.orelse:
            raise KarelError('For-Else is not supported in JavaScript', node.lineno)

    # If-Else
    elif isinstance(node, ast.If):
        check_limit('karel_ifelse', 'if-else statements', node.lineno)

        # If header
        context['code'] += indent_str
        context['code'] += 'if ('
        parse_rec(node.test, context, 0)
        context['code'] += ') {\n'

        # If body
        for child in node.body:
            parse_rec(child, context, indent + 1)

        # If end
        context['code'] += indent_str
        context['code'] += '}\n'

        # Else
        if node.orelse:
            # Else header
            context['code'] += indent_str
            context['code'] += 'else {\n'

            # Else body
            for child in node.orelse:
                parse_rec(child, context, indent + 1)

            # Else end
            context['code'] += indent_str
            context['code'] += '}\n'

    # Boolean operations
    elif isinstance(node, ast.BoolOp):
        context['code'] += '('
        parse_rec(node.values[0], context, 0)
        context['code'] += f' {bool_ops[type(node.op)]} '
        parse_rec(node.values[1], context, 0)
        context['code'] += ')'

    # Comparison operations
    elif isinstance(node, ast.Compare):
        context['code'] += '('
        parse_rec(node.left, context, 0)
        context['code'] += f' {bool_comps[type(node.ops[0])]} '
        parse_rec(node.comparators[0], context, 0)
        context['code'] += ')'

    # Unary operations
    elif isinstance(node, ast.UnaryOp):
        context['code'] += '('
        context['code'] += f'{bool_ops[type(node.op)]}'
        context['code'] += '('
        parse_rec(node.operand, context, 0)
        context['code'] += ')'
        context['code'] += ')'

    # Variable
    elif isinstance(node, ast.Name):
        if node.id not in context['variables']:
            context['code'] += node.id
        else:
            context['code'] += f'karel.variables["{node.id}"].value'

    # Expression
    elif isinstance(node, ast.Expr):
        context['code'] += indent_str
        parse_rec(node.value, context, 0)
        context['code'] += ';\n'

        context['code'] += indent_str
        context['code'] += f'highlight({node.lineno - 1});\n'
        context['code'] += indent_str
        context['code'] += 'await step();\n'

    # Assignment
    elif isinstance(node, ast.Assign):
        context['code'] += indent_str

        variable_name = node.targets[0].id

        if not variable_name in context['variables']:
            context['variables'].append(variable_name)

        context['code'] += f'if (karel.variables["{variable_name}"]) {{\n'

        context['code'] += indent_str + '  '
        context['code'] += f'karel.variables["{variable_name}"].value = '
        parse_rec(node.value, context, 0)
        context['code'] += ';\n'

        context['code'] += indent_str
        context['code'] += '} else {\n'

        context['code'] += indent_str + '  '
        context['code'] += f'karel.variables["{variable_name}"] = {{ value: '
        parse_rec(node.value, context, 0)
        context['code'] += ', func: "" };\n'

        context['code'] += indent_str
        context['code'] += '}\n'

        context['code'] += indent_str
        context['code'] += f'highlight({node.lineno - 1});\n'
        context['code'] += indent_str
        context['code'] += 'await step();\n'

    # Augment assignment
    elif isinstance(node, ast.AugAssign):
        context['code'] += indent_str
        context['code'] += f'karel.variables["{node.target.id}"].value {bin_ops[type(node.op)]}= '
        parse_rec(node.value, context, 0)
        context['code'] += ';\n'

        context['code'] += indent_str
        context['code'] += f'highlight({node.lineno - 1});\n'
        context['code'] += indent_str
        context['code'] += 'await step();\n'

    # Binary operations
    elif isinstance(node, ast.BinOp):
        context['code'] += '('
        parse_rec(node.left, context, 0)
        context['code'] += f' {bin_ops[type(node.op)]} '
        parse_rec(node.right, context, 0)
        context['code'] += ')'

    # Attribute
    elif isinstance(node, ast.Attribute):
        parse_rec(node.value, context, 0)
        context['code'] += f'.{node.attr}'

    # Function call
    elif isinstance(node, ast.Call):
        contextCopy = copy.deepcopy(context)
        contextCopy['code'] = ''
        parse_rec(node.func, contextCopy, 0)

        has_await = False
        if contextCopy['code'] == 'print':
            pass
        else:
          for function in context['functions']:
              if function == contextCopy['code']:
                  has_await = True
                  break
          else:
              for function in karel_functions:
                  if function[0] == contextCopy['code'][6:]:
                      break
              else:
                raise KarelError(f'Function {contextCopy['code']} is not defined', node.lineno)

        context['code'] += '('
        if has_await:
            context['code'] += 'await '

        if contextCopy['code'] == 'print':
            context['code'] += 'appendText(`'
            for i, arg in enumerate(node.args):
                context['code'] += '${'
                parse_rec(arg, context, 0)
                context['code'] += '}'
                if i != len(node.args) - 1:
                    context['code'] += ' '
            context['code'] += '\\n`)'
        else:
          context['code'] += f'{contextCopy['code']}('
          for i, arg in enumerate(node.args):
              parse_rec(arg, context, 0)
              if i != len(node.args) - 1:
                  context['code'] += ', '
          context['code'] += ')'

        context['code'] += ')'

    # Constant
    elif isinstance(node, ast.Constant):
        if not isinstance(node.value, int):
            raise KarelError('Constants other than integers are not supported in Karel', node.lineno)
        context['code'] += str(node.value)

    # Pass
    elif isinstance(node, ast.Pass):
        pass

    else:
        raise KarelError(f'Unsupported node type: {type(node)}', node.lineno)


results = {}
try:
    tree = compile(python_code, filename='<string>', mode='exec', flags=ast.PyCF_ONLY_AST)
    # exec(python_code)

    context = {
        'code': '',
        'variables': [],
        'functions': []
    }
    context['code'] += 'async function karel_main() {\n try{'
    parse_rec(tree, context, 1)
    context['code'] += '} catch(e) {karel.error = e.message;}\n}\nkarel_main().then(done);'

    results['type'] = 'success'
    results['code'] = context['code']

except KarelError as e:
    results['type'] = 'error'
    results['message'] = e.args[0]
    results['line'] = e.lineno - 1

except SyntaxError as e:
    results['type'] = 'error'
    results['message'] = e.msg
    results['line'] = e.lineno - 1

except Exception as e:
    exc_type, exc_obj, exc_tb = sys.exc_info()
    lineno = traceback.extract_tb(exc_tb)[-1][1] - 1

    results['type'] = 'error'
    results['message'] = str(e)
    results['line'] = lineno

print(results)
results
