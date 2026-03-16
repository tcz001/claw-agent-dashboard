<template>
  <el-dialog
    v-model="settingsStore.dialogVisible"
    :title="t('settings.title')"
    width="560px"
    :close-on-click-modal="false"
  >
    <el-form :model="form" label-width="140px" label-position="left">
      <!-- Config target selector -->
      <el-form-item :label="t('settings.configTarget')">
        <el-select v-model="configTarget" style="width: 100%">
          <el-option :label="t('settings.globalDefault')" value="default" />
          <el-option :label="t('settings.translation')" value="translation" />
          <el-option :label="t('settings.versionSummary')" value="version_summary" />
        </el-select>
      </el-form-item>

      <el-divider />

      <el-form-item label="OpenAI Base URL">
        <el-input
          v-model="currentConfig.openai_base_url"
          :placeholder="configTarget === 'default' ? 'https://api.openai.com/v1' : defaultHint.openai_base_url || t('settings.useGlobalDefault')"
        />
        <div v-if="configTarget !== 'default'" class="field-hint">
          {{ t('settings.globalDefaultLabel') }}: {{ defaultHint.openai_base_url || t('settings.notSet') }}
        </div>
      </el-form-item>
      <el-form-item label="API Key">
        <el-input
          v-model="currentConfig.api_key"
          type="password"
          show-password
          :placeholder="configTarget === 'default' ? 'sk-...' : t('settings.leaveEmptyForDefault')"
        />
        <div v-if="configTarget !== 'default'" class="field-hint">
          {{ t('settings.globalDefaultLabel') }}: {{ defaultHint.api_key_display || t('settings.notSet') }}
        </div>
      </el-form-item>
      <el-form-item label="Model Name">
        <el-input
          v-model="currentConfig.model_name"
          :placeholder="configTarget === 'default' ? 'gpt-4o-mini' : defaultHint.model_name || t('settings.useGlobalDefault')"
        />
        <div v-if="configTarget !== 'default'" class="field-hint">
          {{ t('settings.globalDefaultLabel') }}: {{ defaultHint.model_name || t('settings.notSet') }}
        </div>
      </el-form-item>

      <el-divider />

      <el-form-item :label="t('settings.autoGenerateSummary')">
        <el-switch v-model="form.features.auto_summary" />
        <span class="switch-hint">{{ t('settings.autoSummaryDescription') }}</span>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="settingsStore.closeDialog()">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="saving" @click="save">{{ t('common.save') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { reactive, ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useSettingsStore } from '../stores/settings'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

const settingsStore = useSettingsStore()
const saving = ref(false)
const configTarget = ref('default')

const form = reactive({
  llm: {
    default: { openai_base_url: '', api_key: '', model_name: 'gpt-4o-mini' },
    overrides: {
      translation: { openai_base_url: '', api_key: '', model_name: '' },
      version_summary: { openai_base_url: '', api_key: '', model_name: '' },
    },
  },
  features: { auto_summary: true },
})

const currentConfig = computed(() => {
  if (configTarget.value === 'default') return form.llm.default
  if (!form.llm.overrides[configTarget.value]) {
    form.llm.overrides[configTarget.value] = { openai_base_url: '', api_key: '', model_name: '' }
  }
  return form.llm.overrides[configTarget.value]
})

const defaultHint = computed(() => ({
  openai_base_url: form.llm.default.openai_base_url,
  api_key_display: form.llm.default.api_key
    ? form.llm.default.api_key.substring(0, 8) + '...'
    : '',
  model_name: form.llm.default.model_name,
}))

// Sync form when dialog opens
watch(() => settingsStore.dialogVisible, (visible) => {
  if (visible) {
    const s = settingsStore.settings
    const llm = s.llm || {}
    const def = llm.default || {}
    form.llm.default.openai_base_url = def.openai_base_url || ''
    form.llm.default.api_key = def.api_key || ''
    form.llm.default.model_name = def.model_name || 'gpt-4o-mini'
    const overrides = llm.overrides || {}
    for (const key of ['translation', 'version_summary']) {
      const o = overrides[key] || {}
      form.llm.overrides[key] = {
        openai_base_url: o.openai_base_url || '',
        api_key: o.api_key || '',
        model_name: o.model_name || '',
      }
    }
    form.features.auto_summary = s.features?.auto_summary !== false
    configTarget.value = 'default'
  }
})

async function save() {
  saving.value = true
  try {
    await settingsStore.save({ ...form })
    ElMessage.success(t('settings.saved'))
    settingsStore.closeDialog()
  } catch (e) {
    ElMessage.error(t('settings.saveFailed') + ': ' + (e.message || e))
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.field-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}
.switch-hint {
  font-size: 12px;
  color: #909399;
  margin-left: 8px;
}
</style>
