# Changelog

## v0.1.0 (2026-03-20)

### New Features
- **Agent Blueprint System** — Template-based agent creation with variable inheritance, import from existing agents, and filesystem sync
- **Agent Variables & Management** — Define text and secret variables per agent with scope support
- **Full-Text Search** — File content search across workspaces; session message search with Elasticsearch integration (optional)
- **Search Result Navigation** — Jump to and highlight search results in file viewer
- **Disk File Sync** — Detect on-disk file changes with diff review tab
- **Sidebar Refactor** — Improved layout with separated sidebar and tab navigation

### Bug Fixes
- Fix main agent not showing in dashboard
- Fix session indexer message alignment with API offset
- Fix search highlight edge cases
- Fix session indexer aiosqlite compatibility and OpenClaw transcript format parsing
- Fix auto-refresh of agent status indicators in sidebar
- Align `/new` and `/model` endpoints with native OpenClaw behavior
- Fix container UID for bind-mounted volumes
- Remove hardcoded host paths from backend services

## v0.0.1 (2026-03-16)

Initial open-source release.

### Features
- Agent workspace file browser with syntax highlighting
- Session viewer with paginated message history
- Built-in LLM-powered file translation
- File version history with diff comparison and restore
- System metrics dashboard (CPU, memory, disk, network)
- OpenClaw Gateway health monitoring
- Global skills browser
- Bilingual UI (English / Chinese)
