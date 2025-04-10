<template>
  <div
    v-if="loaded"
    style="height: 100%;"
  >
    <TaskPlayer :id="id" />
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
  computed: {
  },
  methods: {
  }
}
</script>

<style scoped>
</style>