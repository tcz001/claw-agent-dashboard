<template>
  <div class="dashboard-card events-card">
    <div class="card-header">
      <el-icon><Bell /></el-icon>
      <span>Events</span>
      <span class="card-count" v-if="events.length">({{ events.length }})</span>
    </div>
    <div class="card-body">
      <div v-if="events.length" class="events-list">
        <div
          v-for="(event, idx) in visibleEvents"
          :key="idx"
          class="event-row"
          :class="'event-' + event.type"
        >
          <span class="event-icon">{{ event.icon }}</span>
          <span class="event-time mono">{{ formatTime(event.time) }}</span>
          <span class="event-summary">{{ event.summary }}</span>
          <el-tag v-if="event.type === 'error' || event.type === 'oom'" type="danger" size="small">{{ event.type }}</el-tag>
          <el-tag v-else-if="event.type === 'warning'" type="warning" size="small">warn</el-tag>
        </div>
        <div v-if="events.length > limit" class="show-more">
          <el-button size="small" text @click="limit += 20">
            Show more ({{ events.length - limit }} remaining)
          </el-button>
        </div>
      </div>
      <div v-else class="empty-tip">
        No events found
        <div class="empty-hint">Gateway logs may not be available or mounted</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Bell } from '@element-plus/icons-vue'

const props = defineProps({
  events: { type: Array, default: () => [] },
})

const limit = ref(30)

const visibleEvents = computed(() => props.events.slice(0, limit.value))

function formatTime(timeStr) {
  if (!timeStr) return '--:--'
  try {
    const d = new Date(timeStr)
    return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
  } catch {
    return timeStr.substring(11, 16) || '--:--'
  }
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
.card-body { padding: 0; }
.events-list { max-height: 500px; overflow-y: auto; padding: 8px 12px; }
.event-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 4px;
  border-radius: 4px;
  font-size: 13px;
  transition: background 0.15s;
}
.event-row:hover { background: var(--el-fill-color-light); }
.event-row.event-error, .event-row.event-oom { background: var(--el-color-danger-light-9); }
.event-row.event-warning { background: var(--el-color-warning-light-9); }
.event-icon { flex-shrink: 0; font-size: 14px; }
.event-time { color: var(--el-text-color-placeholder); font-size: 12px; flex-shrink: 0; min-width: 40px; }
.event-summary { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--el-text-color-regular); }
.show-more { text-align: center; padding: 8px 0; }
.empty-tip { padding: 24px 16px; text-align: center; color: var(--el-text-color-placeholder); }
.empty-hint { font-size: 12px; margin-top: 4px; color: var(--el-text-color-disabled); }
.mono { font-family: 'Cascadia Code', 'Fira Code', 'JetBrains Mono', monospace; }
</style>
