<template>
  <div id="network-block">
    <div class="feature-block">
      <div class="feature-title">
        <h2>
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 512 512"
            class="icon-title-network"
          >
            <!--! Font Awesome Pro 6.1.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license (Commercial License) Copyright 2022 Fonticons, Inc. -->
            <path
              d="M380.6 365.6C401.1 379.9 416 404.3 416 432C416 476.2 380.2 512 336 512C291.8 512 256 476.2 256 432C256 423.6 257.3 415.4 259.7 407.8L114.1 280.4C103.8 285.3 92.21 288 80 288C35.82 288 0 252.2 0 208C0 163.8 35.82 128 80 128C101.9 128 121.7 136.8 136.2 151.1L320 77.52C321.3 34.48 356.6 0 400 0C444.2 0 480 35.82 480 80C480 117.9 453.7 149.6 418.4 157.9L380.6 365.6zM156.3 232.2L301.9 359.6C306.9 357.3 312.1 355.4 317.6 354.1L355.4 146.4C351.2 143.6 347.4 140.4 343.8 136.9L159.1 210.5C159.7 218 158.5 225.3 156.3 232.2V232.2z"
            />
          </svg>
          ネットワーク分析
        </h2>
        リツイート数の多いツイートの関係性を調べる

        <div class="row">
          <div class="form-group col-lg-2 col-md-3 col-sm-6 col-6">
            <select
              class="form-control input-form"
              id="InputWord"
              name="keyword"
              v-model="keyword"
            >
              <option v-for="k in keywordList" :key="k">
                {{ k }}
              </option>
            </select>
          </div>
          <div class="form-group col-lg-2 col-md-3 col-sm-6 col-6">
            <label for="TweetNum" class="col-form-label"
              >に関するツイート</label
            >
          </div>

          <div class="col-lg-3 col-md-4 col-sm-6 col-12">
            <Datepicker
              v-model="dateRange"
              :maxDate="new Date()"
              :enableTimePicker="false"
              range
            />
          </div>

          <div class="form-group col-8 d-grid" v-if="isMobile"></div>

          <div class="form-group col-lg-1 col-md-3 col-sm-2 col-4 d-grid">
            <button
              type="button"
              class="btn btn-primary"
              @click="analyzeNetwork()"
            >
              探す
            </button>
            <!--</div>-->
          </div>
        </div>

        <!--
        <transition
          name="topSlide"
          @before-enter="beforeEnter"
          @enter="enter"
          @before-leave="beforeLeave"
          @leave="leave"
        >-->

        <div
          class="topSlide result-region"
          id="network-result-id"
          v-if="isOpen"
        >
          <pulse-loader
            :loading="isSpinner"
            :color="spinnerColor"
            :size="spinnerSize"
            class="spinner"
          />

          <div v-if="!isSpinner">
            <div class="row">
              <div class="col-md-8 col-12">
                <div class="chart-caption-topic">
                  「{{ keyword }}」と一緒に呟かれている言葉
                </div>
              </div>

              <div class="col-md-4 col-12">
                <div class="row">
                  <div class="col-12">
                    <div class="chart-caption">全体ワード</div>
                    <div>
                      <vue-d3-cloud
                        :data="emotionWord[selectedWcId]"
                        :fontSizeMapper="fontSizeMapper"
                        :width="emotionCloudWidth"
                        :height="emotionCloudWidth"
                        :font="'Noto Sans JP'"
                        :colors="emotionCloudColor"
                        :padding="5"
                        class="cloud-region"
                      />
                    </div>
                  </div>

                  <div class="col-12">
                    <div class="chart-caption">グループワード</div>
                    <div>
                      <vue-d3-cloud
                        :data="emotionWord[selectedWcId]"
                        :fontSizeMapper="fontSizeMapper"
                        :width="emotionCloudWidth"
                        :height="emotionCloudWidth"
                        :font="'Noto Sans JP'"
                        :colors="emotionCloudColor"
                        :padding="5"
                        class="cloud-region"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <!--</transition>-->
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import axios from 'axios'
import PulseLoader from 'vue-spinner/src/PulseLoader.vue'
import { Openable } from './util'
import VueD3Cloud from './VueD3Cloud.vue'
import 'chart.js/auto'
import { Bar, Pie } from 'vue-chartjs'
import Datepicker from '@vuepic/vue-datepicker'
import '@vuepic/vue-datepicker/dist/main.css'
import { format } from 'date-fns'

export default {
  // components: { PulseLoader, VueD3Cloud, Bar, Pie },
  components: { Datepicker },
  mixins: [Openable],
  name: 'network-block',
  data() {
    return {
      navbarHeight: 0,
      backendErrorcode: 0,
      emotionResultElem: null,
      isOpen: false,
      keywordList: [],
      keyword: '',
      dateRange: [],
      datePickerFormat: '',
      searchKeyword: '',
      tweetNum: 100,
      isSpinner: true,
      spinnerColor: '#999',
      spinnerSize: '15px',
      doneSearch: false,
      backArrowElem: null,
      displayWcEmotionIcon: [true, false, false, false],
      displayWcButton: [false, false, false, false],
      displayWcEmotionButton: [false, true, true, true],
      disableSplit: [false, false, false, false],
      disableEmotionAnalysis: [false, false, false, false],
      topicWcBgColor: ['#fff', '#fff', '#fff', '#fff'],
      selectedWcId: 0,
      wholeWord: [],
      emotionWord: [],
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
      emotionSelectElem: null,
      emotionRatio: [],
      emotionRatioOptions: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { reverse: true, display: false }
          // legend: { reverse: true, labels: { font: { size: 15 } } }
        }
      },
      currentWindowWidth: 0,
      colMdMin: 768,
      tweet: {},
      focusEmotion: 'positive',
      moreTweet: true,
      positiveTab: null,
      neutralTab: null,
      negativeTab: null,
      positiveTabDefaultColor: '#e77181',
      neutralTabDefaultColor: '#5bca78',
      negativeTabDefaultColor: '#59a0f1',
      tbodyElem: null,
      isLoad: [
        { positive: false, neutral: false, negative: false },
        { positive: false, neutral: false, negative: false },
        { positive: false, neutral: false, negative: false },
        { positive: false, neutral: false, negative: false }
      ],
      tempdate: null
    }
  },
  computed: {
    // eslint-disable-next-line
    isMobile: function () {
      return this.currentWindowWidth < this.colMdMin
    },

    // eslint-disable-next-line
    topicWordColClass: function () {
      if (this.topicWord.length > 1) {
        return 'col-md-6 col-12'
      } else {
        return 'col-12'
      }
    },
    // eslint-disable-next-line
    backArrowStyle: function () {
      if (this.topicWord.length > 1) {
        return { color: 'rgb(151, 151, 151)' }
      } else {
        return { color: 'rgb(222, 222, 222)' }
      }
    },
    // eslint-disable-next-line
    cloudSize: function () {
      if (this.isMobile) {
        return String(this.currentWindowWidth - 82)
      } else {
        return String(Number(this.currentWindowWidth / 2) - 140)
      }
    },
    // eslint-disable-next-line
    topicCloudSize: function () {
      if (this.topicWord.length === 1 || this.isMobile) {
        return this.cloudSize
      } else {
        return this.cloudSize / 2
      }
    },
    // eslint-disable-next-line
    tweetedTimeHeight: function () {
      if (this.isMobile) {
        return String(Number(this.cloudSize) / 2)
      } else {
        return String(Number(this.cloudSize) / 3)
      }
    },
    // eslint-disable-next-line
    emotionRatioWidth: function () {
      if (this.isMobile) {
        return this.cloudSize
      } else {
        // return String(Number(this.currentWindowWidth / 4) - 60)
        return String((Number(this.emotionCloudWidth) * 3) / 4)
      }
    },
    // eslint-disable-next-line
    emotionRatioHeight: function () {
      // return String(Number(this.emotionRatioWidth) - 100)
      return String((Number(this.emotionCloudWidth) * 3) / 4)
    },
    // eslint-disable-next-line
    emotionCloudWidth: function () {
      if (this.isMobile) {
        return this.cloudSize
      } else {
        return String(Number(this.currentWindowWidth / 4) - 65)
      }
    },
    // eslint-disable-next-line
    selectedTweet: function () {
      if (this.focusEmotion === 'positive') {
        return this.tweet[this.selectedWcId].positive
      } else if (this.focusEmotion === 'neutral') {
        return this.tweet[this.selectedWcId].neutral
      } else if (this.focusEmotion === 'negative') {
        return this.tweet[this.selectedWcId].negative
      }
    },
    // eslint-disable-next-line
    emotionTableWidth: function () {
      if (this.isMobile) {
        return this.currentWindowWidth - 80
      } else {
        return this.currentWindowWidth - 170
      }
    }
  },
  mounted() {
    var endDate = new Date()
    var startDate = new Date(new Date().setDate(endDate.getDate() - 7))
    this.dateRange = [startDate, endDate]

    this.emotionResultElem = document.getElementById('emotion-result-id')
    axios.get('/init_retweet').then((response) => {
      this.keywordList = response.data.keywordList
      this.keyword = this.keywordList[0]
      this.startDate = response.data.startDate
      this.endDate = response.data.endDate
    })

    console.log(this.trend)
    this.currentWindowWidth = window.innerWidth
    window.addEventListener('resize', () => {
      this.currentWindowWidth = window.innerWidth
    })
    this.navbarHeight =
      document.getElementsByClassName('navbar')[0].clientHeight
  },
  updated() {
    if (!this.emotionResultElem) {
      this.emotionResultElem = document.getElementById('emotion-result-id')
    }
    if (this.emotionResultElem && this.doneSearch) {
      window.scrollTo({
        top: this.emotionResultElem.offsetTop - this.navbarHeight,
        behavior: 'auto'
      })
      this.doneSearch = false
    }

    if (!this.backArrowElem) {
      this.backArrowElem = document.getElementById('back-arrow')
    }
    if (!this.tbodyElem) {
      this.tbodyElem = document.getElementById('tbody-tweet')
    }
    if (this.tbodyElem) {
      this.tbodyElem.addEventListener('scroll', this.loadTweet)
    }
    if (!this.positiveTab) {
      this.positiveTab = document.getElementById('positive-tab')
      this.neutralTab = document.getElementById('neutral-tab')
      this.negativeTab = document.getElementById('negative-tab')
      if (this.positiveTab) {
        this.clickPositiveTab()
      }
    }
    var resultElems = document.getElementsByClassName('result-region')
    if (resultElems) {
      for (var i = 0; i < resultElems.length; i++) {
        if (this.isMobile) {
          resultElems[i].style.padding = '0' // スマホ画面
        } else {
          resultElems[i].style.padding = '15px'
        }
      }
    }

    var emotionRatioElem = document.getElementById('emotion-ratio-chart-id')
    if (emotionRatioElem) {
      if (this.isMobile) {
        emotionRatioElem.style.margin = '0 auto 0 auto' // スマホ画面
      } else {
        emotionRatioElem.style.margin = '80 auto 0 auto'
      }
    }
    if (!this.emotionSelectElem) {
      this.emotionSelectElem = document.getElementById('emotion-select-id')
    }
  },
  methods: {
    analyzeNetwork() {
      this.isSpinner = true
      var startDateStr = format(dateRange[0], 'yyyy-MM-dd')
      var endDateStr = format(dateRange[1], 'yyyy-MM-dd')
      axios
        .get('/analyze_network', {
          params: {
            keyword: this.keyword,
            startDate: startDateStr,
            endDate: endDateStr
          }
        })
        .then((response) => {
          this.wholeWord = response.data.wholeWord
          this.groupWord = response.data.groupWord
          this.tweet = response.data.tweet
          this.isSpinner = false
          this.doneSearch = true
        })
      if (this.backendErrorcode !== 0) {
        return
      }
      this.isOpen = true
    },
    wordClickHandler(name, value, vm) {
      console.log('wordClickHandler', name, value, vm)
    },

    splitWc(wcId) {
      if (this.topicWord.length < 4) {
        axios
          .get('/split_wc', {
            params: {
              wcId: wcId
            }
          })
          .then((response) => {
            this.topicWord = response.data.topicWord
            this.emotionRatio = response.data.emotionRatio
            this.emotionWord = response.data.emotionWord
            this.tweet = response.data.tweet
            this.isLoad = response.data.isLoad

            // 単語が1つだけの場合は分割ボタンを無効にする
            for (var i = 0; i < this.topicWord.length; i++) {
              if (
                this.topicWord[i].length === 1 ||
                this.topicWord.length === 4
              ) {
                this.disableSplit[i] = true
              } else {
                this.disableSplit[i] = false
              }
            }
          })
        this.selectWcEmotion(0)
        this.clickPositiveTab()
      }
    },
    selectWcEmotion(wcId) {
      this.selectedWcId = wcId
      this.displayWcEmotionIcon = [false, false, false, false]
      this.displayWcEmotionIcon[wcId] = true
      this.disableEmotionAnalysis = [false, false, false, false]
      this.disableEmotionAnalysis[wcId] = true
    },
    clickWcEmotionButton(wcId) {
      this.selectWcEmotion(wcId)
      if (this.emotionSelectElem) {
        if (this.isMobile) {
          window.scrollTo({
            top: this.emotionSelectElem.offsetTop - this.navbarHeight,
            behavior: 'auto'
          })
        }
      }
    },
    focusBackArrow() {
      if (this.topicWord.length > 1) {
        this.backArrowElem.style.color = 'rgb(140, 140, 140)'
        this.backArrowElem.style.cursor = 'pointer'
      } else {
        this.backArrowElem.style.cursor = 'default'
      }
    },
    blurBackArrow() {
      if (this.topicWord.length > 1) {
        this.backArrowElem.style.color = 'rgb(151, 151, 151)'
      }
    },
    backCluster() {
      if (this.topicWord.length > 1) {
        axios.get('/back_cluster').then((response) => {
          this.topicWord = response.data.topicWord
          this.emotionRatio = response.data.emotionRatio
          this.emotionWord = response.data.emotionWord
          this.tweet = response.data.tweet
          this.isLoad = response.data.isLoad
        })
        this.selectWcEmotion(0)
        this.clickPositiveTab()
      }
    },
    clickPositiveTab() {
      if (this.tbodyElem) {
        this.tbodyElem.scroll({ top: 0 })
        this.focusEmotion = 'positive'
        this.focusTab(this.positiveTab, 'rgb(240, 79, 100)', '#f1afb8')
        this.blurTab(this.neutralTab, this.neutralTabDefaultColor)
        this.blurTab(this.negativeTab, this.negativeTabDefaultColor)
      }
    },
    clickNeutralTab() {
      this.tbodyElem.scroll({ top: 0 })
      this.focusEmotion = 'neutral'
      this.blurTab(this.positiveTab, this.positiveTabDefaultColor)
      this.focusTab(this.neutralTab, 'rgb(44, 210, 88)', '#60dd81')
      this.blurTab(this.negativeTab, this.negativeTabDefaultColor)
    },
    clickNegativeTab() {
      this.tbodyElem.scroll({ top: 0 })
      this.focusEmotion = 'negative'
      this.blurTab(this.positiveTab, this.positiveTabDefaultColor)
      this.blurTab(this.neutralTab, this.neutralTabDefaultColor)
      this.focusTab(this.negativeTab, 'rgb(64, 140, 255)', '#6babf4')
    },
    focusTab(tabElem, bgColor, shadowColor) {
      tabElem.style.color = 'white'
      tabElem.style.background = bgColor
      tabElem.style.boxShadow = '0 0 1px 3px ' + shadowColor
    },
    blurTab(tabElem, bgColor) {
      tabElem.style.color = 'white'
      tabElem.style.background = bgColor
      tabElem.style.boxShadow = '0 0'
    },

    loadTweet() {
      if (
        this.tbodyElem.scrollHeight -
          (this.tbodyElem.clientHeight + this.tbodyElem.scrollTop) <
          50 &&
        this.isLoad[this.selectedWcId][this.focusEmotion]
      ) {
        var selectedWcTweet = this.tweet[this.selectedWcId]
        axios
          .get('/load_tweet', {
            params: {
              wcId: this.selectedWcId,
              emotion: this.focusEmotion,
              tweetCnt: selectedWcTweet[this.focusEmotion].length
            }
          })
          .then((response) => {
            this.isLoad[this.selectedWcId][this.focusEmotion] =
              response.data.isLoadOne
            if (this.focusEmotion === 'positive') {
              selectedWcTweet.positive = selectedWcTweet.positive.concat(
                response.data.addTweet
              )
            } else if (this.focusEmotion === 'neutral') {
              selectedWcTweet.neutral = selectedWcTweet.neutral.concat(
                response.data.addTweet
              )
            } else if (this.focusEmotion === 'negative') {
              selectedWcTweet.negative = selectedWcTweet.negative.concat(
                response.data.addTweet
              )
            }
          })
      }
    }
  }
}
</script>

<style scoped>
.icon-title-network {
  width: 1.5em;
  vertical-align: -0.35em;
}
.chart-caption {
  font-size: 1.3rem;
  margin: 15px;
  text-align: left;
}
.chart-caption-topic {
  font-size: 1.3rem;
  margin: 15px 15px 0 15px;
  text-align: left;
}
.wc-box {
  position: relative;
}
.wc-box-face-bs {
  position: absolute;
  top: 0;
  left: 15px;
  margin: 17px 15px;
  font-size: 1.7em;
  color: rgb(56, 167, 56);
  vertical-align: middle;
}
.wc-box-split {
  position: absolute;
  top: 0;
  right: 0;
  margin: 15px 30px;
  color: white;
}
.wc-box-emotion {
  position: absolute;
  top: 0;
  right: 6em;
  margin: 15px 60px;
  color: white;
}
.cloud-region {
  background-color: #fff;
  border-radius: 10px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
  margin: 15px;
  text-align: center;
}
.tweeted-time-chart {
  margin: 15px;
}

.emotion-ratio-chart {
  margin-left: auto;
  margin-right: auto;
  margin-top: 50px;
}

.tab-positive {
  color: white;
  background-color: #e77181;
}
.tab-neutral {
  color: white;
  background-color: #5bca78;
}
.tab-negative {
  color: white;
  background-color: #59a0f1;
}
.tab-icon {
  color: white;
  font-size: 1.5em;
}
.emotion-table {
  margin: 15px;
}

tbody.tweet {
  /*overflow-x: hidden;*/
  overflow-y: scroll;
  display: block;
  height: 500px;
  /*table-layout: fixed;*/
}
td.tweetline {
  display: block;
}

.load-tweet {
  text-align: center;
  color: blue;
  cursor: pointer;
}
</style>

<style></style>
