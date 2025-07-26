# FinVault Deployment Guide - Render.com

## Prerequisites
- Git repository with your FinVault code
- Render.com account
- PostgreSQL database (can use Render's managed PostgreSQL)
- MongoDB Atlas cluster
- Redis instance (can use Render's managed Redis)

## Deployment Steps

### 1. Push Code to Git
```bash
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

### 2. Deploy Backend Service

1. **Go to Render Dashboard** → **New** → **Web Service**
2. **Connect your Git repository**
3. **Configure Backend Service:**
   - **Name:** `finvault-backend`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r backend/requirements.txt`
   - **Start Command:** `cd backend && gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`
   - **Plan:** Free (or paid for production)

4. **Add Environment Variables:**
   ```
   POSTGRES_URI=postgresql+asyncpg://user:password@host:port/dbname
   MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/dbname
   REDIS_URL=redis://localhost:6379/0
   JWT_SECRET=your_secure_jwt_secret_here
   EMAIL_SENDER=your@email.com
   EMAIL_PASSWORD=your_email_password
   FRONTEND_ORIGINS=https://your-frontend-url.onrender.com
   ```

### 3. Deploy Frontend Service

1. **Go to Render Dashboard** → **New** → **Static Site**
2. **Connect your Git repository**
3. **Configure Frontend Service:**
   - **Name:** `finvault-frontend`
   - **Build Command:** `cd frontend && npm install && npm run build`
   - **Publish Directory:** `frontend/dist/public`
   - **Plan:** Free

4. **Add Environment Variables:**
   ```
   VITE_API_URL=https://your-backend-url.onrender.com
   ```

### 4. Update CORS Settings

After both services are deployed:
1. Update `FRONTEND_ORIGINS` in backend with your frontend URL
2. Update `VITE_API_URL` in frontend with your backend URL
3. Redeploy both services

## Environment Variables Reference

### Backend (.env)
```bash
POSTGRES_URI=postgresql+asyncpg://user:password@host:port/dbname
MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/dbname
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=your_secure_jwt_secret_here
EMAIL_SENDER=your@email.com
EMAIL_PASSWORD=your_email_password
FRONTEND_ORIGINS=https://your-frontend-url.onrender.com
```

### Frontend (.env)
```bash
VITE_API_URL=https://your-backend-url.onrender.com
```

## Gunicorn Configuration

The backend uses Gunicorn with Uvicorn workers for production:

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
```

**Parameters:**
- `-w 4`: 4 worker processes
- `-k uvicorn.workers.UvicornWorker`: Use Uvicorn worker class for ASGI support
- `--bind 0.0.0.0:$PORT`: Bind to all interfaces on the specified port

## Troubleshooting

### Common Issues:
1. **Build Failures:** Check build logs for missing dependencies
2. **CORS Errors:** Ensure `FRONTEND_ORIGINS` is set correctly
3. **Database Connection:** Verify database URLs and credentials
4. **Port Issues:** Ensure using `$PORT` environment variable
5. **Worker Issues:** Check Gunicorn logs for worker process errors

### Logs:
- Check Render dashboard for build and runtime logs
- Backend logs: Render dashboard → Backend service → Logs
- Frontend logs: Render dashboard → Frontend service → Logs

## Production Considerations

1. **Upgrade to Paid Plans** for better performance
2. **Use Render's Managed Databases** for PostgreSQL and Redis
3. **Set up Custom Domains** for production URLs
4. **Configure SSL Certificates** (automatic with Render)
5. **Set up Monitoring and Alerts**
6. **Adjust Gunicorn workers** based on your plan's CPU cores 