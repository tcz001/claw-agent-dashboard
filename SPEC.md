# Agent Preview Tool — 需求规格

## 概述
一个 Web 工具，用于预览和管理 OpenClaw Agent 的配置文件和 Skills。

## 核心功能

### 1. Agent 列表
- 扫描 `/agents/` 目录（Docker 容器内路径）下所有 `workspace-*` 目录
- 每个 workspace 即一个 Agent
- 展示 Agent 名称（从目录名或 IDENTITY.md 提取）

### 2. Agent 核心文件查看
每个 Agent 展示以下核心文件（如果存在）：
- `SOUL.md` — 人设
- `USER.md` — 用户信息
- `AGENTS.md` — 开发规范
- `IDENTITY.md` — 身份信息
- `TOOLS.md` — 工具配置
- `HEARTBEAT.md` — 心跳配置
- `BOOTSTRAP.md` — 启动配置
- 其他 `.md` 文件

### 3. Skills 浏览
- 列出每个 Agent 的 `skills/` 目录下所有 skill
- 每个 skill 可展开查看 **所有文件的完整内容**（SKILL.md + 所有子文件/子目录）
- Markdown 文件渲染为富文本，代码文件语法高亮

### 4. 翻译功能
- 支持将任意文件翻译为中文
- 使用 OpenAI 兼容 API（可配置 base_url, api_key, model_name）
- 翻译后的文件保存到 `/data/agents/<agent-name>/` 目录（对应宿主机的 data 目录）
- 如果已有翻译版本，优先展示翻译版本，同时可切换查看原文

### 5. 在线编辑 + 一键复制
- 文件内容支持在线编辑（编辑器，非直接写回原文件）
- 编辑后提供 **一键复制** 按钮（复制到剪贴板）
- **不要写回原文件** — 用户自己去覆盖
- 同时显示文件在宿主机上的实际路径，方便用户定位

### 6. 设置页面
- 配置 LLM 翻译参数：openai_base_url、api_key、model_name
- 配置持久化（保存到 `/data/config.json`）

## 技术架构

### 后端
- Python FastAPI
- 文件系统扫描 + Markdown 处理
- OpenAI 兼容 API 调用（翻译）

### 前端
- 现代 SPA（推荐 Vue 3 + Vite，或 React）
- Markdown 渲染 + 代码高亮
- Monaco Editor 或 CodeMirror 用于编辑
- 响应式布局

### Docker 部署

```yaml
services:
  agent-preview:
    build: .
    ports:
      - "8080:8080"
    volumes:
      # Agent 文件 — readonly
      - ~/.openclaw:/agents:ro
      # 翻译文件 + 配置 — 可写
      - ./data:/data
    environment:
      - AGENTS_DIR=/agents
      - DATA_DIR=/data
```

### 目录映射
- 容器内 `/agents/` → 宿主机 `~/.openclaw/`（只读）
- 容器内 `/data/` → 宿主机 data 目录（可写，存翻译和配置）
- Agent 发现：扫描 `/agents/workspace-*`

## UI 布局建议
- 左侧边栏：Agent 列表 + 展开的 Skills 树
- 右侧主区域：文件内容查看/编辑
- 顶部：翻译/原文切换、设置入口
- 文件内容区域底部：文件路径 + 一键复制按钮

## 非功能需求
- 启动快，首屏加载 < 2s
- 文件内容按需加载（不要一次性加载所有文件）
- 支持大文件（skill 可能有很多子文件）
