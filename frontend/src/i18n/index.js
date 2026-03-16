import { createI18n } from 'vue-i18n'
import en from './en.js'
import zh from './zh.js'

const savedLocale = localStorage.getItem('locale') || 'en'

const i18n = createI18n({
  legacy: false,
  locale: savedLocale,
  fallbackLocale: 'en',
  messages: { en, zh },
})

export default i18n
