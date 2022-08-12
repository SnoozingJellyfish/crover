<template>
  <div id="emotion-block">
    <div class="feature-block">
      <div class="feature-title">
        <h2>
          <!--<span style="vertical-align: middle">
            <fa icon="face-meh" class="icon-title"></fa></span
          >-->
          <i class="bi bi-emoji-neutral icon-title-bs"></i>
          感情分析
        </h2>
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
              <option selected>100</option>
              <!-- debug -->
              <option>500</option>
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
              @click="searchAnalyze()"
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
        <div class="topSlide result-region" v-if="isOpen">
          <pulse-loader
            :loading="isSpinner"
            :color="spinnerColor"
            :size="spinnerSize"
            class="spinner"
          />

          <div v-if="!isSpinner">
            <div class="row">
              <div class="col-md-6 col-12">
                <div class="chart-caption-topic">
                  <i
                    class="bi bi-arrow-left-circle-fill back-arrow"
                    :style="backArrowStyle"
                    @mouseover="focusBackArrow()"
                    @mouseleave="blurBackArrow()"
                    @click="backCluster()"
                    id="back-arrow"
                  ></i>
                  「{{ searchKeyword }}」と一緒に呟かれている言葉
                </div>

                <div class="row">
                  <div
                    v-for="(tw, wcId) in topicWord"
                    v-bind:key="wcId"
                    :class="topicWordColClass"
                  >
                    <div
                      class="wc-box"
                      @mouseover="displayWcButton[wcId] = true"
                      @mouseleave="displayWcButton[wcId] = false"
                    >
                      <vue-d3-cloud
                        :data="tw"
                        :fontSizeMapper="fontSizeMapper"
                        :width="topicCloudSize"
                        :height="topicCloudSize"
                        :font="'Noto Sans JP'"
                        :colors="topicCloudColor"
                        :padding="5"
                        class="cloud-region"
                      />
                      <!--
                      <fa
                        icon="face-meh"
                        class="icon-title wc-box-face"
                        v-show="displayWcEmotionIcon[wcId]"
                      ></fa>-->
                      <i
                        class="bi bi-emoji-neutral-fill wc-box-face-bs"
                        v-show="displayWcEmotionIcon[wcId]"
                      ></i>
                      <button
                        type="button"
                        class="btn btn-info wc-box-split mb-3 ml-1 mr-1"
                        v-show="displayWcButton[wcId]"
                        @click="splitWc(wcId)"
                        :disabled="disableSplit[wcId]"
                      >
                        意味で分ける
                      </button>
                      <button
                        type="button"
                        class="btn btn-info wc-box-emotion mb-3 ml-1 mr-1"
                        v-show="displayWcButton[wcId]"
                        @click="clickWcEmotionButton(wcId)"
                        :disabled="disableEmotionAnalysis[wcId]"
                      >
                        感情分析
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <div class="col-md-6 col-12">
                <div class="row">
                  <div class="col-12">
                    <div class="chart-caption">
                      <span>ツイート数</span>
                      <!-- 「~一緒に呟かれている言葉」と高さを合わせるため -->
                      <span class="back-arrow"> </span>
                    </div>
                    <Bar
                      :chart-options="tweetedTimeOptions"
                      :chart-data="tweetedTime"
                      :width="cloudSize"
                      :height="tweetedTimeHeight"
                      class="tweeted-time-chart"
                    />
                  </div>

                  <div class="col-md-6 col-12">
                    <div class="chart-caption">ツイート割合</div>
                    <Pie
                      :chart-options="emotionRatioOptions"
                      :chart-data="emotionRatio[selectedWcId]"
                      class="emotion-ratio-chart"
                      :style="{
                        width: emotionRatioWidth + 'px',
                        height: emotionRatioHeight + 'px'
                      }"
                      id="emotion-ratio-chart-id"
                    />
                  </div>

                  <div class="col-md-6 col-12">
                    <div class="chart-caption">感情ワード</div>
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
            <div class="emotion-table">
              <ul class="nav nav-justified" id="myTab" role="tablist">
                <li class="nav-item">
                  <a
                    class="nav-link active tab-positive"
                    id="positive-tab"
                    data-toggle="tab"
                    href="#home"
                    role="tab"
                    aria-controls="home"
                    aria-selected="true"
                    @click="clickPositiveTab()"
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
                    @click="clickNeutralTab()"
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
                    @click="clickNegativeTab()"
                    >ネガティブ</a
                  >
                </li>
              </ul>
              <div class="tab-content" id="myTabContent">
                <div
                  class="tab-pane fade show active"
                  role="tabpanel"
                  aria-labelledby="positive-tab"
                >
                  <table class="table table-striped">
                    <tbody class="tweet" id="tbody-tweet">
                      <tr v-for="t in selectedTweet" :key="t" class="tweetline">
                        <td
                          class="tweetline"
                          :style="{
                            width: String(currentWindowWidth - 170) + 'px'
                          }"
                        >
                          {{ t }}
                        </td>
                      </tr>
                      <!--
                      <tr>
                        <td></td>
                      </tr>
                      -->
                    </tbody>
                  </table>
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
import axios from 'axios'
import PulseLoader from 'vue-spinner/src/PulseLoader.vue'
import { Openable } from './util'
import VueD3Cloud from './VueD3Cloud.vue'
import 'chart.js/auto'
import { Bar, Pie } from 'vue-chartjs'

export default {
  components: { PulseLoader, VueD3Cloud, Bar, Pie },
  mixins: [Openable],
  name: 'emotion-block',
  data() {
    return {
      backendErrorcode: 0,
      emotionBlockElem: null,
      isOpen: false,
      trend: '',
      keyword: '',
      searchKeyword: '',
      tweetNum: 100,
      isSpinner: true,
      spinnerColor: '#999',
      spinnerSize: '15px',
      backArrowElem: null,
      displayWcEmotionIcon: [true, false, false, false],
      displayWcButton: [false, false, false, false],
      displayWcEmotionButton: [false, true, true, true],
      disableSplit: [false, false, false, false],
      disableEmotionAnalysis: [false, false, false, false],
      topicWcBgColor: ['#fff', '#fff', '#fff', '#fff'],
      selectedWcId: 0,
      topicWord: [],
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
      ]
    }
  },
  computed: {
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
      if (this.currentWindowWidth < this.colMdMin) {
        return String(this.currentWindowWidth - 82)
      } else {
        return String(Number(this.currentWindowWidth / 2) - 140)
      }
    },
    // eslint-disable-next-line
    topicCloudSize: function () {
      if (
        this.topicWord.length === 1 ||
        this.currentWindowWidth < this.colMdMin
      ) {
        return this.cloudSize
      } else {
        return this.cloudSize / 2
      }
    },
    // eslint-disable-next-line
    tweetedTimeHeight: function () {
      if (this.currentWindowWidth < this.colMdMin) {
        return String(Number(this.cloudSize) / 2)
      } else {
        return String(Number(this.cloudSize) / 3)
      }
    },
    // eslint-disable-next-line
    emotionRatioWidth: function () {
      if (this.currentWindowWidth < this.colMdMin) {
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
      if (this.currentWindowWidth < this.colMdMin) {
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
    }
  },
  mounted() {
    // this.emotionBlockElem = document.getElementById('emotion-block')
    axios.get('/trend').then((response) => (this.trend = response.data))
    console.log(this.trend)
    this.currentWindowWidth = window.innerWidth
    window.addEventListener('resize', () => {
      this.currentWindowWidth = window.innerWidth
    })
  },
  updated() {
    /*
    if (!this.emotionBlockElem) {
      this.emotionBlockElem = document.getElementById('emotion-block')
    }
    */
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
        if (window.innerWidth < this.colMdMin) {
          resultElems[i].style.padding = '0' // スマホ画面
        } else {
          resultElems[i].style.padding = '15px'
        }
      }
    }

    var emotionRatioElem = document.getElementById('emotion-ratio-chart-id')
    if (emotionRatioElem) {
      if (window.innerWidth < this.colMdMin) {
        emotionRatioElem.style.margin = '0 auto 0 auto' // スマホ画面
      } else {
        emotionRatioElem.style.margin = '80 auto 0 auto'
      }
    }
  },
  methods: {
    searchAnalyze() {
      this.clickWcEmotionButton(0)

      // 特殊文字をスペースに変換
      this.keyword = this.keyword.replace(
        // eslint-disable-next-line
        /[,<\.>\/\\;:\]\}\[\{\$=\^\~\*¥\|\+]/g,
        ' '
      )
      // eslint-disable-next-line
      this.keyword = this.keyword.replace(/[　]/g, ' ')
      this.keyword = this.keyword.replace(/ +/g, ' ')
      this.keyword = this.keyword.replace(/^ /g, '')
      this.keyword = this.keyword.replace(/ $/g, '')
      this.keyword = this.keyword.replace(/#+$/g, '')

      // キーワードにスペース以外の文字が入力されていない場合は警告を出し検索しない
      const noSpaceKeyword = this.keyword.replace(/[ ]/g, '')
      if (noSpaceKeyword === '') {
        alert('記号を含まないキーワードを入力してください。')
        return
      }

      this.isSpinner = true
      this.tbodyElem = null
      this.backArrowElem = null
      axios
        .get('/search_analyze', {
          params: {
            keyword: this.keyword,
            tweetNum: this.tweetNum
          }
        })
        .then((response) => {
          this.backendErrorcode = response.data.errorcode
          if (this.backendErrorcode !== 0) {
            this.isSpinner = false
            alert('不正な文字を含まないキーワードを入力してください。')
            return
          }

          this.searchKeyword = this.keyword
          this.topicWord = response.data.topicWord
          this.tweetedTime = response.data.tweetedTime
          this.emotionRatio = response.data.emotionRatio
          this.emotionWord = response.data.emotionWord
          this.tweet = response.data.tweet
          this.isSpinner = false
          this.isLoad = response.data.isLoad

          // 単語が1つだけの場合は分割ボタンを無効にする
          for (var i = 0; i < this.topicWord.length; i++) {
            if (this.topicWord[i].length === 1 || this.topicWord.length === 4) {
              this.disableSplit[i] = true
            } else {
              this.disableSplit[i] = false
            }
          }
        })
      if (this.backendErrorcode !== 0) {
        return
      }
      this.isOpen = true
      this.focusEmotion = 'positive'
      /*
      window.scrollTo({
        top: this.emotionBlockElem.offsetTop,
        behavior: 'auto'
      })
      */

      this.$nextTick(() => {
        this.positiveTab = document.getElementById('positive-tab')
        this.neutralTab = document.getElementById('neutral-tab')
        this.negativeTab = document.getElementById('negative-tab')
        this.clickPositiveTab()
        this.tbodyElem = document.getElementById('tbody-tweet')
        this.tbodyElem.addEventListener('scroll', this.loadTweet)
        this.backArrowElem = document.getElementById('back-arrow-elem')
      })
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
        this.clickWcEmotionButton(0)
        this.clickPositiveTab()
      }
    },
    clickWcEmotionButton(wcId) {
      this.selectedWcId = wcId
      this.displayWcEmotionIcon = [false, false, false, false]
      this.displayWcEmotionIcon[wcId] = true
      this.disableEmotionAnalysis = [false, false, false, false]
      this.disableEmotionAnalysis[wcId] = true
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
        this.clickWcEmotionButton(0)
        this.clickPositiveTab()
      }
    },
    clickPositiveTab() {
      this.tbodyElem.scroll({ top: 0 })
      this.focusEmotion = 'positive'
      this.focusTab(this.positiveTab, 'rgb(240, 79, 100)', '#f1afb8')
      this.blurTab(this.neutralTab, this.neutralTabDefaultColor)
      this.blurTab(this.negativeTab, this.negativeTabDefaultColor)
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
        this.tbodyElem.scrollHeight ===
          this.tbodyElem.clientHeight + this.tbodyElem.scrollTop &&
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
.back-arrow {
  font-size: 1.5em;
  vertical-align: middle;
}
.trend-label {
  font-size: 1em;
  margin: 1.5em 2rem 0rem 0rem;
  vertical-align: super;
}
.trend-button {
  margin: 0rem 1rem 0rem 0rem;
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
