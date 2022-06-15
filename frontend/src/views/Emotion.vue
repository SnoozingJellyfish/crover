<template>
  <div class="emotion-block feature-block">
    <div class="feature-title">
      <h2><fa icon="face-meh" class="icon-title"></fa>感情分析</h2>
      キーワードを含むツイートの感情と、一緒にツイートされている言葉を調べる
      <form method="post">
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
            <button type="submit" class="btn btn-primary">探す</button>
          </div>
        </div>

        <label class="trend-label"> 今のトレンド </label>
        <button
          v-for="t in trend"
          v-bind:key="t"
          @click="keyword = t"
          class="btn btn-outline-primary trend-button mb-3 ml-1 mr-1"
          type="button"
        >
          {{ t }}
        </button>
      </form>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'emotion-block',
  data() {
    return {
      isOpen: false,
      trend: '',
      keyword: ''
    }
  },
  mounted() {
    axios.get('/trend').then((response) => (this.trend = response.data))
    console.log(this.trend)
  },
  methods: {
    beforeEnter(el) {
      el.style.height = '0'
    },
    enter(el) {
      el.style.height = el.scrollHeight + 'px'
    },
    beforeLeave(el) {
      el.style.height = el.scrollHeight + 'px'
    },
    leave(el) {
      el.style.height = '0'
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
</style>

<style></style>
