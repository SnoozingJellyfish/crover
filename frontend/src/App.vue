<template>
  <div id="app">
    <home-view />
    <!--
    <router-view></router-view>
    -->
  </div>
</template>

<script>
import HomeView from './views/Home.vue'
export default {
  name: 'app',
  components: { HomeView },
  data() {
    return {
      activeIndex: this.$route.name,
      emotionBlockElem: null
    }
  }
}
</script>

<style>
#app {
  font-family: 'Avenir', Helvetica, Arial, sans-serif;
  text-align: center;
  color: #2c3e50;
}
a {
  text-decoration: none;
}
</style>
