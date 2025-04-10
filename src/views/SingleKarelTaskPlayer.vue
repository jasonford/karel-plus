<template>
  <div
    v-if="loaded"
    style="height: 100%;"
  >
    <TaskPlayer
      :id="id"
      @taskCorrect="onTaskCorrect"
    />
  </div>
  <div v-else>
    loading...
  </div>
</template>

<script>
import TaskPlayer from '../components/TaskPlayer/index.vue'

export default {
  name: 'SingleKarelTaskPlayer',
  components: {
    TaskPlayer
  },
  props: {
    id: String
  },
  mounted() {
    this
      .$store
      .dispatch('loadContentById', this.id)
      .then(() => this.loaded = true)
  },
  data() {
    return {
      loaded: false
    }
  },
  methods: {
    onTaskCorrect() {
      Agent.close({ success: true })
    }
  }
}
</script>

<style scoped>
</style>