<template>
  <div class="about-page">
    <br />
    <h1>言葉の海に潜ってみよう</h1>
    <h2>Twitter分析ツール</h2>

    <div class="about-toggle" @click="isOpen = true" v-show="!isOpen">
      ▼About
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
          >https://twitter.com/snooze_jelly</a
        ><br />
        <a href="https://github.com/SnoozingJellyfish/crover"
          >アプリソースコード（GitHub）</a
        ><br />
        <br />
        <h2>License</h2>
        関連ワードの分割に<a
          href="http://www.cl.ecei.tohoku.ac.jp/~m-suzuki/jawiki_vector/"
          >WikiEntVec（鈴木正敏、2019年/CC-BY-SA）</a
        >のword2vecを使用
      </div>
    </transition>
    <div class="about-toggle" @click="isOpen = false" v-show="isOpen">
      ▲close
    </div>
  </div>
</template>

<script>
export default {
  name: 'about-page',
  data() {
    return {
      isOpen: false
    }
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
.about-toggle {
  color: blue;
  cursor: pointer;
}
</style>

<style>
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
</style>
