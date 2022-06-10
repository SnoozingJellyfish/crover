<template>
  <div class="home-page">
    <about-block></about-block>
    <emotion-block></emotion-block>
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
  padding: 3rem 1rem 1rem 3rem;
}
</style>
