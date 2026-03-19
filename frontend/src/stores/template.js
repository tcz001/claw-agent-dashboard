import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  lookupTemplate,
  fetchRenderedTemplate,
  updateTemplate as apiUpdate,
} from '../api'

export const useTemplateStore = defineStore('template', () => {
  const currentTemplate = ref(null)
  const renderedContent = ref('')
  const renderWarnings = ref([])
  const templateLoading = ref(false)
  const _agentId = ref(null)

  // Whether the current template is inherited from a blueprint (not owned by the agent)
  const isInherited = computed(() => {
    if (!currentTemplate.value || !_agentId.value) return false
    return currentTemplate.value.agent_id !== _agentId.value
  })

  async function loadTemplate(agentId, filePath) {
    templateLoading.value = true
    _agentId.value = agentId
    try {
      const template = await lookupTemplate(agentId, filePath)
      currentTemplate.value = template

      const rendered = await fetchRenderedTemplate(template.id, agentId)
      renderedContent.value = rendered.content
      renderWarnings.value = rendered.warnings || []

      return template
    } finally {
      templateLoading.value = false
    }
  }

  async function saveTemplate(content, commitMsg = null) {
    if (!currentTemplate.value) return
    const updated = await apiUpdate(currentTemplate.value.id, content, commitMsg)
    currentTemplate.value = updated

    const rendered = await fetchRenderedTemplate(updated.id, _agentId.value)
    renderedContent.value = rendered.content
    renderWarnings.value = rendered.warnings || []

    return updated
  }

  function clearTemplate() {
    currentTemplate.value = null
    renderedContent.value = ''
    renderWarnings.value = []
    _agentId.value = null
  }

  return {
    currentTemplate, renderedContent, renderWarnings, templateLoading,
    isInherited,
    loadTemplate, saveTemplate, clearTemplate,
  }
})
