# Deployment Guide

## Backend (Render)

1. **Deploy backend to Render:**
   - Connect your GitHub repository
   - Set build command: `pip install -r backend/requirements.txt`
   - Set start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - Root directory: Leave blank (repo root)

2. **Set environment variables in Render:**
   - `DATABASE_URL` - Your Supabase Postgres connection string
   - `OPENAI_API_KEY` - OpenAI API key for embeddings and LLM
   - `TAVILY_API_KEY` - Tavily API key for web search
   - `PERPLEXITY_API_KEY` - (Optional) Perplexity API key

3. **Note your backend URL:**
   - Example: `https://agent-issue-tracking.onrender.com`
   - You'll need this for frontend configuration

## Frontend (Vercel)

1. **Configure Vercel project settings:**
   - Go to Project Settings → Build & Development Settings
   - Set **Root Directory**: `frontend`
   - Framework: Next.js (should auto-detect)
   - Build Command: `npm run build` (default)
   - Output Directory: `.next` (default)

2. **Set environment variables in Vercel:**
   - Go to Project Settings → Environment Variables
   - Add: `NEXT_PUBLIC_API_BASE_URL` = `https://your-backend-url.onrender.com/api`
   - **Important:** Include `/api` at the end since all backend routes use this prefix
   - Select: Production, Preview, Development (all environments)
   - Click Save

3. **Redeploy:**
   - Vercel will automatically redeploy after adding environment variables
   - Or trigger manual redeploy from Deployments tab

## Verify Deployment

1. **Check backend is running:**
   ```bash
   curl https://your-backend-url.onrender.com/api/health
   ```

2. **Check frontend can reach backend:**
   - Visit your Vercel URL
   - Open browser DevTools → Network tab
   - Should see successful requests to your Render backend
   - Should see issue data displayed

## Troubleshooting

### Frontend shows "Failed to fetch"
- **Cause**: `NEXT_PUBLIC_API_BASE_URL` not set in Vercel
- **Fix**: Add the environment variable and redeploy

### CORS errors in browser console
- **Cause**: Backend CORS config doesn't allow your Vercel URL
- **Fix**: Add your Vercel URL to `allow_origins` in `backend/main.py`

### Backend returns 404 for all routes
- **Cause**: Routes are defined at `/api/*` but base URL doesn't include `/api`
- **Fix**: Backend routes already include `/api` prefix, no change needed

## Local Development

### Backend:
```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### Frontend:
```bash
cd frontend
npm install
npm run dev
```

In development, the frontend uses `/api` which is proxied to `localhost:8000` by `next.config.js`.

## Environment Variable Discovery

**To find all environment variables used in the codebase:**

Backend:
```bash
grep -r "process.env\|os.getenv\|os.environ" backend/
```

Frontend:
```bash
grep -r "process.env\." frontend/src/
```

Always document new environment variables in the appropriate `.env.example` file.
