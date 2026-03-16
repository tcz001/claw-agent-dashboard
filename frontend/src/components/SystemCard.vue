<template>
  <div class="dashboard-card system-card">
    <div class="card-header">
      <el-icon><Cpu /></el-icon>
      <span>System</span>
    </div>
    <div class="card-body" v-if="system">
      <div class="metric">
        <span class="label">Memory</span>
        <span class="value">
          <span class="mono">{{ system.memory?.usage_pct ?? '—' }}%</span>
          <span class="secondary">{{ system.memory?.used_mb ?? 0 }}/{{ system.memory?.total_mb ?? 0 }} MB</span>
        </span>
      </div>
      <el-progress
        :percentage="system.memory?.usage_pct ?? 0"
        :stroke-width="6"
        :show-text="false"
        :color="memoryColor"
        style="margin-bottom: 8px;"
      />
      <div class="metric">
        <span class="label">Load (1m)</span>
        <span class="value mono">{{ system.load?.['1m'] ?? '—' }}</span>
      </div>
      <div class="metric">
        <span class="label">Load (5m / 15m)</span>
        <span class="value mono">{{ system.load?.['5m'] ?? '—' }} / {{ system.load?.['15m'] ?? '—' }}</span>
      </div>
    </div>
    <div class="card-body" v-else>
      <span class="no-data">No system data</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Cpu } from '@element-plus/icons-vue'

const props = defineProps({
  system: { type: Object, default: null },
})

const memoryColor = computed(() => {
  const pct = props.system?.memory?.usage_pct ?? 0
  if (pct >= 90) return '#F56C6C'
  if (pct >= 70) return '#E6A23C'
  return '#409EFF'
})
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
.card-body { padding: 12px 16px; }
.metric { display: flex; align-items: center; justify-content: space-between; padding: 4px 0; }
.label { color: var(--el-text-color-secondary); font-size: 13px; }
.value { font-size: 13px; font-weight: 500; display: flex; align-items: center; gap: 8px; }
.secondary { color: var(--el-text-color-placeholder); font-size: 12px; }
.mono { font-family: 'Cascadia Code', 'Fira Code', 'JetBrains Mono', monospace; }
.no-data { color: var(--el-text-color-placeholder); font-size: 13px; }
</style>
