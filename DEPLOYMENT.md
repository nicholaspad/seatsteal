# SeatSteal Vercel Deployment Guide

This guide covers deploying the SeatSteal frontend and backend to Vercel as separate projects.

## Architecture Overview

- **Frontend**: React + Vite application (`seatsteal/` directory)
- **Backend**: FastAPI Python application (`webapp/` directory)
- **Scrapers & Notifications**: Deployed separately to AWS EC2 (not covered here)

## Local Development

Before deploying to production, you can run the application locally:

### Frontend
```bash
cd seatsteal
npm install
npm run dev
```
The frontend will run on `http://localhost:5173`

### Backend
```bash
cd webapp
source venv/bin/activate  # Activate virtual environment
pip install -r requirements.txt  # If not already installed
uvicorn app:app --reload --port 5000
```
The backend will run on `http://localhost:5000`

### Environment Variables
Make sure you have a `.env` file in the project root with all required variables (see Prerequisites section).

## Prerequisites

1. Install Vercel CLI:
   ```bash
   npm install -g vercel
   ```

2. Login to Vercel:
   ```bash
   vercel login
   ```

3. Ensure you have:
   - Supabase PostgreSQL database configured
   - AWS SES credentials for email notifications
   - Stripe API keys (if using payments)

## Deployment Steps

### 1. Deploy Frontend

Navigate to the frontend directory and deploy:

```bash
cd seatsteal
vercel --prod
```

**Environment Variables to Set in Vercel Dashboard:**

Go to your project settings > Environment Variables and add:

- `VITE_SUPABASE_URL` - Your Supabase project URL
- `VITE_SUPABASE_ANON_KEY` - Your Supabase anonymous key
- `VITE_API_BASE_URL` - Your backend API URL (set after backend deployment)

**Configuration Files:**
- `vercel.json` - Vite build configuration with SPA routing

### 2. Deploy Backend

Before deploying, you need to handle the requirements file:

**Option A: Temporarily rename requirements file**
```bash
cd ../webapp
mv requirements.txt requirements-dev.txt
mv requirements-vercel.txt requirements.txt
vercel --prod
# After deployment, restore files:
mv requirements.txt requirements-vercel.txt
mv requirements-dev.txt requirements.txt
```

**Option B: Copy optimized requirements**
```bash
cd ../webapp
cp requirements-vercel.txt requirements.txt
vercel --prod
```

**Environment Variables to Set in Vercel Dashboard:**

Go to your project settings > Environment Variables and add:

**Database:**
- `DATABASE_URL` - PostgreSQL database URL from Supabase

**Supabase:**
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_ANON_KEY` - Your Supabase anonymous key
- `SUPABASE_SERVICE_ROLE_KEY` - Your Supabase service role key

**AWS SES (Email):**
- `AWS_REGION` - AWS region (e.g., `us-east-1`)
- `AWS_ACCESS_KEY_ID` - AWS access key ID
- `AWS_SECRET_ACCESS_KEY` - AWS secret access key
- `AWS_SES_FROM_EMAIL` - Email address for notifications

**Application:**
- `PYTHON_ENV` - Set to `production` (already configured in vercel.json)
- `API_BASE_URL` - Your backend API URL (same as deployment URL)
- `FRONTEND_URL` - Your frontend URL (from step 1)

**Redis (if needed for future features):**
- `REDIS_URL` - Redis connection URL (optional for API-only deployment)

**Stripe (Payments):**
- `STRIPE_SECRET_KEY` - Stripe secret API key
- `STRIPE_WEBHOOK_SECRET` - Stripe webhook signing secret
- `STRIPE_PLUS_PRICE_ID` - Stripe Plus tier price ID
- `STRIPE_PRO_PRICE_ID` - Stripe Pro tier price ID

**Scraper (not used in Vercel deployment but required by config):**
- `SCRAPER_CONCURRENT_LIMIT` - Set to `5`
- `SCRAPER_RATE_LIMIT` - Set to `100`

**Configuration Files:**
- `vercel.json` - Python serverless configuration
- `api/index.py` - Vercel entry point
- `requirements-vercel.txt` - Optimized dependencies (excludes playwright, celery)

### 3. Update CORS Configuration

After both deployments, update the backend's CORS settings:

1. Note your frontend production URL (e.g., `https://your-app.vercel.app`)
2. Add it to the allowed origins in `webapp/app.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:5173",
        "http://localhost:3000",
        "https://your-frontend.vercel.app",  # Add your production URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

3. Redeploy the backend:
```bash
cd webapp
vercel --prod
```

4. Update the frontend's `VITE_API_BASE_URL` environment variable in Vercel to point to your backend URL
5. Redeploy the frontend to pick up the new API URL

### 4. Verify Deployment

Test your deployments:

**Backend Health Check:**
```bash
curl https://your-backend.vercel.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "seatsteal-api",
  "version": "1.0.0",
  "environment": "production"
}
```

**Frontend:**
Visit your frontend URL and ensure it loads correctly and can communicate with the backend.

## Important Notes

### Backend Serverless Considerations

1. **Database Connections**: The app uses connection pooling with `pool_pre_ping=True`, which should handle serverless cold starts. Each serverless function may create its own connection pool.

2. **Lifespan Events**: The FastAPI lifespan events (startup/shutdown) work differently in serverless. The database connection is tested on each cold start.

3. **Scrapers Not Included**: The Vercel deployment uses `requirements-vercel.txt` which excludes:
   - `playwright` (large browser automation library)
   - `celery` and `redis` (background task processing)
   - `beautifulsoup4`, `requests`, `lxml` (scraping libraries)
   - Dev dependencies (`pytest`, `black`, `flake8`, `mypy`)

   These should be deployed separately to AWS EC2 for cron jobs.

4. **Stateless Functions**: Each request may hit a different serverless function instance. Ensure any shared state is stored in the database or external cache.

### Database Migrations

Database migrations should be run manually or via a separate CI/CD pipeline:

```bash
cd webapp
source venv/bin/activate
alembic upgrade head
```

Do not rely on the Vercel deployment to run migrations automatically.

### Monitoring

- Check Vercel deployment logs for any startup errors
- Monitor database connection pool usage
- Set up Vercel's monitoring and alerting for production

## Alternative Deployment Commands

### Deploy to Preview Environment
```bash
# Frontend
cd seatsteal
vercel

# Backend
cd ../webapp
vercel
```

### Deploy with Custom Project Name
```bash
vercel --prod --name my-custom-name
```

### Link to Existing Vercel Project
```bash
vercel link
vercel --prod
```

## Troubleshooting

### Import Errors in Backend
If you see import errors related to `webapp.app`, ensure the package structure is correct:
- `webapp/__init__.py` exists
- `webapp/api/__init__.py` exists
- `webapp/api/index.py` correctly imports from `..app`

### Database Connection Errors
- Verify `DATABASE_URL` is set correctly in Vercel environment variables
- Ensure your Supabase database allows connections from Vercel's IP ranges
- Check that connection pooling settings are appropriate for serverless

### CORS Errors
- Verify frontend URL is added to backend's allowed origins
- Ensure both `FRONTEND_URL` environment variable and hardcoded URLs in `app.py` include your production URL
- Check that credentials are enabled in CORS settings

### Build Failures
- Check Vercel build logs for specific errors
- Ensure all required environment variables are set
- Verify `requirements-vercel.txt` includes all necessary dependencies

## Next Steps

1. Set up custom domains in Vercel
2. Configure Stripe webhooks to point to your backend URL
3. Set up AWS EC2 instance for scrapers and notification crons
4. Configure monitoring and error tracking (e.g., Sentry)
5. Set up CI/CD pipeline for automated deployments
