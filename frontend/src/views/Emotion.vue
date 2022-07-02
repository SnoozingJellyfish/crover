<template>
  <div id="emotion-block">
    <div class="feature-block">
      <div class="feature-title">
        <h2><fa icon="face-meh" class="icon-title"></fa>感情分析</h2>
        キーワードを含むツイートの感情と、一緒にツイートされている言葉を調べる
        <div class="row">
          <div class="form-group col-lg-3 col-md-5 col-sm-6 col-xs-12">
            <input
              type="text"
              class="form-control input-form"
              id="InputWord"
              name="keyword"
              placeholder="キーワード"
              v-model="keyword"
              required
            />
          </div>
          <div class="form-group col-xl-1 col-md-2 col-sm-3 col-4">
            <select
              class="form-control input-form"
              id="TweetNum"
              name="tweet_num"
              v-model="tweetNum"
            >
              <option selected>500</option>
              <option>1000</option>
              <option>2000</option>
            </select>
          </div>
          <div class="form-group col-lg-1 col-md-2 col-sm-2 col-4">
            <label for="TweetNum" class="col-form-label">ツイート</label>
          </div>
          <div class="form-group col-lg-1 col-md-3 col-sm-2 col-4 d-grid">
            <button
              type="button"
              class="btn btn-primary"
              @click="searchAnalyze(keyword, tweetNum)"
            >
              探す
            </button>
          </div>
        </div>

        <label class="trend-label"> 今のトレンド </label>
        <button
          v-for="t in trend"
          v-bind:key="t"
          @click="keyword = t"
          type="button"
          class="btn btn-outline-primary trend-button mb-3 ml-1 mr-1"
        >
          {{ t }}
        </button>
        <br />

        <transition
          name="topSlide"
          @before-enter="beforeEnter"
          @enter="enter"
          @before-leave="beforeLeave"
          @leave="leave"
        >
          <div class="topSlide result-region" v-show="isOpen">
            <pulse-loader
              :loading="!isSpinner"
              :color="spinnerColor"
              :size="spinnerSize"
              class="spinner"
            />
            <div v-if="isSpinner">
              <vue-d3-cloud
                :data="topicWord"
                :fontSizeMapper="fontSizeMapper"
                :width="cloudWH"
                :height="cloudWH"
                :font="'Noto Sans JP'"
                :colors="cloudColor"
                :padding="5"
                class="cloud-region"
              />
              <Bar
                :chart-options="chartOptions"
                :chart-data="tweetedTime"
                :width="barChartW"
                :height="barChartH"
                class="tweeted-time-chart"
              />
            </div>
          </div>
        </transition>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
import PulseLoader from 'vue-spinner/src/PulseLoader.vue'
import { Openable } from './util'
import VueD3Cloud from './VueD3Cloud.vue'
import { Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  BarElement,
  CategoryScale,
  LinearScale
} from 'chart.js'

ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale)

export default {
  components: { PulseLoader, VueD3Cloud, Bar },
  mixins: [Openable],
  name: 'emotion-block',
  data() {
    return {
      isOpen: false,
      trend: '',
      keyword: '',
      tweetNum: 500,
      isSpinner: true,
      spinnerColor: '#999',
      spinnerSize: '15px',
      topicWord: [],
      tweet: [],
      wordcloudColor: ['#1f77b4'],
      wcMargin: { top: 10, right: 5, bottom: 15, left: 15 },
      wcRotate: { from: 0, to: 0, numOfOrientation: 1 },
      fontSizeMapper: (word) => Math.log2(word.value) * 10,
      cloudColor: ['navy'],
      cloudWH: '600',
      tweetedTime: {},
      chartOptions: {
        responsive: true,
        plugins: {
          legend: {
            display: false
          }
        },
        scales: {
          x: {
            grid: {
              display: false
            }
          }
        }
      },
      barChartW: 10,
      barChartH: 5
    }
  },
  mounted() {
    axios.get('/trend').then((response) => (this.trend = response.data))
    console.log(this.trend)
    const relativeCloudWH = window.innerWidth * 0.65

    if (relativeCloudWH < 600) {
      this.cloudWH = String(relativeCloudWH)
    }
  },
  methods: {
    searchAnalyze(keyword, tweetNum) {
      this.isOpen = true
      axios.get('/search_analyze').then((response) => {
        this.topicWord = response.data.topicWord
        // this.tweet = response.tweet
        this.tweetedTime = response.data.tweetedTime
      })
    },
    wordClickHandler(name, value, vm) {
      console.log('wordClickHandler', name, value, vm)
    }
  }
}
</script>

<style scoped>
.trend-label {
  font-size: 1rem;
  margin: 1rem 2rem 0rem 0rem;
}
.trend-button {
  margin: 0.8rem 1rem 0rem 0rem;
}
.cloud-region {
  background-color: #fff;
  border-radius: 10px;
  width: 65vw;
  height: 65vw;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
  margin: 2rem;
  text-align: center;
  max-width: 600px;
  max-height: 600px;
}
.tweeted-time-chart {
  width: 25vw;
  height: 25vw;
}
</style>

<style></style>
