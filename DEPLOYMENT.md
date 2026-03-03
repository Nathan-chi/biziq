# BizIQ Deployment Guide

This guide explains how to deploy your BizIQ application to the web for free.

## Project Structure
Your project is organized as follows:
- `backend/`: Python FastAPI code
- `frontend/`: React Vite code

## 1. Prepare GitHub
1. Create a new repository on GitHub.
2. Push your code:
   ```bash
   git init
   git add .
   git commit -m "Initial deploy"
   git remote add origin https://github.com/YOUR_USERNAME/biziq.git
   git push -u origin main
   ```

## 2. Deploy Backend (Render.com)
1. Sign up at [Render](https://render.com).
2. Create a **New Web Service**.
3. Connect your GitHub repository.
4. Settings:
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main_auth:app --host 0.0.0.0 --port $PORT`
5. **Environment Variables**:
   - `GROQ_API_KEY`: Your Groq API key
   - `BIZIQ_SECRET_KEY`: A long random string
   - `ALLOWED_ORIGINS`: Your Vercel URL (once deployed)

## 3. Deploy Frontend (Vercel.com)
1. Sign up at [Vercel](https://vercel.com).
2. Import your GitHub repository.
3. Settings:
   - **Root Directory**: `frontend`
   - **Framework Preset**: `Vite`
4. **Environment Variables**:
   - `VITE_API_URL`: The URL provided by Render (e.g., `https://biziq-backend.onrender.com`)

## 4. Final Polish
Update your backend's `ALLOWED_ORIGINS` environment variable on Render to match your Vercel URL to enable secure communication.
