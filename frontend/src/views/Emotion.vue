<template>
  <div class="emotion-block feature-block">
    <div class="feature-title">
      <h2>感情分析</h2>
      <h5>
        キーワードを含むツイートの感情と、一緒にツイートされている言葉を調べる
      </h5>
    </div>
  </div>
</template>

<script>
export default {
  name: 'emotion-block',
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

<style scoped></style>

<style></style>
