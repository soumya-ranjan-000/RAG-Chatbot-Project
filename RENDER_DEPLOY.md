# Render Deployment Guide

## Quick Start with render.yaml

The `render.yaml` file in the root directory defines both services. To deploy:

1. **Push to GitHub** (Render requires a Git repository)
   ```bash
   git add .
   git commit -m "Add Render configuration"
   git push origin main
   ```

2. **Connect to Render**
   - Go to https://dashboard.render.com
   - Click "New +" → "Blueprint"
   - Connect your GitHub repository
   - Select the branch with `render.yaml`
   - Click "Create Resources"

## Manual Render Dashboard Setup (Alternative)

If you prefer to configure manually without render.yaml:

### PSS (Passenger Service System) Service
1. **Create Web Service**
   - Name: `rag-chatbot-pss`
   - Environment: `Python 3.13`
   - Build Command: `cd pss_system && pip install -r requirements.txt`
   - Start Command: `cd pss_system && uvicorn main:app --host 0.0.0.0 --port $PORT`
   
2. **Environment Variables**
   - `SUPABASE_URL` → Your PSS Supabase project URL
   - `SUPABASE_SERVICE_ROLE_KEY` → Your PSS Supabase service role API key

### Backend Service
1. **Create Web Service**
   - Name: `rag-chatbot-backend`
   - Environment: `Python 3.13`
   - Build Command: `cd app && pip install -r requirements.txt`
   - Start Command: `cd app && uvicorn app:app --host 0.0.0.0 --port $PORT`
   
2. **Environment Variables**
   - `OPENAI_API_KEY` → Your OpenAI API key
   - `AWS_ACCESS_KEY_ID` → Your AWS access key
   - `AWS_SECRET_ACCESS_KEY` → Your AWS secret key
   - `SUPABASE_URL` → Your Supabase project URL
   - `SUPABASE_KEY` → Your Supabase API key
   - `PSS_API_URL` → `https://rag-chatbot-pss.onrender.com` (use your deployed PSS URL)


### Frontend Service
1. **Create Web Service**
   - Name: `rag-chatbot-frontend`
   - Environment: `Node 18+`
   - Build Command: `cd frontend && npm install && npm run build`
   - Start Command: `cd frontend && npx serve -s dist -l $PORT`
   
2. **Environment Variables**
   - `VITE_API_URL` → `https://rag-chatbot-backend.onrender.com` (use your backend URL)

## Build & Start Commands by Service

### PSS Service (FastAPI)
```bash
# Build (run in /pss_system)
pip install -r requirements.txt

# Start (run in /pss_system)
uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Backend (FastAPI)
```bash
# Build (run in /app)
pip install -r requirements.txt


# Start
uvicorn app:app --host 0.0.0.0 --port $PORT
```

### Frontend (React + Vite + Node.js Server)
```bash
# Build
npm install
npm run build

# Start (Development)
npm run dev

# Start (Production)
npm start
```

**Production start** uses a Node.js Express server (`server.js`) that:
- Serves static files from the `dist/` directory
- Handles SPA routing (all routes return `index.html`)
- Respects the `$PORT` environment variable

## Environment Variables for Production

### PSS Service (.env for Render)
```
SUPABASE_URL=https://...supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...
```

### Backend (.env for Render)
```
OPENAI_API_KEY=sk-...
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
SUPABASE_URL=https://...supabase.co
SUPABASE_KEY=eyJhbGc...
PSS_API_URL=https://rag-chatbot-pss.onrender.com
```

### Frontend (.env.production)
```
VITE_API_URL=https://rag-chatbot-backend.onrender.com
```


## Troubleshooting

### Frontend build fails
- Ensure `npm run build` works locally: `npm run build`
- Check TypeScript errors: `npm run build` should compile without errors
- Verify all dependencies in package.json

### Backend won't start
- Check Python version compatibility: `python --version`
- Test locally: `uvicorn app:app --host 0.0.0.0 --port 3000`
- Verify all env vars are set in Render dashboard

### CORS errors in production
- Backend CORS is configured to accept requests from frontend
- Ensure `VITE_API_URL` matches your backend service URL exactly

## Notes

- **Port**: Render assigns a dynamic port via `$PORT` environment variable
- **Memory**: Free tier has 0.5GB, paid plans have more
- **Build time**: Initial build can take 2-5 minutes
- **Auto-deploy**: Render auto-deploys when you push to GitHub (if connected)
