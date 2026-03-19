<template>
  <el-drawer
    :model-value="store.variablesDrawerOpen"
    :title="t('agentVariables.title')"
    direction="rtl"
    size="420px"
    :before-close="store.closeVariablesDrawer"
    :append-to-body="true"
  >
    <div v-loading="store.agentVariablesLoading" class="agent-vars-content">
      <div v-if="store.agentVariables.length === 0 && !store.agentVariablesLoading" class="empty-state">
        {{ t('agentVariables.noVariables') }}
      </div>
      <div v-else class="var-list">
        <div v-for="v in store.agentVariables" :key="v.name" class="var-item">
          <div class="var-header">
            <code class="var-name">{{ v.name }}</code>
            <el-tag :type="scopeTagType(v.scope)" size="small">{{ v.scope }}</el-tag>
          </div>
          <div class="var-value">
            <code>{{ v.type === 'secret' ? '******' : v.value }}</code>
          </div>
          <div class="var-actions">
            <template v-if="v.scope === 'agent'">
              <el-button size="small" text @click="editVar(v)">{{ t('agentVariables.edit') }}</el-button>
              <el-popconfirm
                :title="t('agentVariables.deleteConfirm')"
                @confirm="deleteVar(v)"
              >
                <template #reference>
                  <el-button size="small" text type="danger">{{ t('agentVariables.delete') }}</el-button>
                </template>
              </el-popconfirm>
            </template>
            <template v-else>
              <el-button size="small" text type="primary" @click="overrideVar(v)">
                {{ t('agentVariables.override') }}
              </el-button>
            </template>
          </div>
        </div>
      </div>
      <el-button class="new-var-btn" size="small" @click="createAgentVar()">
        {{ t('agentVariables.newVariable') }}
      </el-button>
    </div>
    <VariableDialog />
  </el-drawer>
</template>

<script setup>
import { watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { useAgentStore } from '../stores/agent'
import { useVariableStore } from '../stores/variable'
import { deleteVariable as apiDelete } from '../api'
import VariableDialog from './VariableDialog.vue'

const { t } = useI18n()
const store = useAgentStore()
const variableStore = useVariableStore()

function scopeTagType(scope) {
  if (scope === 'global') return ''
  if (scope === 'blueprint') return 'warning'
  return 'success'
}

function editVar(v) {
  variableStore.openEditDialog(v)
}

async function deleteVar(v) {
  try {
    await apiDelete(v.id, true)
    ElMessage.success(t('management.variableDeleted'))
    await store.loadAgentVariables()
  } catch {
    ElMessage.error(t('management.deleteFailed'))
  }
}

function overrideVar(v) {
  variableStore.openCreateDialog({
    scope: 'agent',
    agent_id: store.currentAgent?.id,
    name: v.name,
  })
}

function createAgentVar() {
  variableStore.openCreateDialog({
    scope: 'agent',
    agent_id: store.currentAgent?.id,
  })
}

// Refresh list after dialog closes
watch(() => variableStore.dialogVisible, async (visible) => {
  if (!visible && store.variablesDrawerOpen) {
    await store.loadAgentVariables()
  }
})
</script>

<style scoped>
.agent-vars-content {
  min-height: 200px;
}
.empty-state {
  text-align: center;
  padding: 40px 0;
  color: #909399;
}
.var-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.var-item {
  padding: 10px 12px;
  border-radius: 6px;
  background: #f5f7fa;
}
.var-header {
  display: flex;
  align-items: center;
  gap: 8px;
}
.var-name {
  font-family: monospace;
  font-size: 13px;
  font-weight: 600;
  color: #e94560;
}
.var-value {
  margin: 4px 0;
  font-size: 12px;
  color: #606266;
}
.var-value code {
  font-family: monospace;
  background: #fff;
  padding: 2px 6px;
  border-radius: 3px;
}
.var-actions {
  display: flex;
  gap: 4px;
}
.new-var-btn {
  margin-top: 16px;
  width: 100%;
}
</style>
