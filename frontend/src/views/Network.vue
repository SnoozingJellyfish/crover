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
              id="retweet-keyword"
              name="keyword"
              v-model="keyword"
            >
              <option v-for="k in keywordList" :key="k">
                {{ k }}
              </option>
            </select>
          </div>
          <div class="form-group col-lg-2 col-md-3 col-sm-6 col-6">
            <label class="col-form-label">に関するツイート</label>
          </div>

          <div class="col-lg-3 col-md-4 col-sm-6 col-12">
            <Datepicker
              v-model="dateRange[selectedKeywordId]"
              :minDate="minDateList[selectedKeywordId]"
              :maxDate="maxDateList[selectedKeywordId]"
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
              <div class="col-md-6 col-12">
                <div class="chart-caption-topic" id="network-result">
                  「{{ keyword }}」と一緒に呟かれているツイート
                </div>
                <div class="network-region wc-box" id="network-graph">
                  <network
                    :nodeList="graphData['nodes']"
                    :linkList="graphData['links']"
                    :svgSize="{
                      width: networkRegionSize,
                      height: networkRegionSize
                    }"
                    @hoverNode="hoverNode"
                    @houtNode="houtNode"
                  ></network>
                  <!-- カーソルを合わせたときに表示する情報領域-->
                  <div id="tweet-content" class="tweet-content-class">
                    <h4></h4>
                    <p></p>
                  </div>
                </div>
              </div>

              <div class="col-md-3 col-12">
                <div class="row">
                  <div class="col-12">
                    <div class="chart-caption">全体ワード</div>
                    <div>
                      <vue-d3-cloud
                        :data="wholeWord"
                        :fontSizeMapper="fontSizeMapper"
                        :width="cloudSize"
                        :height="cloudSize"
                        :font="'Noto Sans JP'"
                        :colors="['black']"
                        :padding="5"
                        class="cloud-region"
                      />
                    </div>
                  </div>

                  <div class="col-12">
                    <div class="chart-caption">グループワード</div>
                    <div>
                      <vue-d3-cloud
                        :data="groupWord[selectedGroup]"
                        :fontSizeMapper="fontSizeMapper"
                        :width="cloudSize"
                        :height="cloudSize"
                        :font="'Noto Sans JP'"
                        :colors="[selectedGroupColor]"
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
import * as d3 from 'd3'
import VueD3Cloud from './VueD3Cloud.vue'
import 'chart.js/auto'
import { Bar, Pie } from 'vue-chartjs'
import Datepicker from '@vuepic/vue-datepicker'
import '@vuepic/vue-datepicker/dist/main.css'
import { format } from 'date-fns'
// import Network from 'vue-network-d3'
import Network from './NetworkD3.vue'

export default {
  // components: { Datepicker, PulseLoader, VueD3Cloud },
  components: { Datepicker, PulseLoader, Network, VueD3Cloud },
  mixins: [Openable],
  name: 'network-block',
  data() {
    return {
      navbarHeight: 0,
      backendErrorcode: 0,
      isOpen: false,
      keywordList: [],
      startDateList: [],
      minDateList: [],
      maxDateList: [],
      dateRange: [],
      datePickerFormat: '',
      isSpinner: true,
      spinnerColor: '#999',
      spinnerSize: '15px',
      doneSearch: false,
      selectedKeywordId: 0,
      wholeWord: [],
      groupWord: [],
      // colorScale: d3.scaleOrdinal(d3.schemeCategory10),
      colorScale: d3.schemeCategory10,
      fontSizeMapper: (word) => Math.log2(word.value) * 10,
      currentWindowWidth: 0,
      colMdMin: 768,
      tweet: {},
      networkGraphElem: null,
      networkRegionElem: null,
      graphData: {},
      nodeData: {},
      tweetContentElem: null,
      selectedGroup: 0,
      selectedGroupColor: ''
    }
  },
  computed: {
    // eslint-disable-next-line
    isMobile: function () {
      return this.currentWindowWidth < this.colMdMin
    },
    // eslint-disable-next-line
    networkRegionSize: function () {
      if (this.isMobile) {
        return this.currentWindowWidth - 82
      } else {
        return this.currentWindowWidth / 2 - 140
      }
    },
    // eslint-disable-next-line
    tweetContentWidth: function () {
      if (this.isMobile) {
        return 130
      } else {
        return 200
      }
    },
    // eslint-disable-next-line
    cloudSize: function () {
      if (this.isMobile) {
        return this.networkRegionSize
      } else {
        return this.currentWindowWidth / 4 - 110
      }
    },
    // eslint-disable-next-line
    keyword: function () {
      return this.keywordList[this.selectedKeywordId]
    }
  },
  mounted() {
    const retweetKeywordElem = document.getElementById('retweet-keyword')
    retweetKeywordElem.onchange = () =>
      (this.selectedKeywordId = retweetKeywordElem.selectedIndex)
    axios.get('/init_retweet').then((response) => {
      this.keywordList = response.data.keywordList

      for (var i = 0; i < this.keywordList.length; i++) {
        var d = response.data.minDateList[i]
        var minMonth = String(Number(d.substr(5, 2)) - 1)
        var minDate = new Date(d.substr(0, 4), minMonth, d.substr(8, 2))
        this.minDateList.push(minDate)

        d = response.data.maxDateList[i]
        var maxMonth = String(Number(d.substr(5, 2)) - 1)
        var maxDate = new Date(d.substr(0, 4), maxMonth, d.substr(8, 2))
        this.maxDateList.push(maxDate)

        d = response.data.startDateList[i]
        var startMonth = String(Number(d.substr(5, 2)) - 1)
        var startDate = new Date(d.substr(0, 4), startMonth, d.substr(8, 2))

        this.dateRange.push([startDate, maxDate])
      }
      this.selectedKeywordId = 0
    })

    this.currentWindowWidth = window.innerWidth
    window.addEventListener('resize', () => {
      this.currentWindowWidth = window.innerWidth
    })
    this.navbarHeight =
      document.getElementsByClassName('navbar')[0].clientHeight
  },
  updated() {
    if (!this.tweetContentElem) {
      this.tweetContentElem = document.getElementById('tweet-content')
    }
    if (!this.networkGraphElem) {
      this.networkGraphElem = document.getElementById('network-graph')
    }
    if (!this.networkResultElem) {
      this.networkResultElem = document.getElementById('network-result')
    }
    if (this.networkResultElem && this.doneSearch) {
      window.scrollTo({
        top: this.networkResultElem.offsetTop - this.navbarHeight,
        behavior: 'auto'
      })
      this.doneSearch = false
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
  },
  methods: {
    analyzeNetwork() {
      if (!this.dateRange[this.selectedKeywordId][1]) {
        alert('ツイートを収集する最終日を入力してください。')
        return
      }
      this.isSpinner = true
      this.networkResultElem = null

      var startDateStr = format(
        this.dateRange[this.selectedKeywordId][0],
        'yyyy-MM-dd'
      )
      var endDateStr = format(
        this.dateRange[this.selectedKeywordId][1],
        'yyyy-MM-dd'
      )
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
          this.isSpinner = false

          this.selectedGroup = this.groupWord.length - 1

          // 事前に描画したグラフをクリア
          /*
          var graphElem = d3.select('#network_graph').selectAll('g')
          console.log(graphElem)
          graphElem.remove()
          */
          this.graphData = response.data.graph
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
    hoverNode(e, eDict) {
      this.nodeData = eDict
      this.selectedGroupColor = this.colorScale[eDict.group]
      this.tweetContentElem = d3.select('#tweet-content')
      if (
        eDict.x + 30 + this.tweetContentWidth < // padding の20pxをプラス
        this.networkGraphElem.offsetLeft + this.networkRegionSize
      ) {
        var tweetContentLeft = eDict.x + 10
      } else {
        tweetContentLeft = eDict.x - 10 - this.tweetContentWidth
      }

      this.tweetContentElem
        .style('left', tweetContentLeft + 'px')
        .style('top', eDict.y + 10 + 'px')
        .style('width', this.tweetContentWidth + 'px')
        .style('z-index', 0)
        .style('opacity', 1)

      this.tweetContentElem
        .select('h4')
        .style('border-bottom', '2px solid ' + this.selectedGroupColor)
        .style('margin-right', '0px')
        .text(eDict.author)
      this.tweetContentElem.select('p').text(eDict.tweet)

      this.selectedGroup = eDict.group
    },
    houtNode(e, eDict) {
      this.tweetContentElem.style('opacity', 0)
      this.selectedGroup = this.groupWord.length - 1
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
.network-region {
  border-radius: 10px;
  margin: 15px;
}
.tweet-content-class {
  position: absolute;
  background-color: #fff;
  padding: 10px;
  border-radius: 10px;
  border: solid gray;
  opacity: 0;
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
</style>

<style></style>
