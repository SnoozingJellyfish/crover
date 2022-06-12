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
</style>
