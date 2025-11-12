# Repository Guidelines

## Project Structure & Module Organization
- ackend/: FastAPI services in 	radingagents/, HTTP handlers in pi/, settings in config/, automation in scripts/, and pytest suites in 	ests/.
- rontend/: React + Vite client under src/ with feature folders, Zustand stores, and chart helpers; public/ hosts static assets and dist/ holds build artifacts. Tailwind, ESLint, and tsconfig sit at the folder root.
- Cross-cutting docs (FRONTEND_BACKEND_INTEGRATION_GUIDE.md, reports in rchive/, .claude/ notes) capture architectural intent—review them before altering workflows or protocols.

## Build, Test, and Development Commands
- Backend env: cd backend && python -m venv .venv && .\.venv\Scripts\activate && pip install -r requirements.txt.
- API server: python start_api.py (Uvicorn + FastAPI, honors .env).
- Containers: docker compose up web mongodb redis brings up the Streamlit admin plus MongoDB/Redis defaults from docker-compose.yml.
- Frontend dev: cd frontend && npm install && npm run dev (served on http://localhost:5188).
- Production assets: 
pm run build && npm run preview; lint and type-check via 
pm run lint and 
pm run type-check.

## Coding Style & Naming Conventions
- Python: PEP 8, 4-space indent, snake_case functions, PascalCase classes, typed signatures. Use 	radingagents.utils.logging_manager.get_logger and keep modules under 500 lines.
- TypeScript: functional components, hooks prefixed with use, PascalCase files (e.g., PortfolioGrid.tsx), colocate Zustand stores in src/state/, share utilities through src/lib/.
- Formatting: run python scripts/quick_syntax_check.py before commits; frontend relies on ESLint + Prettier via 
pm run lint / 
pm run format.

## Testing Guidelines
- pytest drives suites under ackend/tests; run python -m pytest tests -v pre-commit, and scope failures with paths such as python -m pytest tests/trading/test_eastmoney_broker.py.
- Prefer fixtures over inline mocks, recycle CSVs in data/, and clear memory_db/ or Redis before stateful tests.
- Integration additions should cover LLM prompt orchestration, broker adapters, and cache fallbacks; document intentional skips in the PR.

## Commit & Pull Request Guidelines
- Use Conventional Commits (eat(frontend): 添加API错误显示), keep summaries under 72 chars, reference tickets with Refs #123.
- PRs need a narrative description, checklist of touched areas, test evidence (pytest output or 
pm run lint), and UI screenshots for frontend changes.

## Security & Configuration Tips
- Copy .env.example files locally and keep credentials out of git; CI reads sanitized configs from config/.
- Store provider secrets in config/*.json or vault tooling, never inside source modules.
- Logs in ackend/logs/ can contain client identifiers; redact before sharing.
