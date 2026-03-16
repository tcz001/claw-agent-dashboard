import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchFullStatus, fetchRecentEvents } from '../api'

export const useDashboardStore = defineStore('dashboard', () => {
  // State
  const gatewayStatus = ref(null)
  const systemMetrics = ref(null)
  const events = ref([])
  const allAgentsStatus = ref([])
  const loading = ref(false)

  let refreshInterval = null

  // Actions
  async function loadAll() {
    loading.value = true
    try {
      const [statusData, eventsData] = await Promise.all([
        fetchFullStatus(),
        fetchRecentEvents(null, 100),
      ])
      // fetchFullStatus returns { gateway, system, agents, timestamp }
      gatewayStatus.value = statusData.gateway || null
      systemMetrics.value = statusData.system || null
      allAgentsStatus.value = statusData.agents || []
      events.value = eventsData || []
    } catch (e) {
      console.error('Failed to load dashboard data:', e)
    } finally {
      loading.value = false
    }
  }

  function startAutoRefresh(intervalMs = 10000) {
    stopAutoRefresh()
    refreshInterval = setInterval(() => {
      loadAll()
    }, intervalMs)
  }

  function stopAutoRefresh() {
    if (refreshInterval) {
      clearInterval(refreshInterval)
      refreshInterval = null
    }
  }

  return {
    gatewayStatus,
    systemMetrics,
    events,
    allAgentsStatus,
    loading,
    loadAll,
    startAutoRefresh,
    stopAutoRefresh,
  }
})
