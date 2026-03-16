# Agent Preview Tool — 设计文档

## 整体架构

```
┌────────────────────────────────────────────────────────┐
│                    Docker Container                     │
│                                                        │
│  ┌──────────────┐     ┌────────────────────────────┐  │
│  │   Frontend    │     │        Backend             │  │
│  │  Vue3+Vite   │────▶│      FastAPI :8080         │  │
│  │ (静态文件)    │     │                            │  │
│  └──────────────┘     │  /api/agents   文件扫描     │  │
│                       │  /api/translate LLM翻译     │  │
│                       │  /api/settings 配置管理     │  │
│                       └─────┬──────────┬───────────┘  │
│                             │          │               │
│                     ┌───────▼──┐ ┌─────▼─────┐        │
│                     │ /agents/ │ │  /data/    │        │
│                     │ (只读)   │ │  (可写)    │        │
│                     └──────────┘ └───────────┘        │
└────────────────────────────────────────────────────────┘
```

**单容器部署**：FastAPI 同时提供 API 和前端静态文件服务，监听 8080 端口。

## 目录结构

```
agent-preview/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI 入口，挂载静态文件 + API路由
│   │   ├── config.py            # 环境变量配置
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── agents.py        # Agent列表 + 文件读取
│   │   │   ├── translate.py     # 翻译功能
│   │   │   └── settings.py      # 设置管理
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── scanner.py       # 扫描 /agents/workspace-* 目录
│   │       ├── file_service.py  # 文件读取、类型检测、路径映射
│   │       ├── translate.py     # OpenAI 兼容 API 翻译
│   │       └── config.py        # config.json 读写
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── main.js
│   │   ├── App.vue
│   │   ├── api/
│   │   │   └── index.js         # Axios API 客户端
│   │   ├── stores/
│   │   │   ├── agent.js         # Agent 状态管理 (Pinia)
│   │   │   └── settings.js      # 设置状态管理
│   │   ├── components/
│   │   │   ├── AppLayout.vue    # 整体布局
│   │   │   ├── Sidebar.vue      # 左侧栏：Agent列表 + Skills树
│   │   │   ├── FileViewer.vue   # 主内容区：文件查看
│   │   │   ├── MarkdownRenderer.vue  # Markdown 渲染
│   │   │   ├── CodeEditor.vue   # Monaco Editor 封装
│   │   │   ├── FileToolbar.vue  # 文件操作栏：翻译/复制/路径
│   │   │   └── SettingsDialog.vue    # 设置弹窗
│   │   └── utils/
│   │       └── highlight.js     # 代码高亮配置
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── Dockerfile
├── docker-compose.yml
├── SPEC.md
├── DESIGN.md
└── README.md
```

## API 设计

### Agent 相关

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/agents` | 列出所有 Agent（名称、目录名） |
| GET | `/api/agents/{name}/files` | 列出某 Agent 的核心文件 + 其他 .md 文件 |
| GET | `/api/agents/{name}/skills` | 列出某 Agent 的 Skills 树 |
| GET | `/api/agents/{name}/file` | 读取指定文件内容 `?path=relative/path` |
| GET | `/api/agents/{name}/skill-files/{skill}` | 获取某 skill 下所有文件列表 |

### 翻译相关

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/translate` | 翻译文件内容 `{agent, path}` |
| GET | `/api/translate/{agent}` | 获取翻译版本 `?path=relative/path` |
| GET | `/api/translate/{agent}/exists` | 检查翻译是否已存在 `?path=relative/path` |

### 设置相关

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/settings` | 获取当前设置 |
| PUT | `/api/settings` | 更新设置 |

## 数据模型

```python
# Agent
class AgentInfo(BaseModel):
    name: str            # 目录名 e.g. "workspace-jarvis"
    display_name: str    # 从 IDENTITY.md 提取或目录名
    path: str            # 容器内路径
    host_path: str       # 宿主机路径

# 文件树节点
class FileNode(BaseModel):
    name: str
    path: str            # 相对于 agent 根目录的路径
    type: str            # "file" | "directory"
    children: list[FileNode] | None = None

# 文件内容
class FileContent(BaseModel):
    path: str
    name: str
    content: str
    language: str        # "markdown" | "python" | "yaml" | "json" | ...
    host_path: str       # 宿主机完整路径
    has_translation: bool

# 设置
class Settings(BaseModel):
    openai_base_url: str = ""
    api_key: str = ""
    model_name: str = "gpt-4o-mini"

# 翻译请求
class TranslateRequest(BaseModel):
    agent: str
    path: str
```

## 前端设计

### 布局

```
┌─────────────────────────────────────────────────────┐
│ 🔧 Agent Preview Tool                  [⚙ 设置]    │
├──────────────┬──────────────────────────────────────┤
│              │  📄 SOUL.md          [原文|翻译] [翻] │
│ 📦 Agents   │──────────────────────────────────────│
│              │                                      │
│ ▶ workspace- │  # Character                        │
│   jarvis     │                                      │
│   ├ SOUL.md  │  You are Jarvis, an AI assistant    │
│   ├ USER.md  │  with a focus on...                 │
│   ├ AGENTS.md│                                      │
│   ├ TOOLS.md │                                      │
│   └ Skills   │                                      │
│     ├ sk-abc │                                      │
│     └ sk-def │──────────────────────────────────────│
│              │  📋 ~/.openclaw/...      │
│ ▶ workspace- │  [📋 复制内容] [✏️ 编辑]             │
│   marvin     └──────────────────────────────────────┤
└──────────────────────────────────────────────────────┘
```

### 核心交互

1. **左侧栏**：可折叠的 Agent 树，点击文件名在右侧显示内容
2. **右侧主区域**：
   - 查看模式：Markdown 渲染 / 代码高亮
   - 编辑模式：Monaco Editor
3. **工具栏**：原文/翻译切换、翻译按钮、复制按钮、编辑按钮
4. **底部信息**：宿主机文件路径

### 关键组件

- **MarkdownRenderer**：使用 `markdown-it` + `highlight.js` 渲染 Markdown
- **CodeEditor**：使用 `monaco-editor` 提供代码编辑，只读模式 + 编辑模式切换
- **Sidebar**：树形结构，Agent → Core Files + Skills → Skill Files

## 翻译流程

```
用户点击"翻译" → 前端 POST /api/translate
    → 后端读取原文件内容
    → 调用 OpenAI 兼容 API 翻译为中文
    → 保存到 /data/agents/{agent-name}/{相同路径}
    → 返回翻译结果
    → 前端自动切换到翻译视图
```

翻译存储结构：
```
/data/
├── config.json
└── agents/
    └── workspace-jarvis/
        ├── SOUL.md              # SOUL.md 的翻译
        ├── skills/
        │   └── sk-abc/
        │       └── SKILL.md     # skill 文件的翻译
        └── ...
```

## Docker 构建

**多阶段构建**：

```dockerfile
# Stage 1: 构建前端
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/ .
RUN npm ci && npm run build

# Stage 2: 运行
FROM python:3.12-slim
WORKDIR /app
COPY backend/ ./backend/
COPY --from=frontend-build /app/frontend/dist ./static/
RUN pip install -r backend/requirements.txt
EXPOSE 8080
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

FastAPI 挂载 `/static` 作为静态文件服务，SPA 路由 fallback 到 `index.html`。

## 非功能性实现

| 需求 | 方案 |
|------|------|
| 首屏 < 2s | Vite 构建优化 + 代码分割，Monaco 异步加载 |
| 按需加载 | 文件内容点击时才请求 API |
| 大文件支持 | 虚拟滚动（大文件用 Monaco），分页加载 |

## 实现顺序

1. **后端基础**：FastAPI 项目结构 + Agent 扫描 + 文件读取 API
2. **前端基础**：Vue 3 项目 + 布局 + 侧边栏 + Agent 列表
3. **文件查看**：Markdown 渲染 + 代码高亮
4. **在线编辑**：Monaco Editor 集成 + 复制功能
5. **翻译功能**：设置页 + OpenAI API 调用 + 翻译存储
6. **Docker 部署**：Dockerfile + docker-compose.yml
