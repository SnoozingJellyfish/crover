<template>
  <div class="about-block">
    <br />
    <h1>言葉の海に潜ってみよう</h1>
    <h2>Twitter分析ツール</h2>
    <div class="about-align">
      <span class="about-toggle" @click="isOpen = true" v-show="!isOpen">
        ▼About
      </span>
    </div>
    <div v-show="isOpen">
      <br />
    </div>
    <transition
      name="topSlide"
      @before-enter="beforeEnter"
      @enter="enter"
      @before-leave="beforeLeave"
      @leave="leave"
    >
      <div class="topSlide" v-show="isOpen">
        世界がネットワークで繋がって<br />
        指先一つでどんな情報にもアクセスできるようになった<br />
        毎日誰かの気の利いたつぶやきを目にするようになった<br />
        でもその一方で<br />
        網目から零れ落ちるように無数の言葉が情報の海に沈んでいく<br />
        限りなく開かれた空間の中に淀みが生まれ<br />
        知らぬ間に周りが見えなくなる<br />
        隣の人は何の話をしている？<br />
        あの話題について、みんなどう思っているんだろう？<br />
        多様性は見えていないだけで、すぐそこにある<br />
        分断を渡る地図を手に<br />
        言葉の海に潜ってみよう<br />
        <br />
        <h2>お問い合わせ・開発参加</h2>
        <a href="https://twitter.com/snooze_jelly"
          ><i class="bi bi-twitter"></i> https://twitter.com/snooze_jelly</a
        ><br />
        <a href="https://github.com/SnoozingJellyfish/crover"
          ><i class="bi bi-github"></i> GitHub</a
        ><br />
        <br />
        <h2>License</h2>
        関連ワードの分割に<a
          href="http://www.cl.ecei.tohoku.ac.jp/~m-suzuki/jawiki_vector/"
          >WikiEntVec（鈴木正敏、2019年/CC-BY-SA）</a
        >のword2vecを使用
      </div>
    </transition>
    <div class="about-align">
      <span class="about-toggle" @click="isOpen = false" v-show="isOpen">
        ▲close
      </span>
    </div>
  </div>
</template>

<script>
import { Openable } from './util'
export default {
  name: 'about-block',
  mixins: [Openable],
  data() {
    return {
      isOpen: false,
      colMdMin: 768
    }
  },
  mounted() {
    var aboutToggleElems = document.getElementsByClassName('about-toggle')
    for (var i = 0; i < aboutToggleElems.length; i++) {
      if (window.innerWidth < this.colMdMin) {
        aboutToggleElems[i].style.padding = '0 30px 0 0'
      } else {
        aboutToggleElems[i].style.padding = '0 60px 0 0'
      }
    }
  }
}
</script>

<style scoped>
.about-toggle {
  color: royalblue;
  cursor: pointer;
}
.about-align {
  text-align: right;
  padding-bottom: 0.3rem;
}
</style>

<style></style>
