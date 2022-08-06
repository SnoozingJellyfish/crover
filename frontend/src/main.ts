import { createApp } from 'vue'
import App from './App.vue'
import './registerServiceWorker'
import router from './router'
import store from './store'
// import { BootstrapVue, IconsPlugin } from 'bootstrap-vue'
import 'bootstrap/dist/css/bootstrap.min.css'
// import { BootstrapVueIcons } from 'bootstrap-vue'
// import 'bootstrap-vue/dist/bootstrap-vue-icons.min.css'
import 'bootstrap-icons/font/bootstrap-icons.css'
import { FontAwesomeIcon } from '@/plugins/font-awesome'
import Axios from 'axios'
// Axios.defaults.baseURL = 'http://localhost:3000' // mockサーバーを設定

createApp(App)
  .use(store)
  .use(router)
  .component('fa', FontAwesomeIcon)
  .mount('#app')
