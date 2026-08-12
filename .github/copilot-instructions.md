# Copilot Instructions

- This is a Next.js frontend + FastAPI backend project.
- Keep frontend code in app/ and backend code in backend/ (agents/, core/, models/, services/, workflows/), with the FastAPI app in backend/main.py.
- Utility scripts are located in scripts/.
- Experimental or practice code should be kept in archives/.
- Issue knowledge is stored in a Supabase Postgres database (not files): the `issues` table holds metadata, the `components` table holds versioned knowledge (research/summary/timeline/sources/questions - each new version is an immutable row), and `global_docs` holds shared rubric/ranking/taxonomy docs. Access via SQLAlchemy in backend/core/ (db.py, issue.py, versioning.py, knowledge.py, global_docs.py). Schema changes go through Alembic migrations in backend/migrations/.
- Prefer small, tested changes over large rewrites.
- Keep the UI simple, clean, and consistent: clear spacing, readable typography, accessible contrast, and minimal clutter.
- Keep backend endpoints focused, predictable, and easy to test.
- Verify the frontend with npm run build after UI changes.
- Verify the backend with python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload after API changes.
- Use environment variables for secrets and do not commit them.
- Do not make large changes without updating or adding tests where appropriate.
- Avoid common AI mistakes: do not over-explain, do not add unnecessary files, do not leave code unverified, and do not claim something works without checking it.
- If a change affects behavior, verify it with the relevant test or a manual run before finishing.
