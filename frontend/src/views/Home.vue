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
  },
  data() {
    return {
      colMdMin: 768
    }
  },
  mounted() {
    var titleElems = document.getElementsByClassName('feature-title')
    for (var i = 0; i < titleElems.length; i++) {
      if (window.innerWidth < this.colMdMin) {
        titleElems[i].style.padding = '20px' // スマホ画面
      } else {
        titleElems[i].style.padding = '40px'
      }
    }

    var resultElems = document.getElementsByClassName('result-region')
    for (i = 0; i < resultElems.length; i++) {
      if (window.innerWidth < this.colMdMin) {
        resultElems[i].style.padding = '0' // スマホ画面
      } else {
        resultElems[i].style.padding = '15px'
      }
    }
  }
}
</script>

<style>
.feature-block {
  background-color: #eee;
}

.feature-title {
  text-align: left;
}
.icon-title {
  width: 3rem;
  margin-right: 1rem;
  /* vertical-align: middle; */
}
.icon-title-bs {
  vertical-align: middle;
  font-size: 1.3em;
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
