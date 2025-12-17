# SeatSteal Terminal Server

A dedicated WebSocket server for the admin terminal feature. This is required because Vercel's serverless functions don't support WebSocket connections.

## Architecture

```
┌─────────────────┐     WebSocket      ┌──────────────────┐
│  Frontend       │ ←────────────────→ │  Terminal Server │
│  (Vercel)       │                    │  (Render)        │
└─────────────────┘                    └──────────────────┘
         │                                      │
         │ Auth (Supabase)                     │ Verify Token
         ↓                                      ↓
┌─────────────────┐                    ┌──────────────────┐
│  Supabase       │                    │  PostgreSQL DB   │
└─────────────────┘                    └──────────────────┘
```

## Deployment to Render

### Option A: Deploy via Render Dashboard (Recommended)

1. **Create a Render account** at https://render.com if you don't have one.

2. **Create a new Web Service:**
   - Go to your Render Dashboard
   - Click **"New +"** → **"Web Service"**
   - Connect your GitHub repository (or use "Deploy from a public Git repository")
   - Set the **Root Directory** to `terminal-server`

3. **Configure the service:**
   | Setting | Value |
   |---------|-------|
   | Name | `seatsteal-terminal` |
   | Region | Oregon (US West) or closest to your users |
   | Branch | `main` (or your production branch) |
   | Runtime | Docker |
   | Instance Type | Starter ($7/month) or Free (limited) |

4. **Set Environment Variables:**
   In the Render dashboard, add these environment variables:

   | Variable | Description | Example |
   |----------|-------------|---------|
   | `SUPABASE_URL` | Your Supabase project URL | `https://abc123.supabase.co` |
   | `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key (from Supabase dashboard → Settings → API) | `eyJhbGci...` |
   | `DATABASE_URL` | PostgreSQL connection string (from Supabase dashboard → Settings → Database → Connection string → URI) | `postgresql://postgres:...@db.abc123.supabase.co:5432/postgres` |
   | `ALLOWED_ORIGINS` | Comma-separated list of allowed frontend URLs | `https://seatsteal.vercel.app,https://yourdomain.com` |

5. **Deploy:**
   - Click **"Create Web Service"**
   - Wait for the build and deployment to complete
   - Note the service URL (e.g., `https://seatsteal-terminal.onrender.com`)

### Option B: Deploy via render.yaml (Blueprint)

1. Push the `terminal-server` directory to your repository.

2. In Render dashboard, click **"New +"** → **"Blueprint"**

3. Connect your repository and Render will detect the `render.yaml` file.

4. Set the environment variables when prompted.

## Configure Frontend

After deploying the terminal server, update your frontend environment:

### Vercel Dashboard

1. Go to your Vercel project settings
2. Navigate to **Settings** → **Environment Variables**
3. Add:
   ```
   VITE_TERMINAL_SERVER_URL = https://seatsteal-terminal.onrender.com
   ```
4. Redeploy your frontend for the changes to take effect

### Local Development

Add to your `seatsteal/.env.local`:
```bash
VITE_TERMINAL_SERVER_URL=https://seatsteal-terminal.onrender.com
```

Or omit it to use the local backend (when running `uvicorn` locally).

## Local Development

### Running the Terminal Server Locally

```bash
cd terminal-server

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your credentials

# Run the server
uvicorn app:app --reload --port 10000
```

### Testing WebSocket Connection

You can test the WebSocket connection with a tool like `websocat`:

```bash
# Install websocat (macOS)
brew install websocat

# Test connection (replace TOKEN with a valid admin JWT)
websocat "ws://localhost:10000/api/admin/terminal?token=YOUR_JWT_TOKEN"
```

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Service role key for admin operations |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `ALLOWED_ORIGINS` | No | CORS allowed origins (default: `*`) |

## Security Notes

- The terminal server verifies admin tokens against Supabase and the database
- Only users with `role = 'admin'` in the `profiles` table can access the terminal
- CORS is configured to only accept requests from allowed origins
- WebSocket connections are authenticated via JWT tokens

## Troubleshooting

### "Unauthorized" Error
- Verify the user has `role = 'admin'` in the database
- Check that `SUPABASE_SERVICE_ROLE_KEY` is correct
- Ensure the JWT token is valid and not expired

### WebSocket Connection Failed
- Check that `VITE_TERMINAL_SERVER_URL` is set correctly in the frontend
- Verify the terminal server is running and accessible
- Check CORS settings if connecting from a different domain

### Health Check Failing on Render
- The `/health` endpoint should return `{"status": "healthy"}`
- Check Render logs for startup errors
- Verify all environment variables are set

## Cost

- **Render Starter**: ~$7/month (recommended for always-on)
- **Render Free**: Limited to 750 hours/month, spins down after inactivity (15-30s cold start)
