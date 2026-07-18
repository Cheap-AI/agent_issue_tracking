# agent_issue_tracking

This project is being built as a small MVP for an issue-tracking and news-monitoring app.
The goal is to reach a deployable version where:
- the frontend is hosted on Vercel
- the backend is hosted on Render
- they can talk to each other over HTTP

## Recommended order of work

1. Local MVP foundation
   - confirm the frontend can call the backend locally
   - confirm the backend returns simple JSON

2. Backend deployment
   - deploy the FastAPI app to Render
   - verify the health endpoint is publicly reachable

3. Frontend deployment
   - deploy the Next.js app to Vercel
   - point the frontend to the live backend URL using environment variables

4. Connect frontend and backend in production
   - fetch data from the backend in the browser
   - verify the UI shows the backend response

5. Add the first real feature
   - list issues or documents
   - allow a simple create flow
   - optionally add AI summarization later

## Local development

### Frontend

From the project root:

```bash
npm install
npm run dev
```

### Backend

From the project root:

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r api/requirements.txt
python -m uvicorn api.index:app --host 127.0.0.1 --port 8000 --reload
```

## MVP target

The first successful MVP should include:
- a live frontend URL on Vercel
- a live backend URL on Render
- a simple page that fetches data from the backend
- a visible response rendered in the browser

## Deployment target

- Frontend: Vercel
- Backend: Render
- Database: Supabase or Neon later
- AI: OpenAI later

## Notes

- The frontend is currently built with Next.js and React.
- The backend is currently a minimal FastAPI service.
- For production, replace local SQLite with a managed database.
