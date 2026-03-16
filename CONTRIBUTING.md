# Contributing to claw-agent-dashboard

Thank you for your interest in contributing to the claw-agent-dashboard project! This guide will help you get started.

## Prerequisites

- Node.js 20+
- Python 3.12+
- Docker (optional, for containerized development)

## Local Development

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Runs on http://localhost:5173

### Backend

```bash
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --port 8080
```

Runs on http://localhost:8080

## Code Style

- **Frontend:** Vue 3 Composition API with `<script setup>`, Element Plus components
- **Backend:** Python type hints, FastAPI conventions
- Use existing patterns in the codebase as reference

## Internationalization (i18n)

- Locale files: `frontend/src/i18n/en.js` and `frontend/src/i18n/zh.js`
- Use `const { t } = useI18n()` in components
- Add keys to both locale files when adding new user-facing strings
- Test both languages after changes

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes with clear messages
4. Push to your fork and open a Pull Request to `main`
5. Ensure the build passes (`cd frontend && npm run build`)

## Reporting Issues

- Use GitHub Issues
- Include steps to reproduce, expected vs actual behavior
- Include browser/environment details if relevant
