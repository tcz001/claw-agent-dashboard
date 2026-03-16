<template>
  <div class="dashboard-card agents-overview-card">
    <div class="card-header">
      <el-icon><User /></el-icon>
      <span>Agents</span>
      <span class="card-count" v-if="agents.length">({{ agents.length }})</span>
    </div>
    <div class="card-body">
      <div v-if="agents.length" class="agents-grid">
        <div
          v-for="agent in agents"
          :key="agent.agent_name"
          class="agent-mini-card"
          @click="navigateToAgent(agent.agent_name)"
        >
          <div class="mini-header">
            <span class="status-dot" :class="dotClass(agent.status)"></span>
            <span class="agent-name">{{ agent.agent_name }}</span>
          </div>
          <div class="mini-meta">
            <span>{{ agent.sessions?.length || 0 }} sessions</span>
            <span class="status-label">{{ agent.status_label }}</span>
          </div>
        </div>
      </div>
      <div v-else class="empty-tip">No agents found</div>
    </div>
  </div>
</template>

<script setup>
import { User } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'

const router = useRouter()

defineProps({
  agents: { type: Array, default: () => [] },
})

function dotClass(status) {
  const map = {
    working: 'dot-working',
    active: 'dot-active',
    idle: 'dot-idle',
    dormant: 'dot-dormant',
    error: 'dot-error',
    unknown: 'dot-unknown',
  }
  return map[status] || 'dot-unknown'
}

function navigateToAgent(agentName) {
  router.push(`/agents/${agentName}`)
}
</script>

<style scoped>
.dashboard-card {
  background: var(--el-bg-color-overlay);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;
  overflow: hidden;
}
.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  font-weight: 600;
  font-size: 14px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  background: var(--el-fill-color-light);
}
.card-count { font-weight: 400; color: var(--el-text-color-secondary); font-size: 12px; }
.card-body { padding: 12px 16px; }
.agents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
}
.agent-mini-card {
  padding: 10px 14px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}
.agent-mini-card:hover {
  border-color: var(--el-color-primary-light-5);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  background: var(--el-color-primary-light-9);
}
.mini-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.agent-name { font-weight: 600; font-size: 14px; }
.mini-meta { display: flex; align-items: center; justify-content: space-between; font-size: 12px; color: var(--el-text-color-secondary); }
.status-label { font-size: 11px; color: var(--el-text-color-placeholder); }
.status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.dot-active { background: var(--el-color-success); box-shadow: 0 0 4px var(--el-color-success); }
.dot-working { background: var(--el-color-warning); box-shadow: 0 0 4px var(--el-color-warning); animation: dot-pulse 1.5s ease-in-out infinite; }
@keyframes dot-pulse {
  0%, 100% { box-shadow: 0 0 4px var(--el-color-warning); }
  50% { box-shadow: 0 0 8px var(--el-color-warning); }
}
.dot-idle { background: var(--el-text-color-secondary); }
.dot-dormant { background: var(--el-text-color-disabled); }
.dot-error { background: var(--el-color-danger); box-shadow: 0 0 4px var(--el-color-danger); }
.dot-unknown { background: var(--el-text-color-placeholder); }
.empty-tip { text-align: center; color: var(--el-text-color-placeholder); padding: 12px; }
</style>
