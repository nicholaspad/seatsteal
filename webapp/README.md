# SeatSteal Backend (Python)

FastAPI-based backend for the SeatSteal course enrollment notification system.

## Setup

### 1. Install Dependencies

```bash
cd webapp
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

The backend reads from the shared `.env` file at the project root (`/Users/nicholaspad/Sandbox/seatsteal/.env`).

### 3. Initialize Database

```bash
# Run migrations
alembic upgrade head

# Add colleges (example)
python scripts/add_college.py --name "Princeton University" --short-name "princeton" --domain "princeton.edu"
```

## Running the Services

### Main API Server

```bash
uvicorn app:app --reload --port 5000
```

The API will be available at `http://localhost:5000`
- API docs: `http://localhost:5000/docs`
- Health check: `http://localhost:5000/health`

### Scraper Worker

**Terminal 2 - Scraper Script:**
```bash
# Make sure you're in the webapp directory
cd webapp

# Run once for a specific college
python scraper/run_scraper.py run --college princeton

# Run for all active colleges
python scraper/run_scraper.py run-all

# Run in loop mode (scrapes every 10 minutes)
python scraper/run_scraper.py --loop

# Run with options
python scraper/run_scraper.py run --college brown --subject CS --limit 50

# View scraper status
python scraper/run_scraper.py status

# With debug logging
python scraper/run_scraper.py run-all --debug
```

The scraper system:
- Uses database-based locking to prevent concurrent scrapes
- Includes retry logic with exponential backoff (3 attempts)
- Logs all runs to `scraper_logs` table
- No Redis dependency (unlike old Celery version)

### Notification Worker

**Terminal 3 - Notification Script:**
```bash
# Make sure you're in the webapp directory
cd webapp

# Run once
python notifications/send_notifs.py

# Run in loop mode (checks every minute)
python notifications/send_notifs.py --loop

# Dry run (no database changes)
python notifications/send_notifs.py --dry-run

# With debug logging
python notifications/send_notifs.py --loop --debug
```

The notification system runs every minute and sends notifications based on user tier:
- **Pro users**: Every minute
- **Plus users**: Every 5 minutes
- **Free users**: Every 30 minutes

## Management Scripts

### Add a College

```bash
python scripts/add_college.py --name "Brown University" --short-name "brown" --domain "brown.edu"

# List all colleges
python scripts/add_college.py --list
```

### Clear College Data

```bash
# Clear all course data for a college (with confirmation)
python scripts/clear_college.py --college princeton --confirm

# Keep subscriptions (deactivate instead of delete)
python scripts/clear_college.py --college princeton --keep-subscriptions --confirm
```

### Migrate Data from Old Database

```bash
# Dry run (no changes)
python scripts/migrate_data.py --old-db "postgresql://..." --dry-run

# Execute migration
python scripts/migrate_data.py --old-db "postgresql://..." --confirm
```

## API Endpoints

### Colleges
- `GET /api/colleges` - List all colleges
- `GET /api/colleges/{id}` - Get college details

### Courses
- `GET /api/courses?college_id={id}` - List courses for a college
- `GET /api/courses/{id}` - Get course details

### Classes
- `GET /api/classes?course_id={id}` - List classes for a course
- `GET /api/classes/{id}` - Get class details

### Subscriptions (Authenticated)
- `GET /api/subscriptions` - Get user's subscriptions
- `POST /api/subscriptions` - Create subscription
- `DELETE /api/subscriptions/{id}` - Delete subscription

### Auth
- `POST /api/auth/magic-link` - Request magic link
- `POST /api/auth/verify` - Verify magic link

## Architecture

```
webapp/
├── api/                    # API routes and middleware
│   ├── routes/            # Endpoint handlers
│   └── middleware/        # Auth, rate limiting
├── models/                # SQLAlchemy database models
├── schemas/               # Pydantic validation schemas
├── scraper/              # Course scraping system
│   ├── scrapers/         # College-specific scrapers
│   ├── services/         # Scraper logic
│   ├── run_scraper.py   # Scraper CLI script
│   ├── scraper_job.py   # Job orchestration
│   ├── scraper_lock.py  # Database-based locking
│   └── utils/            # Utilities
├── notifications/        # Notification system
│   ├── templates/        # Email templates
│   ├── send_notifs.py   # Notification job script
│   ├── constants.py     # Tier cadence configuration
│   └── email_service.py # Email sending service
├── db/                   # Database connection
├── scripts/              # Management scripts
└── alembic/             # Database migrations
```

## Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

## Task Management

### Scraper (Python Script)

```bash
# Run scraper for a specific college
python scraper/run_scraper.py run --college princeton

# Run scraper for all colleges
python scraper/run_scraper.py run-all

# View scraper status
python scraper/run_scraper.py status
```

### Notifications (Python Script)

```bash
# Run notification check once
python notifications/send_notifs.py

# Dry run (no changes)
python notifications/send_notifs.py --dry-run
```

## Development

### Code Formatting
```bash
black .
```

### Running Tests
```bash
pytest
```

## Implemented Scrapers

- ✅ Princeton University
- ✅ Brown University
- ✅ Boston University (BU)
- ✅ Cornell University
- ✅ Northeastern University (NEU)
- ✅ University of Southern California (USC)

## Notes

- **No Redis/Celery required** - Both scraper and notifications use simple Python scripts
- AWS SES credentials required for email notifications
- Scraper uses database-based locking to prevent concurrent runs
- Notification system uses tier-based cadence (pro=1min, plus=5min, free=30min)
- Database migrations are in `alembic/versions/`
- All scrapers implement the `BaseScraper` interface
