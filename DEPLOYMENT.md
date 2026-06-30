# LabelX Deployment Guide

This guide explains how to deploy the full LabelX stack: a FastAPI backend on Render and a React.js frontend on Vercel.

## 1. Prerequisites
Before deploying, make sure you have active accounts on:
- [Render](https://render.com/) (Backend)
- [Vercel](https://vercel.com/) (Frontend)
- [Qdrant Cloud](https://cloud.qdrant.io/) (Vector Database)
- [Tavily](https://tavily.com/) (Web Search Fallback)
- [Redis Cloud](https://redis.com/redis-enterprise-cloud/overview/) or Render Redis (Caching & History)
- [Google AI Studio](https://aistudio.google.com/) (Gemini 3.1 Flash-Lite)

## 2. Deploying the Backend (FastAPI on Render)
1. In your Render Dashboard, click **New +** > **Web Service**.
2. Connect your GitHub repository.
3. Use the following configuration:
   - **Root Directory**: `backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add the following **Environment Variables**:
   - `GEMINI_API_KEY`: Your Google AI Studio key
   - `QDRANT_URL`: Your Qdrant cluster URL
   - `QDRANT_API_KEY`: Your Qdrant API key
   - `TAVILY_API_KEY`: Your Tavily API key
   - `REDIS_URL`: Your Redis connection string
5. Click **Create Web Service**. Wait for the deployment to finish and copy the provided Render URL (e.g., `https://labelx-backend.onrender.com`).

## 3. Deploying the Frontend (React on Vercel)
1. Log in to Vercel and click **Add New** > **Project**.
2. Import your GitHub repository.
3. In the Configuration screen:
   - **Framework Preset**: Create React App (or Vite if used)
   - **Root Directory**: `frontend`
4. Add the following **Environment Variables**:
   - `REACT_APP_API_URL` (or `VITE_API_URL`): The URL of your Render backend (e.g., `https://labelx-backend.onrender.com`).
5. Click **Deploy**.

## 4. Configuring CORS
Once you have the final Vercel URL (e.g., `https://labelx-front.vercel.app`), you MUST update the backend CORS settings to allow requests from the frontend.
1. Open your backend code (`backend/main.py`).
2. Ensure the `CORSMiddleware` allows your Vercel domain, or set an environment variable `ALLOWED_ORIGINS` in Render containing your Vercel URL, and read it in `main.py`.
3. Push the update to trigger a Render redeployment.

## 5. Verification
1. Visit your Vercel frontend URL.
2. Complete the profile setup.
3. Analyze a food ingredient list and verify the SSE streaming updates work in production.
