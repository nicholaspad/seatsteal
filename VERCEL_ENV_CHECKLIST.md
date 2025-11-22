# Vercel Environment Variables Checklist

This checklist ensures all required environment variables are set in your Vercel deployments.

## Backend (seatsteal-backend.vercel.app)

Go to: Vercel Dashboard → seatsteal-backend → Settings → Environment Variables

### Required Variables

- [ ] **DATABASE_URL** - PostgreSQL connection string from Supabase
  - Format: `postgresql://postgres.[project-ref]:[password]@aws-0-us-west-1.pooler.supabase.com:6543/postgres`

- [ ] **VITE_SUPABASE_URL** - Supabase project URL
  - Format: `https://[project-ref].supabase.co`

- [ ] **VITE_SUPABASE_ANON_KEY** - Supabase anonymous/public key
  - Long JWT string starting with `eyJhbGci...`

- [ ] **SUPABASE_SERVICE_ROLE_KEY** - Supabase service role key (admin)
  - Long JWT string starting with `eyJhbGci...`

- [ ] **AWS_REGION** - AWS region for SES
  - Example: `us-east-1`

- [ ] **AWS_ACCESS_KEY_ID** - AWS access key
  - Format: `AKIA...`

- [ ] **AWS_SECRET_ACCESS_KEY** - AWS secret key
  - Long alphanumeric string

- [ ] **AWS_SES_FROM_EMAIL** - Email address for notifications
  - Example: `notifications@seatsteal.app`

- [ ] **FRONTEND_URL** - Your frontend domain
  - **Set to**: `https://www.seatsteal.app` (with www - your primary domain)
  - Used for Stripe success/cancel redirects

- [ ] **STRIPE_SECRET_KEY** - Stripe API secret key
  - Test: `sk_test_...`
  - Live: `sk_live_...`

- [ ] **STRIPE_WEBHOOK_SECRET** - Stripe webhook signing secret
  - Format: `whsec_...`

- [ ] **STRIPE_PLUS_PRICE_ID** - Stripe price ID for Plus tier
  - Format: `price_1...`

- [ ] **STRIPE_PRO_PRICE_ID** - Stripe price ID for Pro tier
  - Format: `price_1...`

### Optional Variables (have defaults)

- [ ] **PYTHON_ENV** - Should be `production` (auto-set by vercel.json)
- [ ] **VITE_API_BASE_URL** - Backend URL (usually same as deployment URL)
- [ ] **SCRAPER_CONCURRENT_LIMIT** - Default: `5`
- [ ] **SCRAPER_RATE_LIMIT** - Default: `100`

## Frontend (www.seatsteal.app)

Go to: Vercel Dashboard → seatsteal → Settings → Environment Variables

### Required Variables

- [ ] **VITE_SUPABASE_URL** - Supabase project URL
  - Format: `https://[project-ref].supabase.co`

- [ ] **VITE_SUPABASE_ANON_KEY** - Supabase anonymous/public key
  - Long JWT string starting with `eyJhbGci...`

- [ ] **VITE_API_BASE_URL** - Backend API URL
  - **Set to**: `https://seatsteal-backend.vercel.app`

## Verification Steps

### Backend Health Check
```bash
curl https://seatsteal-backend.vercel.app/health
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

### Check Stripe Configuration
After deployment, check the logs for:
```
INFO:utils.stripe_utils:Stripe initialized with key starting with: sk_test_51Rl...
```

If you see warnings about missing Stripe keys, those variables weren't loaded correctly.

### Test CORS
Open browser DevTools on `https://www.seatsteal.app`:
1. Try to subscribe to a course
2. Check Network tab for the API request
3. Response headers should include: `Access-Control-Allow-Origin: https://www.seatsteal.app`

### Test Stripe Checkout
1. Navigate to pricing section
2. Click "Subscribe" button
3. Should redirect to Stripe checkout (not show error)
4. If error occurs, check the error message (now shows specific issue instead of generic "Failed to create checkout session")

## Common Issues

### CORS Error
- **Symptom**: `No 'Access-Control-Allow-Origin' header is present`
- **Fix**: Code now allows both `https://seatsteal.app` and `https://www.seatsteal.app`
- **Action**: Redeploy backend after updating code

### Stripe Errors
- **Missing API Key**: `Stripe authentication failed. Check STRIPE_SECRET_KEY`
- **Invalid Price ID**: `Invalid Stripe request. This usually means the price ID is invalid`
- **Action**: Verify all 4 Stripe variables are set correctly in Vercel

### Database Connection
- **Symptom**: 500 errors on all API endpoints
- **Check**: Verify `DATABASE_URL` is correct
- **Note**: Supabase pooler URL should use port `6543`

## After Setting Variables

1. Redeploy both frontend and backend for changes to take effect
2. Check deployment logs for any startup errors
3. Run verification steps above
4. Test key user flows (login, subscribe, view courses)
