<template>
  <div class="home-page">
    <nav class="navbar navbar-expand-lg navbar-light bg-light fixed-top">
      <div class="container-fluid">
        <a class="navbar-brand" href="#"
          ><img
            src="@/assets/crover_logo_3leaf_rgb.png"
            alt="crover_logo"
            width="80"
        /></a>
        <button
          class="navbar-toggler"
          type="button"
          data-bs-toggle="collapse"
          data-bs-target="#navbarScroll"
          aria-controls="navbarScroll"
          aria-expanded="false"
          aria-label="Toggle navigation"
        >
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarScroll">
          <ul
            class="navbar-nav me-auto my-2 my-lg-0 navbar-nav-scroll"
            style="--bs-scroll-height: 100px"
          >
            <!-- emotion analysis -->
            <li class="nav-item">
              <a
                class="nav-link"
                data-toggle="tab"
                href="#emotion"
                role="tab"
                aria-selected="true"
                @click="clickEmotionNav()"
                >Emotion</a
              >
            </li>
            <!-- network graph -->
            <li class="nav-item">
              <a
                class="nav-link"
                data-toggle="tab"
                href="#network"
                role="tab"
                aria-selected="true"
                @click="clickNetworkNav()"
                >Network</a
              >
            </li>
          </ul>
        </div>
      </div>
    </nav>

    <!-- コンテンツ -->
    <about-block />
    <emotion-block id="emotion-block-id" />
    <network-block id="network-block-id" />
  </div>
</template>

<script>
import AboutBlock from './About.vue'
import EmotionBlock from './Emotion.vue'
import NetworkBlock from './Network.vue'
export default {
  name: 'home-page',
  components: {
    AboutBlock,
    EmotionBlock,
    NetworkBlock
  },
  data() {
    return {
      colMdMin: 768,
      aboutElem: null,
      emotionBlockElem: null,
      networkBlockElem: null,
      navbarHeight: 0,
      titleElems: null
    }
  },
  mounted() {
    this.navbarHeight =
      document.getElementsByClassName('navbar')[0].clientHeight
    document.body.style.paddingTop = String(this.navbarHeight) + 'px'

    this.aboutElem = document.getElementsByClassName('about-block')[0]
    if (window.innerWidth < this.colMdMin) {
      this.aboutElem.style.padding = '0 20px 0 20px' // スマホ画面
    } else {
      this.aboutElem.style.padding = '0 40px 0 40px'
    }

    this.emotionBlockElem = document.getElementById('emotion-block-id')
    this.networkBlockElem = document.getElementById('network-block-id')

    this.titleElems = document.getElementsByClassName('feature-title')
    for (var i = 0; i < this.titleElems.length; i++) {
      if (window.innerWidth < this.colMdMin) {
        this.titleElems[i].style.padding = '20px' // スマホ画面
      } else {
        this.titleElems[i].style.padding = '40px'
      }
    }
  },
  methods: {
    clickEmotionNav() {
      window.scrollTo({
        top: this.emotionBlockElem.offsetTop - this.navbarHeight
      })
    },
    clickNetworkNav() {
      window.scrollTo({
        top: this.networkBlockElem.offsetTop - this.navbarHeight
      })
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
.icon-help {
  vertical-align: middle;
  font-size: 1.3em;
  color: royalblue;
  font-weight: bold;
}
.help-caption {
  position: absolute;
  color: white;
  background-color: rgb(75, 75, 75);
  padding: 10px;
  border-radius: 10px;
  opacity: 0.9;
  z-index: 100;
}
.input-form {
  border-radius: 10px;
  margin-right: 3rem;
}

.result-region {
  background-color: #fff;
  border-radius: 10px;
  margin: 15px 0 0 0;
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
