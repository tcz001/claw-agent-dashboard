# Dashboard 架构重构设计

## 问题

Dashboard 内容（Gateway 状态、System 资源、Events）目前挂载在 Agent 层面 — 必须先选中一个 Agent 才能看到。但这些都是全局信息，不应该绑定在某个 Agent 下。

## 决策摘要

| 决策项 | 选择 |
|--------|------|
| 顶部导航交互 | 全局替换 — Dashboard 全屏独立面板，Agents 保留 Sidebar + Main |
| Dashboard 布局 | 卡片网格 — Gateway / System / Events / Agents 概览各一块 |
| Agents 概览粒度 | 迷你卡片 — 状态圆点 + session 数 + 最近活动时间，可点击跳转 |
| Agent 默认展示 | 顶部状态栏 + Sessions split-pane，无内部 Tab |
| 实现机制 | Vue Router — 路由驱动视图切换，支持 URL 深链接 |

## 路由结构

```
/                → 重定向到 /dashboard
/dashboard       → DashboardView（全屏卡片网格）
/agents          → AgentsView（Sidebar + Main，无选中 Agent）
/agents/:name    → AgentsView（Sidebar + Main，选中指定 Agent）
```

AppLayout 的 Header 包含 Tab 导航（Dashboard / Agents），绑定到当前路由。Header 下方渲染 `<router-view />`。

路由参数格式：`:name` 使用短名称（如 `developer`），不含 `workspace-` 前缀。Agent 目录名 `workspace-developer` 与路由参数 `developer` 之间的映射在 `selectAgentByName()` 内部处理。

路由参数驱动 Agent 选择：
- 进入 `/agents/developer` → AgentsView 的 route watcher 调用 `agentStore.selectAgentByName('developer')`
- Sidebar 点击 Agent `workspace-developer` → `router.push('/agents/developer')`（strip `workspace-` prefix）
- Dashboard 点击 Agent 迷你卡片 → `router.push('/agents/developer')`

## 页面布局

### Dashboard 页面（DashboardView）

全屏卡片网格，无 Sidebar：

```
┌─────────────────┬─────────────────┐
│  GatewayCard    │  SystemCard     │   ← 上半行：小卡片
├─────────────────┴─────────────────┤
│  AgentsOverviewCard               │   ← 中间：Agent 迷你卡片网格
├───────────────────────────────────┤
│  EventsCard                       │   ← 下方：Events 列表（占主体空间）
└───────────────────────────────────┘
```

### Agents 页面（AgentsView）

保留现有的 Sidebar + Main 布局：

```
┌──────────────┬────────────────────────────┐
│   Sidebar    │  未选 Agent → 空状态         │
│   (300px)    │  选中 Agent → AgentSessions  │
│              │    ┌─ 状态栏：名称+圆点+标签 ─┐│
│              │    ├─ Sessions split-pane ───┤│
│              │    └────────────────────────┘│
│              │  查看文件 → FileViewer        │
└──────────────┴────────────────────────────┘
```

## 组件结构

### 新建组件

| 组件 | 职责 |
|------|------|
| `DashboardView.vue` | 全局 Dashboard 全屏页面，卡片网格容器 |
| `GatewayCard.vue` | Gateway 进程状态卡片（运行状态、PID、RSS、uptime） |
| `SystemCard.vue` | 系统资源卡片（内存用量/百分比、Load） |
| `EventsCard.vue` | Events 列表卡片（时间倒序，可展开更多） |
| `AgentsOverviewCard.vue` | Agent 迷你卡片网格（状态圆点 + session 数 + 最近活动，点击跳转） |
| `AgentsView.vue` | Sidebar + Main 布局包装器（从 AppLayout 提取） |

### 改造组件

| 组件 | 变化 |
|------|------|
| `AppLayout.vue` | Header 加 Tab 导航（绑定路由），body 改为 `<router-view />`，移除直接引用 Sidebar/FileViewer |
| `AgentStatus.vue` → 重命名为 `AgentSessions.vue` | 删除 Dashboard & Events tab，删除 gateway/system summary bar，删除 Agent info card。保留：顶部状态栏（Agent 名 + 状态圆点 + 标签）+ Sessions split-pane + New Session 对话框 |
| `FileViewer.vue` | 移除 `showingStatus` 依赖。新逻辑：`store.currentAgent && !store.currentFile` 时显示 `AgentSessions`（取代之前的 `showingStatus && currentAgent`）。AgentSessions 作为 FileViewer 内部的一个视图状态保留，不抽成 AgentsView 的兄弟组件 |
| `Sidebar.vue` | Agent 点击改为 `router.push('/agents/xxx')`；状态圆点数据源从 `agentStore.fullStatus` 改为 `dashboardStore.allAgentsStatus` |

### 不变的组件

`SessionMessages.vue`、`CodeEditor.vue`、`MarkdownRenderer.vue`、`FileToolbar.vue`、`SettingsDialog.vue`

## Store 架构

### 新建：`stores/dashboard.js`

独立管理全局 Dashboard 的数据，与 Agent 数据解耦。

```
dashboard store
├── state
│   ├── gatewayStatus      // { running, pid, rss_mb, uptime_human, ... }
│   ├── systemMetrics      // { memory: {...}, swap: {...}, load: {...} }
│   ├── events             // [{ time, type, icon, summary, ... }]
│   └── allAgentsStatus    // [{ agent_name, status, sessions: [...], ... }]
│
├── actions
│   ├── loadAll()          // fetchFullStatus() + fetchRecentEvents() 并行（2 次请求）
│   │                      // fetchFullStatus() 返回 gateway + system + agents
│   │                      // fetchRecentEvents() 单独获取 events（/api/status 不含 events）
│   ├── startAutoRefresh(interval=10s)
│   └── stopAutoRefresh()
```

注意：`GET /api/status` 返回 `{ gateway, system, agents }` 但不含 events。因此 `loadAll()` 发两次请求：`fetchFullStatus()` + `fetchRecentEvents()`，并行执行。不提供单独的 `loadGateway()` / `loadSystem()` 等方法 — 目前无独立调用场景。

### agent store 变化

移除：
- `fullStatus` / `loadFullStatus()` — 移到 dashboard store
- `showingStatus` — 由路由驱动，不再需要
- `showAgentStatus()` — 依赖上述两者，一并移除

新增：
- `selectAgentByName(shortName)` — 接受短名称字符串（如 `developer`），从 `agents` 列表中查找匹配的 agent 对象（匹配 `workspace-{shortName}`），然后调用现有 `selectAgent(agentObject)`。如果 `agents` 列表为空（尚未加载完成），先 `await loadAgents()` 再查找。找不到匹配时不操作（`currentAgent` 保持 null，显示空状态）。AgentsView 的 route watcher 调用此方法。

保留：
- `agentDetail` / `loadAgentDetail()` — Agent Sessions 仍需要
- `selectAgent(agentObject)` — 保留原有签名，内部被 `selectAgentByName` 调用
- session 相关所有状态和方法 — 不变

`selectAgent()` 简化：移除 `loadFullStatus()` 调用和 `showingStatus = true` 赋值。

## 数据流

```
Dashboard 页面:
  onMounted → dashboardStore.loadAll() + startAutoRefresh(10s)
  onUnmounted → stopAutoRefresh()

Agents 页面:
  onMounted → dashboardStore.loadAll()（一次性加载，为 Sidebar 状态圆点提供数据）
  route.params.name 变化 → agentStore.selectAgentByName(name)
  选中 Agent 后 → agentStore.startStatusAutoRefresh(10s)（仅刷新 sessions）
  离开页面 → agentStore.stopStatusAutoRefresh()
```

Sidebar 状态圆点：Sidebar 从 `dashboardStore.allAgentsStatus` 读取各 Agent 状态。进入 Agents 页面时 AgentsView 会触发一次 `dashboardStore.loadAll()`，确保 Sidebar 有数据。数据不做定时刷新（Agents 页面的定时刷新仅针对选中 Agent 的 sessions），但用户切换到 Dashboard 页面时会自动获取最新数据。

## 自动刷新策略

| 视图 | 刷新内容 | 间隔 | 生命周期 |
|------|----------|------|----------|
| Dashboard | Gateway + System + Events + All Agents | 10s | DashboardView mounted/unmounted |
| Agent Sessions | agentDetail（sessions + 消息自动刷新） | 10s | AgentSessions mounted/unmounted |

## 后端兼容

零后端改动。所有需要的 API 已存在：

| API | 用途 |
|-----|------|
| `GET /api/status` | 全量状态（gateway + system + agents） |
| `GET /api/status/gateway` | 单独 gateway 状态 |
| `GET /api/status/system` | 单独 system 指标 |
| `GET /api/status/events` | Events 列表（支持 agent filter） |
| `GET /api/status/agent/{name}` | Agent 详情（sessions + 增强信息） |

Dashboard 用 `GET /api/status`（gateway + system + agents）+ `GET /api/status/events`（events）两次并行请求获取全部数据。`GET /api/status` 不含 events。

前端 `api/index.js` 已有 `fetchFullStatus`、`fetchSystemStatus`、`fetchGatewayStatus`、`fetchRecentEvents`，全部复用。

## 改动范围

| 文件 | 操作 |
|------|------|
| `package.json` | 新增 `vue-router` 依赖 |
| `main.js` | 引入 router 实例 |
| `router/index.js` | **新建** — 路由定义 |
| `stores/dashboard.js` | **新建** — 全局 dashboard store |
| `views/DashboardView.vue` | **新建** — 全屏 dashboard 页面 |
| `views/AgentsView.vue` | **新建** — Sidebar + Main 包装 |
| `components/GatewayCard.vue` | **新建** |
| `components/SystemCard.vue` | **新建** |
| `components/EventsCard.vue` | **新建** |
| `components/AgentsOverviewCard.vue` | **新建** |
| `components/AppLayout.vue` | **改造** — Header 加 Tab，body 换 router-view |
| `components/AgentStatus.vue` → `AgentSessions.vue` | **改造** — 删全局内容，加状态栏 |
| `components/FileViewer.vue` | **小改** — 组件引用更新 |
| `components/Sidebar.vue` | **小改** — Agent 点击改为 router.push |
| `stores/agent.js` | **小改** — 移除 `fullStatus`/`loadFullStatus()`/`showingStatus`/`showAgentStatus()`；新增 `selectAgentByName(shortName)` |
| `App.vue` | **小改** — 移除 `agentStore.loadFullStatus()` 调用，改为 `dashboardStore.loadAll()`（为 Sidebar 状态圆点提供初始数据） |

不动：后端所有 Python 文件、`SessionMessages.vue`、`CodeEditor.vue`、`MarkdownRenderer.vue`、`FileToolbar.vue`、`SettingsDialog.vue`。
