import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchSettings, updateSettings as apiUpdate } from '../api'

export const useSettingsStore = defineStore('settings', () => {
  const settings = ref({
    llm: {
      default: { openai_base_url: '', api_key: '', model_name: 'gpt-4o-mini' },
      overrides: {},
    },
    features: { auto_summary: true },
  })
  const dialogVisible = ref(false)

  async function load() {
    try {
      const data = await fetchSettings()
      settings.value = data
    } catch {
      // ignore
    }
  }

  async function save(data) {
    const result = await apiUpdate(data)
    if (result.settings) {
      settings.value = result.settings
    }
  }

  function openDialog() {
    dialogVisible.value = true
  }

  function closeDialog() {
    dialogVisible.value = false
  }

  return { settings, dialogVisible, load, save, openDialog, closeDialog }
})
