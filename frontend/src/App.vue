<template>
  <div id="app">
    <nav class="navbar navbar-expand-md navbar-light bg-light">
      <div class="container-fluid">
        <a class="navbar-brand">
          <img
            src="@/assets/crover_logo_3leaf_rgb.png"
            alt="crover_logo"
            width="80"
        /></a>
        <button
          class="navbar-toggler"
          type="button"
          data-toggle="collapse"
          data-target="#navbarNav"
          aria-controls="navbarNav"
          aria-expanded="false"
          aria-label="Toggle navigation"
        >
          <span class="navbar-toggler-icon"></span>
        </button>

        <div class="collapse navbar-collapse" id="navbarNav">
          <ul class="navbar-nav mr-auto">
            <!-- About -->
            <li class="nav-item">
              <a class="nav-link" href="/about">About</a>
            </li>
            <!-- emotion analysis -->
            <li class="nav-item">
              <a class="nav-link" href="#">Emotion</a>
            </li>
            <!-- network graph -->
            <li class="nav-item">
              <a class="nav-link" href="#">Network</a>
            </li>
          </ul>
        </div>
      </div>
    </nav>
    <router-view></router-view>
  </div>
</template>

<script>
export default {
  name: 'app',
  data() {
    return {
      activeIndex: this.$route.name
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
