<template>
  <div class="home-page">
    <about-view></about-view>
  </div>
</template>

<script>
import AboutView from './About.vue'
export default {
  name: 'home-page',
  components: {
    AboutView
  }
}
</script>
