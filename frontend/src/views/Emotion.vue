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
        <!--
        <transition
          name="topSlide"
          @before-enter="beforeEnter"
          @enter="enter"
          @before-leave="beforeLeave"
          @leave="leave"
        >-->
        <div class="topSlide result-region" v-show="isOpen">
          <pulse-loader
            :loading="!isSpinner"
            :color="spinnerColor"
            :size="spinnerSize"
            class="spinner"
          />

          <div v-if="isSpinner">
            <div class="row">
              <div class="col-md-6 col-12" id="topicCloud">
                <div class="chart-caption">
                  「{{ searchKeyword }}」と一緒に呟かれている言葉
                </div>
                <vue-d3-cloud
                  :data="topicWord"
                  :fontSizeMapper="fontSizeMapper"
                  :width="topicCloudSize"
                  :height="topicCloudSize"
                  :font="'Noto Sans JP'"
                  :colors="topicCloudColor"
                  :padding="5"
                />
              </div>

              <div class="col-md-6 col-12">
                <div class="row">
                  <div class="col-12">
                    <div class="chart-caption">ツイート数</div>
                    <Bar
                      :chart-options="tweetedTimeOptions"
                      :chart-data="tweetedTime"
                      :width="topicCloudSize"
                      :height="tweetedTimeHeight"
                      class="tweeted-time-chart"
                    />
                  </div>

                  <div class="col-md-6 col-12">
                    <div class="chart-caption">ツイート割合</div>
                    <Pie
                      :chart-options="emotionRatioOptions"
                      :chart-data="emotionRatio"
                      class="emotion-ratio-chart"
                      :style="{
                        width: emotionRatioWidth + 'px',
                        height: emotionRatioHeight + 'px'
                      }"
                    />
                  </div>
                  <div class="col-md-6 col-12">
                    <div class="chart-caption">感情ワード</div>
                    <vue-d3-cloud
                      :data="emotionWord"
                      :fontSizeMapper="fontSizeMapper"
                      :width="emotionCloudWidth"
                      :height="emotionCloudWidth"
                      :font="'Noto Sans JP'"
                      :colors="emotionCloudColor"
                      :padding="5"
                    />
                  </div>
                </div>
              </div>
            </div>
            <ul
              class="nav nav-justified emotion-table"
              id="myTab"
              role="tablist"
            >
              <li class="nav-item">
                <a
                  class="nav-link active tab-positive"
                  id="positive-tab"
                  data-toggle="tab"
                  href="#home"
                  role="tab"
                  aria-controls="home"
                  aria-selected="true"
                  >ポジティブ</a
                >
              </li>
              <li class="nav-item">
                <a
                  class="nav-link tab-neutral"
                  id="neutral-tab"
                  data-toggle="tab"
                  href="#profile"
                  role="tab"
                  aria-controls="profile"
                  aria-selected="false"
                  >ニュートラル</a
                >
              </li>
              <li class="nav-item">
                <a
                  class="nav-link tab-negative"
                  id="negative-tab"
                  data-toggle="tab"
                  href="#contact"
                  role="tab"
                  aria-controls="contact"
                  aria-selected="false"
                  >ネガティブ</a
                >
              </li>
            </ul>
          </div>
        </div>
        <!--</transition>-->
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
import PulseLoader from 'vue-spinner/src/PulseLoader.vue'
import { Openable } from './util'
import VueD3Cloud from './VueD3Cloud.vue'
import 'chart.js/auto'
import { Bar, Pie } from 'vue-chartjs'
/*
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  BarElement,
  ArcElement,
  CategoryScale,
  LinearScale
} from 'chart.js'

ChartJS.register(
  Title,
  Tooltip,
  Legend,
  BarElement,
  ArcElement,
  CategoryScale,
  LinearScale
)
*/

export default {
  components: { PulseLoader, VueD3Cloud, Bar, Pie },
  // components: { PulseLoader, VueD3Cloud },
  mixins: [Openable],
  name: 'emotion-block',
  data() {
    return {
      isOpen: false,
      trend: '',
      keyword: '',
      searchKeyword: '',
      tweetNum: 500,
      isSpinner: true,
      spinnerColor: '#999',
      spinnerSize: '15px',
      topicWord: [],
      emotionWord: [],
      tweet: [],
      fontSizeMapper: (word) => Math.log2(word.value) * 10,
      topicCloudColor: ['navy'],
      emotionCloudColor: ['darkgreen'],
      tweetedTime: {},
      tweetedTimeOptions: {
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
            },
            ticks: {
              // font: { size: 13 }
            }
          }
        }
      },
      barChartW: 10,
      barChartH: 3,
      emotionRatio: {},
      emotionRatioOptions: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { reverse: true, display: false }
          // legend: { reverse: true, labels: { font: { size: 15 } } }
        }
      },
      currentWindowWidth: 0,
      colMdMin: 768
    }
  },
  computed: {
    // eslint-disable-next-line
    topicCloudSize: function () {
      if (this.currentWindowWidth < this.colMdMin) {
        return String(this.currentWindowWidth - 140)
      } else {
        return String(Number(this.currentWindowWidth / 2) - 140)
      }
    },
    // eslint-disable-next-line
    tweetedTimeHeight: function () {
      if (this.currentWindowWidth < this.colMdMin) {
        return String(Number(this.topicCloudSize) / 2)
      } else {
        return String(Number(this.topicCloudSize) / 3)
      }
    },
    // eslint-disable-next-line
    emotionRatioWidth: function () {
      if (this.currentWindowWidth < this.colMdMin) {
        return this.topicCloudSize
      } else {
        return String(Number(this.currentWindowWidth / 4) - 50)
      }
    },
    // eslint-disable-next-line
    emotionRatioHeight: function () {
      return String(Number(this.emotionRatioWidth) - 100)
    },
    // eslint-disable-next-line
    emotionCloudWidth: function () {
      if (this.currentWindowWidth < this.colMdMin) {
        return this.topicCloudSize
      } else {
        return String(Number(this.currentWindowWidth / 4) - 140)
      }
    }
  },
  mounted() {
    axios.get('/trend').then((response) => (this.trend = response.data))
    console.log(this.trend)
    this.currentWindowWidth = window.innerWidth
    window.addEventListener('resize', () => {
      this.currentWindowWidth = window.innerWidth
    })
  },
  methods: {
    searchAnalyze(keyword, tweetNum) {
      this.isOpen = true
      axios.get('/search_analyze').then((response) => {
        this.searchKeyword = this.keyword
        this.topicWord = response.data.topicWord
        // this.tweet = response.tweet
        this.tweetedTime = response.data.tweetedTime
        this.emotionRatio = response.data.emotionRatio
        this.emotionWord = response.data.emotionWord
      })
      this.topic_cloud_w = document.getElementById('topicCloud').style.maxWidth
      this.topic_cloud_h = document.getElementById('topicCloud').style.maxHeight
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
.chart-caption {
  font-size: 1.3rem;
  margin: 30px;
  text-align: left;
}
.tweeted-time-chart {
  margin: 30px;
}
.emotion-ratio-chart {
  margin: 30px;
}
.tab-positive {
  color: white;
  background-color: #e77181;
}
.tab-positive:hover {
  color: white;
  background-color: #c7606e;
}
.tab-positive:focus {
  color: white;
  box-shadow: 0 0 1px 4px #f1afb8;
  background-color: #c7606e;
}
.tab-neutral {
  color: white;
  background-color: #5bca78;
}
.tab-neutral:hover {
  color: white;
  background-color: #50b76b;
}
.tab-neutral:focus {
  color: white;
  box-shadow: 0 0 1px 4px #60dd81;
  background-color: #50b76b;
}
.tab-negative {
  color: white;
  background-color: #59a0f1;
}
.tab-negative:hover {
  color: white;
  background-color: #4e90db;
}
.tab-negative:focus {
  color: white;
  box-shadow: 0 0 1px 4px #61a6f5;
  background-color: #4e90db;
}
.emotion-table {
  margin: 30px;
}
</style>

<style></style>
