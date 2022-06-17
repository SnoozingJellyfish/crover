<template>
  <div class="home-page">
    <about-block />
    <emotion-block />
  </div>
</template>

<script>
import AboutBlock from './About.vue'
import EmotionBlock from './Emotion.vue'
export default {
  name: 'home-page',
  components: {
    AboutBlock,
    EmotionBlock
  }
}
</script>

<style>
.feature-block {
  background-color: #eee;
}

.feature-title {
  text-align: left;
  padding: 2rem 3rem 3rem 3rem;
}
.icon-title {
  width: 3rem;
  margin-right: 1rem;
}
.input-form {
  border-radius: 10px;
  margin-right: 3rem;
}

.result-region {
  background-color: #fff;
  border-radius: 10px;
}

.topSlide {
  transition: height 0.3s ease-in-out;
  overflow: hidden;
}

.topSlide-enter-active {
  animation-duration: 0.3s;
  animation-fill-mode: both;
}

.topSlide-leave-active {
  animation-duration: 0.3s;
  animation-fill-mode: both;
}

.spinner {
  width: 15px;
  margin: 0 auto;
  transform: rotate(-90deg);
}
</style>
