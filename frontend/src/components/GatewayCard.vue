<template>
  <div class="dashboard-card gateway-card">
    <div class="card-header">
      <el-icon><Connection /></el-icon>
      <span>Gateway</span>
      <span class="status-dot" :class="dotClass"></span>
    </div>
    <div class="card-body">
      <template v-if="gateway?.running">
        <div class="metric">
          <span class="label">Status</span>
          <el-tag type="success" size="small">Running</el-tag>
        </div>
        <div class="metric">
          <span class="label">Uptime</span>
          <span class="value">{{ gateway.uptime_human }}</span>
        </div>
        <div class="metric">
          <span class="label">Memory</span>
          <span class="value mono">{{ gateway.rss_mb }} MB</span>
        </div>
      </template>
      <template v-else>
        <div class="metric">
          <span class="label">Status</span>
          <el-tag type="danger" size="small">Down</el-tag>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Connection } from '@element-plus/icons-vue'

const props = defineProps({
  gateway: { type: Object, default: null },
})

const dotClass = computed(() => {
  return props.gateway?.running ? 'dot-active' : 'dot-error'
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
.value { font-size: 13px; font-weight: 500; }
.mono { font-family: 'Cascadia Code', 'Fira Code', 'JetBrains Mono', monospace; }
.status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-left: auto; }
.dot-active { background: var(--el-color-success); box-shadow: 0 0 4px var(--el-color-success); }
.dot-error { background: var(--el-color-danger); box-shadow: 0 0 4px var(--el-color-danger); }
</style>
