# Agent Management Phase 1: Variables & Template Layer Design

Date: 2026-03-16
Status: Draft
Branch: feat/agent-management

## Overview

为 Claw Agent Dashboard 添加变量管理和模板层能力。这是 Agent Management 功能的第一阶段，后续还有 Templates 模块 UI 和 Skills 管理模块。

核心架构变化：引入**模板优先**的文件管理模式——所有 agent 文件分为模板层（存储在数据库，含 `${VAR}` 占位符）和实际文件层（渲染后写入磁盘）。变量系统支持全局和 Agent 级覆盖，密钥类型变量在 API 中掩码返回。

## Decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | 开发策略 | 分阶段：Variables + Template Layer 优先 |
| 2 | 变量作用域 | 全局 + Agent 级覆盖（agent 优先，fallback 到全局） |
| 3 | 存储方式 | 复用现有 `versions.db`，新增表 |
| 4 | 密钥处理 | API 读时掩码（`"******"`），提交新值才更新 |
| 5 | 导航位置 | 新增 "Management" 顶级 tab |
| 6 | 文件架构 | 模板优先：所有文件分模板层和实际文件层 |
| 7 | 前端展示 | 预览 = 渲染后内容，编辑 = 模板原文 |
| 8 | 模板存储 | 数据库（templates 表） |
| 9 | 保存行为 | 保存模板到 DB → 渲染 → 写入实际文件 |
| 10 | 变量联动 | 修改变量 → 树状展示影响范围 → 用户确认 → 批量重渲染 |
| 11 | Agent 关联 | 使用现有 agents 表的 id 作为外键 |

## Data Model

在现有 `versions.db` 中新增 2 张表。`base_templates` 表延后到 Templates 模块 UI 阶段实现。

### variables

```sql
CREATE TABLE IF NOT EXISTS variables (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    value       TEXT NOT NULL,
    type        TEXT NOT NULL DEFAULT 'text' CHECK(type IN ('text', 'secret')),
    scope       TEXT NOT NULL DEFAULT 'global' CHECK(scope IN ('global', 'agent')),
    agent_id    INTEGER REFERENCES agents(id),
    description TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK((scope = 'global' AND agent_id IS NULL) OR (scope = 'agent' AND agent_id IS NOT NULL))
);

-- 全局变量唯一性约束（SQLite 中 NULL != NULL，UNIQUE 无法覆盖）
CREATE UNIQUE INDEX IF NOT EXISTS idx_variables_global_unique
    ON variables(name) WHERE scope = 'global';

-- Agent 级变量唯一性约束
CREATE UNIQUE INDEX IF NOT EXISTS idx_variables_agent_unique
    ON variables(name, agent_id) WHERE scope = 'agent';
```

- `scope='global', agent_id=NULL` → 全局变量
- `scope='agent', agent_id=N` → agent 级覆盖
- 解析时优先级：agent 级 > 全局

### templates

```sql
CREATE TABLE IF NOT EXISTS templates (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id         INTEGER NOT NULL REFERENCES agents(id),
    file_path        TEXT NOT NULL,
    content          TEXT NOT NULL,
    base_template_id INTEGER,          -- 预留，Phase 2 关联 base_templates
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(agent_id, file_path)
);
```

> **Note:** `base_templates` 表及其 CRUD API 延后到 Templates 模块 UI 阶段。Phase 1 中 `base_template_id` 列始终为 NULL。

### 版本管理变化

现有 `file_versions` 表结构不变。语义变化：
- 新版本的 `content` 存储**模板内容**（非渲染后内容）
- `source` 新增值 `'template'`，标识由模板系统产生的版本
- 已有版本记录不受影响，保持原有的实际文件内容

## Backend API

### Variables — `/api/variables`

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/variables` | 列出所有全局变量（secret 值掩码） |
| `GET` | `/api/variables/agent/{agent_id}` | 获取 agent 有效变量（全局 + agent 覆盖合并） |
| `POST` | `/api/variables` | 创建变量 |
| `PUT` | `/api/variables/{id}` | 更新变量（value 为掩码值时跳过更新） |
| `DELETE` | `/api/variables/{id}` | 删除变量 |
| `GET` | `/api/variables/{id}/references` | 查询引用此变量的模板列表 |

**Request body (POST/PUT):**
```json
{
    "name": "API_KEY",
    "value": "sk-xxx",
    "type": "secret",
    "scope": "global",
    "agent_id": null,
    "description": "Main API key"
}
```

**Response (GET list):**
secret 类型的 value 返回 `"******"`。

**GET /api/variables/agent/{agent_id} 合并语义：**
返回一个扁平列表，agent 级变量完全替换同名全局变量。每个条目包含 `scope` 字段标明来源（`global` 或 `agent`）。

**DELETE /api/variables/{id} 行为：**
删除前检查模板引用。如果有模板引用该变量，返回 `affected_templates` 列表，前端弹出确认对话框提醒用户删除后 `${VAR}` 将保持为未解析的占位符。用户确认后执行删除。

**Response (PUT) — 含联动信息:**
```json
{
    "variable": { "id": 1, "name": "API_KEY", "..." : "..." },
    "affected_templates": [
        { "id": 1, "agent_name": "Jarvis", "file_path": "AGENTS.md", "ref_count": 2 },
        { "id": 3, "agent_name": "Marvin", "file_path": "AGENTS.md", "ref_count": 1 }
    ]
}
```

### Templates — `/api/templates`

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/templates/agent/{agent_id}` | 获取 agent 所有模板 |
| `GET` | `/api/templates/lookup?agent_id={id}&file_path={path}` | 按 agent + 路径查找模板（无记录时触发懒加载创建） |
| `GET` | `/api/templates/{id}` | 获取模板详情（原始内容） |
| `GET` | `/api/templates/{id}/rendered` | 获取渲染后内容 |
| `PUT` | `/api/templates/{id}` | 更新模板（+ 创建版本 + 渲染写入实际文件） |
| `POST` | `/api/templates/agent/{agent_id}` | 为 agent 创建模板 |
| `DELETE` | `/api/templates/{id}` | 删除模板 |
| `POST` | `/api/templates/{id}/apply` | 手动触发渲染写入 |
| `POST` | `/api/templates/batch-apply` | 批量渲染写入 |

**Lookup 端点**是前端从 (agent_id, file_path) 获取 template ID 的核心桥梁：
- 如果 templates 表已有记录 → 返回该模板
- 如果没有记录 → 读取实际文件内容，创建 template 记录，返回新模板
- 返回结构包含 `id`，前端后续用 `id` 调用其他 template 端点

**Batch apply request:**
```json
{ "template_ids": [1, 3, 5] }
```

> **Note:** `base_templates` CRUD API (`/api/base-templates`) 延后到 Templates 模块 UI 阶段实现。

## Template Engine

独立后端 service：`template_engine.py`

### 变量插值

```python
def render_template(template_content: str, variables: dict[str, str]) -> str:
    """将模板中的 ${VAR_NAME} 替换为变量值"""
```

- 语法：`${VAR_NAME}`，正则 `\$\{([A-Za-z_][A-Za-z0-9_]*)\}`
- 未找到变量时保留原始占位符不动，返回警告列表
- 未闭合的 `${` 不做处理（正则只匹配完整的 `${...}` 模式）
- 纯键值替换，不支持嵌套、表达式、条件逻辑
- **Secret 变量渲染**：引擎直接从数据库读取原始值进行替换，不经过 API 掩码层。API 掩码仅用于前端展示，渲染写入磁盘的文件包含真实密钥值。

### 变量解析优先级

```
1. agent 级变量（scope='agent', agent_id=该agent）
2. 全局变量（scope='global'）
```

Agent 级覆盖全局。

### 保存流程

```
用户编辑模板 → PUT /api/templates/{id}
  ├─ 保存模板内容到 templates 表
  ├─ 创建 file_versions 记录（source='template'）
  ├─ 解析该 agent 的有效变量
  ├─ 渲染模板 → 得到实际内容
  └─ 写入 agent 目录的实际文件 + 更新 tracked_files hash
```

### 变量修改联动

```
PUT /api/variables/{id}
  ├─ 立即更新 variables 表（变量值已生效）
  ├─ 扫描 templates 表，找出 content 中包含 ${该变量名} 的记录
  └─ 返回 affected_templates 列表

前端收到 → 弹出树状确认对话框
  ├─ 用户确认 → POST /api/templates/batch-apply → 重新渲染并写入实际文件
  └─ 用户取消 → 变量已更新，但实际文件仍为旧值（处于不一致状态，
  │              下次打开文件或编辑模板时会自动同步）
```

**注意：** PUT 操作是立即生效的——变量值在数据库中已更新。确认对话框只控制是否立即将新值渲染到实际文件。如果用户取消，系统处于"变量已更新、文件未同步"的临时状态，后续任何对相关模板的保存操作都会使用新变量值。

### 与 change_detector 协调

- 模板系统写入文件后同步更新 `tracked_files` 的 hash，避免误判为外部修改
- 外部直接修改文件的情况仍被检测到，此时模板与实际文件不一致
- 前端提示用户："文件已被外部修改，与模板不一致。[同步到模板] [忽略]"

## Frontend

### Navigation

新增顶级 tab "Management"，与 Dashboard、Agents 并列。

路由：`/management`，默认显示 Variables 子页面。

子标签页：Variables | Templates | Skills（后两者在后续阶段实现）。

### Management > Variables 页面

**布局：**
- 顶部工具栏：+ New Variable 按钮、作用域筛选（All/Global/Agent）、搜索框
- 主体表格：Name、Type（text/secret badge）、Value（secret 掩码）、Scope（global/agent badge）、Description、Actions（编辑/删除）

**新建/编辑对话框：**
- Variable Name（monospace input）
- Type 选择（Text / Secret radio）
- Scope 选择（Global / Agent → agent 下拉选择）
- Value 输入（secret 类型用 password input）
- Description（可选）

**变量修改联动确认对话框：**
- 树状结构展示影响范围：Agent → 目录(skill) → 文件
- 每个文件标注引用次数（×N refs）
- 底部汇总：N agents, N files, N references
- 操作按钮：Skip (update later) / Apply All

### Agents 页面改造

**编辑器模式变化：**

| Mode | Before | After |
|------|--------|-------|
| Preview | 文件原文 Markdown 渲染 | 渲染后内容（变量已替换）Markdown 渲染 |
| Edit | Monaco 显示文件原文 | Monaco 显示模板原文（含 `${VAR}` 占位符） |

**编辑器增强：**
- Monaco 自定义语法高亮：`${VAR_NAME}` 标记为特殊 token
- 鼠标悬停显示 tooltip：当前值（secret 掩码）和作用域

**API 调用变化：**

```
打开文件 → GET /api/templates/lookup?agent_id={id}&file_path={path}
           （返回模板记录，含 template.id；无记录时自动懒加载创建）
         → 用返回的 template.id：
           GET /api/templates/{id}（模板原文，编辑用）
           GET /api/templates/{id}/rendered（渲染结果，预览用）
保存文件 → PUT /api/templates/{id}
```

**外部修改提示：**
- 文件列表中显示警告标记
- 打开文件时顶部提示条："文件已被外部修改，与模板不一致。[同步到模板] [忽略]"

**Global Skills 不受影响：**
- Global Skills 文件（通过 `selectGlobalFile()` 打开）为只读，不经过模板层
- 前端在打开 Global Skill 文件时跳过 template lookup，仍使用现有的 global skills API

**Store 拆分：**
- 新增 `template` store，管理模板相关状态
- 新增 `variable` store，管理变量 CRUD
- 现有 `agent` store 通过 action 与新 store 协作

### 首次导入（懒加载）

```
用户打开文件 → 后端检查 templates 表
  ├─ 有记录 → 返回模板
  └─ 无记录 → 读取实际文件 → 创建 template 记录 → 返回
```

无需批量迁移，按需创建。

## Migration Strategy

### 数据库

`version_db.py` 的 `init_db()` 中新增 `CREATE TABLE IF NOT EXISTS` 语句。首次启动自动创建，无需迁移脚本。

### API 兼容性

现有端点保留并内部改造：
- `GET /api/agents` — 增加返回 `id` 字段（来自 agents 表），供前端获取数据库 ID
- `GET /api/agents/{name}/file` — 仍返回实际文件内容（兼容预览）
- `PUT /api/agents/{name}/file` — 内部转为保存模板 + 渲染写入

新端点 `/api/templates/*` 供 Management 页面和高级操作使用。

### 版本历史

已有 `file_versions` 记录保持原样（content = 实际文件内容）。新版本记录 content = 模板内容。混合对比正常工作（都是文本 diff）。版本列表 UI 根据 `source` 字段标注类型（`template` / `app` / `external`），帮助用户区分包含 `${VAR}` 占位符的模板版本和旧的实际文件版本。

### i18n

`en.js` 和 `zh.js` 新增 `management` section，包含 variables、templates 相关文案。

## New Files

**Backend:**
- `backend/app/routers/variables.py` — Variables API router
- `backend/app/routers/templates.py` — Templates API router (含 lookup 端点)
- `backend/app/services/variable_service.py` — Variable CRUD + 解析逻辑
- `backend/app/services/template_service.py` — Template CRUD + 渲染 + 联动
- `backend/app/services/template_engine.py` — 变量插值引擎

**Frontend:**
- `frontend/src/views/ManagementView.vue` — Management 页面
- `frontend/src/components/VariablesPanel.vue` — Variables 子页面
- `frontend/src/components/VariableDialog.vue` — 新建/编辑变量对话框
- `frontend/src/components/ImpactTreeDialog.vue` — 变量联动确认对话框（树状结构）
- `frontend/src/stores/variable.js` — Variable store
- `frontend/src/stores/template.js` — Template store

**Modified Files:**
- `backend/app/main.py` — 注册新 routers
- `backend/app/services/version_db.py` — init_db 新增表创建
- `backend/app/routers/agents.py` — 内部改造文件读写逻辑
- `backend/app/services/file_service.py` — 集成模板层
- `backend/app/services/change_detector.py` — 协调模板系统
- `frontend/src/router/index.js` — 新增 /management 路由
- `frontend/src/components/AppLayout.vue` — 新增 Management tab
- `frontend/src/components/FileViewer.vue` — 编辑器模式改造
- `frontend/src/components/CodeEditor.vue` — 变量高亮增强
- `frontend/src/stores/agent.js` — 与 template store 协作
- `frontend/src/api/index.js` — 新增 API 函数
- `frontend/src/i18n/en.js` — management section
- `frontend/src/i18n/zh.js` — management section
