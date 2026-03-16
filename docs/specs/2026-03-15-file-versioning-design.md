# 文件版本管理设计

## 问题

agent-preview 当前保存文件时直接覆盖原文件，没有任何备份或版本历史。一旦文件被改坏（无论是用户操作、OpenClaw 修改、还是外部编辑），无法回滚到之前的状态。

## 决策摘要

| 决策项 | 选择 |
|--------|------|
| 版本管理范围 | 核心文件（SOUL.md 等）+ Skills（`skills/*/` 下所有文件） |
| 存储方案 | SQLite（`/data/versions.db`），每个版本存完整内容快照 |
| Agent 标识 | Agent 表分配稳定 ID，workspace_name 可变更，版本通过 ID 关联 |
| 变更来源分类 | `app`（agent-preview 写入）/ `external`（所有其他写入）/ `restore`（恢复操作） |
| OpenClaw 识别 | 启发式：外部变更时检查是否存在活跃 `.jsonl.lock`，标记 `likely_openclaw` |
| 变更检测 | 抽象接口，初始实现为 30 秒定期哈希扫描，后续可替换为 watchdog |
| LLM 配置 | 全局默认 + 按功能覆盖（翻译、版本摘要），空值 fallback 到全局 |
| 摘要生成 | 统一异步生成；用户提供 commit msg 则跳过 LLM；可全局关闭 |
| 版本恢复 | 创建新版本（source=restore），不删除任何历史版本 |
| 前端 UI | FileToolbar 按钮 → 右侧抽屉面板，含版本列表、查看、对比、恢复 |

## 数据库 Schema

使用 SQLite，数据库文件位于 `/data/versions.db`。

### agents 表

为每个 agent 分配稳定 ID，`workspace_name` 可更新，所有版本通过 `agent_id` 关联。

```sql
CREATE TABLE agents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_name  TEXT NOT NULL UNIQUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### file_versions 表

每行是一个版本快照，存储文件完整内容。

```sql
CREATE TABLE file_versions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id        INTEGER NOT NULL REFERENCES agents(id),
    file_path       TEXT NOT NULL,            -- 相对于 agent 目录
    version_num     INTEGER NOT NULL,         -- 该文件的递增版本号（从 1 开始）
    content         TEXT NOT NULL,            -- 文件完整内容
    content_hash    TEXT NOT NULL,            -- SHA-256
    source          TEXT NOT NULL,            -- "app" | "external" | "restore"
    likely_openclaw BOOLEAN DEFAULT FALSE,
    commit_msg      TEXT,                     -- 用户手动填写（可为 NULL）
    ai_summary      TEXT,                     -- LLM 异步生成（初始为 NULL）
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(agent_id, file_path, version_num)
);

CREATE INDEX idx_versions_file ON file_versions(agent_id, file_path, created_at DESC);
CREATE INDEX idx_versions_hash ON file_versions(agent_id, file_path, content_hash);
```

### tracked_files 表

扫描器的工作表，记录每个受管文件的最新已知哈希。

```sql
CREATE TABLE tracked_files (
    agent_id      INTEGER NOT NULL REFERENCES agents(id),
    file_path     TEXT NOT NULL,
    current_hash  TEXT NOT NULL,
    last_scanned  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY(agent_id, file_path)
);
```

### 设计要点

- `version_num` 每个文件独立递增，不是全局序列
- `content_hash` 用于扫描时快速判断文件是否变化
- 恢复操作创建 `source = "restore"` 的新版本，`commit_msg` 自动填 `"Restored from version N"`

## 后端架构

新增 4 个模块，放在现有的 `backend/app/services/` 和 `backend/app/routers/` 下。

```
backend/app/
├── services/
│   ├── version_db.py          # SQLite 连接管理 + CRUD
│   ├── version_service.py     # 版本管理核心逻辑
│   ├── change_detector.py     # 变更检测抽象接口 + 哈希扫描实现
│   └── summary_service.py     # LLM 摘要异步生成
├── routers/
│   └── versions.py            # 版本管理 API
```

### version_db.py — 数据库层

职责：SQLite 连接管理和所有数据库操作。

- `init_db()`：创建表（IF NOT EXISTS），在 FastAPI startup 事件中调用
- `get_or_create_agent(workspace_name) → agent_id`：首次见到的 agent 自动创建记录
- `create_version(agent_id, file_path, content, hash, source, likely_openclaw, commit_msg) → version`
- `get_versions(agent_id, file_path, limit, offset) → (list, total)`：分页查询版本列表
- `get_version(version_id) → version`：获取单个版本完整内容
- `update_summary(version_id, summary)`：异步摘要回写
- `get_tracked_file(agent_id, file_path) → tracked_file`
- `upsert_tracked_file(agent_id, file_path, hash)`：创建或更新跟踪记录
- `get_next_version_num(agent_id, file_path) → int`：查询当前最大版本号 + 1

使用 `aiosqlite` 实现异步数据库访问。连接在应用生命周期内保持，通过模块级变量或 FastAPI 依赖注入管理。

### version_service.py — 业务逻辑层

职责：版本管理的核心业务逻辑，协调文件系统、数据库和摘要生成。

**`save_file_with_version(agent_name, path, content, commit_msg=None)`**

agent-preview 保存文件时调用：
1. 写文件到磁盘（复用现有 `file_service.write_file()`）
2. 计算内容 SHA-256
3. 在 `file_versions` 创建新版本（source="app"）
4. 更新 `tracked_files.current_hash`（避免扫描器重复检测）
5. 如果 `auto_summary` 开启且 `commit_msg` 为空，触发异步摘要

**`restore_version(version_id)`**

恢复历史版本：
1. 从数据库读取目标版本内容
2. 写回文件
3. 创建新版本（source="restore"，commit_msg="Restored from version N"）
4. 更新 `tracked_files.current_hash`

**`record_external_change(agent_id, file_path, content, hash, likely_openclaw)`**

扫描器发现外部变更时调用：
1. 创建版本（source="external"）
2. 更新 `tracked_files.current_hash`
3. 如果 `auto_summary` 开启，触发异步摘要

### change_detector.py — 变更检测

定义抽象接口，初始实现为哈希扫描。

```python
class ChangeDetector(ABC):
    @abstractmethod
    async def start(self): ...

    @abstractmethod
    async def stop(self): ...

class HashScanDetector(ChangeDetector):
    """定期哈希扫描，默认 30 秒间隔"""
```

`HashScanDetector` 的扫描逻辑：
1. 遍历所有 agent 的核心文件 + `skills/` 目录下的文件
2. 计算每个文件的 SHA-256
3. 与 `tracked_files.current_hash` 比对
4. 如果哈希变化：读取内容，检查 `.jsonl.lock` 判断 `likely_openclaw`，调用 `version_service.record_external_change()`
5. 如果文件是新发现的（不在 `tracked_files` 中）：创建初始版本（version_num=1, source="external"），加入跟踪
6. 如果 `tracked_files` 中记录的文件已不存在：可标记或忽略（不删除版本历史）

后续替换为 watchdog 时，只需新建 `WatchdogDetector(ChangeDetector)` 类，实现相同接口。

### summary_service.py — LLM 摘要

职责：异步调用 LLM 生成版本变更摘要。

- 使用 `get_llm_config("version_summary")` 获取 LLM 配置
- 输入：旧版本内容（如有）+ 新版本内容
- Prompt：要求 LLM 用一句话中文描述变更内容
- 输出：摘要文本，写入 `file_versions.ai_summary`
- 通过 `asyncio.create_task()` 在后台运行，不阻塞版本创建
- 检查 `features.auto_summary` 配置，关闭时跳过

## API 设计

新增 router `versions.py`，挂载在 `/api/versions` 前缀下。

### 版本管理端点

```
GET    /api/versions/{agent_name}/{file_path:path}
       获取文件版本列表（分页）
       Query: limit=20, offset=0
       Response: {
         versions: [
           { id, version_num, source, likely_openclaw,
             commit_msg, ai_summary, created_at }
         ],
         total: int
       }
       注：列表不返回 content 字段，减少传输量

GET    /api/versions/detail/{version_id}
       获取单个版本完整内容
       Response: {
         id, agent_id, file_path, version_num, content,
         content_hash, source, likely_openclaw,
         commit_msg, ai_summary, created_at
       }

POST   /api/versions/{agent_name}/{file_path:path}/restore
       恢复到指定版本
       Body: { version_id: int }
       Response: { new_version_id: int, version_num: int }

GET    /api/versions/{agent_name}/{file_path:path}/diff
       两个版本间的 diff
       Query: from_version_id, to_version_id
       Response: { diff: string }
       格式：unified diff
```

### 现有 API 改动

`PUT /api/agents/{name}/file` 的 request body 新增可选字段：

```
PUT    /api/agents/{name}/file?path=...
       Body: { content: string, commit_msg?: string }
       改为调用 version_service.save_file_with_version()
       Response: { success: bool, version_num?: int }
```

### 设置 API 扩展

```
GET    /api/settings
       Response 结构变为:
       {
         "llm": {
           "default": {
             "openai_base_url": "...",
             "api_key": "sk-***",
             "model_name": "gpt-4o-mini"
           },
           "overrides": {
             "translation": { ... },
             "version_summary": { ... }
           }
         },
         "features": {
           "auto_summary": true
         }
       }

PUT    /api/settings
       Body: 同上结构
       overrides 中字段为空 = 使用 default
```

## LLM 配置架构

### 配置文件结构

`/data/config.json` 从扁平结构升级为嵌套结构：

```json
{
  "llm": {
    "default": {
      "openai_base_url": "https://api.openai.com/v1",
      "api_key": "sk-...",
      "model_name": "gpt-4o-mini"
    },
    "overrides": {
      "translation": {},
      "version_summary": {}
    }
  },
  "features": {
    "auto_summary": true
  }
}
```

### 配置解析逻辑

改造 `services/config.py`：

```python
def get_llm_config(purpose: str = "default") -> dict:
    """获取指定功能的 LLM 配置，空值 fallback 到 default"""
    config = load_config()
    default = config["llm"]["default"]
    if purpose == "default":
        return dict(default)
    override = config["llm"].get("overrides", {}).get(purpose, {})
    result = dict(default)
    for key, value in override.items():
        if value:
            result[key] = value
    return result
```

### 向后兼容

启动时检测旧格式（扁平的 `openai_base_url` / `api_key` / `model_name`），自动迁移为新的嵌套结构。迁移后写回文件。

### 功能开关

`features.auto_summary`：默认 `true`。设为 `false` 时所有版本创建不触发 LLM 摘要生成。

## 前端 UI

### 设置对话框改造（SettingsDialog.vue）

顶部新增下拉框，选项：`全局默认` / `翻译` / `版本摘要`。

- 选 `全局默认`：显示三个字段（Base URL、API Key、Model），行为和现有一致
- 选功能覆盖：同样三个字段，留空 = 使用全局默认值，填值 = 覆盖。每个字段下方灰色文字提示当前全局默认值
- 底部新增 `自动生成摘要` 开关（对应 `features.auto_summary`）

### 版本历史入口（FileToolbar.vue）

在 FileToolbar 新增"版本历史"按钮（时钟图标），仅当前文件属于受管范围（核心文件或 skills）时显示。

### 版本历史抽屉（新组件 VersionDrawer.vue）

从右侧滑出，宽度约 400px。

```
┌─────────────────────────────────┐
│  版本历史 — SOUL.md        [×] │
│─────────────────────────────────│
│  ▸ v5  3分钟前  [app]          │
│    "调整了 agent 的语气风格"     │
│                                 │
│  ▸ v4  1小时前  [external 🦞]   │
│    "新增了工具使用指南段落"       │
│                                 │
│  ▸ v3  昨天  [restore]          │
│    "Restored from version 1"    │
│                                 │
│  ▸ v2  昨天  [app]              │
│    "重写了开场白部分"            │
│                                 │
│  ▸ v1  2天前  [app]             │
│    ⏳ 生成摘要中...              │
│─────────────────────────────────│
│         加载更多...              │
└─────────────────────────────────┘
```

**版本条目内容**：
- 版本号 + 相对时间 + 来源标签（`app` 绿色 / `external` 蓝色 / `restore` 橙色）
- `likely_openclaw` 为 true 时在 external 标签旁显示 🦞 图标
- 摘要文字：显示 `commit_msg`（优先）或 `ai_summary`，生成中显示 loading 动画
- 展开后显示操作按钮：
  - **查看**：在 FileViewer 中以只读模式预览该版本内容
  - **对比**：和当前版本做 diff
  - **恢复**：弹出确认对话框，确认后调用 restore API

**Diff 视图**：点击"对比"后抽屉内容切换为 diff 视图，使用 unified diff 格式渲染（绿色/红色行高亮），顶部有"返回列表"按钮。

### 保存对话框改造

现有的保存确认弹窗中新增可选的 commit message 输入框（placeholder："描述本次修改（可选，留空将自动生成）"）。

### 新增前端文件

```
frontend/src/
├── components/
│   └── VersionDrawer.vue      # 版本历史抽屉组件
├── api/
│   └── index.js               # 新增版本相关 API 调用
├── stores/
│   └── agent.js               # 新增版本历史状态管理
```

### Store 扩展（agent.js）

新增状态和 actions：
- `versionDrawerOpen`：抽屉开关
- `versionList`：当前文件的版本列表
- `versionTotal`：总版本数
- `fetchVersions(agentName, filePath, limit, offset)`
- `fetchVersionDetail(versionId)`
- `restoreVersion(agentName, filePath, versionId)`
- `fetchDiff(agentName, filePath, fromId, toId)`

## 端到端数据流

### 场景 1：用户在 agent-preview 中保存文件

```
用户点击保存（可选填 commit msg）
  → PUT /api/agents/{name}/file  { content, commit_msg? }
  → version_service.save_file_with_version()
      1. 写文件到磁盘
      2. 计算 SHA-256
      3. 创建版本记录 (source="app")
      4. 更新 tracked_files.current_hash
      5. if auto_summary 开启 且 commit_msg 为空:
           asyncio.create_task(summary_service.generate(...))
  → 返回 { success, version_num }
```

### 场景 2：定期扫描发现外部变更

```
HashScanDetector（每 30 秒）
  → 遍历所有 agent 核心文件 + skills/
  → 计算 SHA-256，与 tracked_files 比对
  → hash 变化时:
      1. 读取新内容
      2. 检查 .jsonl.lock → likely_openclaw
      3. version_service.record_external_change()
      4. if auto_summary 开启:
           asyncio.create_task(summary_service.generate(...))
  → 新文件: 创建初始版本 + 加入 tracked_files
```

### 场景 3：用户恢复历史版本

```
用户在抽屉点击"恢复" → 确认弹窗
  → POST /api/versions/{agent}/{path}/restore  { version_id }
  → version_service.restore_version()
      1. 读取目标版本内容
      2. 写回文件
      3. 创建新版本 (source="restore")
      4. 更新 tracked_files.current_hash
  → 返回 { new_version_id, version_num }
  → 前端刷新版本列表 + FileViewer 内容
```

## 依赖变更

### 后端

- 新增 `aiosqlite`：异步 SQLite 访问（`requirements.txt`）
- Python 标准库 `hashlib`、`difflib`：哈希计算和 diff 生成，无需额外安装

### 前端

- 无新依赖。Diff 渲染可用现有的 `highlight.js` 或简单的 CSS 行高亮实现

## Docker 配置

`/data/` 目录已有 volume 挂载，`versions.db` 放在此目录下无需额外配置。数据随 volume 持久化。
