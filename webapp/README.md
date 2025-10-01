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

### Scraper Workers

**Terminal 1 - Scraper Worker:**
```bash
celery -A scraper.daemon.tasks worker --loglevel=info --pool=solo
```

**Terminal 2 - Scraper Beat (Scheduler):**
```bash
celery -A scraper.daemon.scheduler beat --loglevel=info
```

### Notification Workers

**Terminal 3 - Notification Worker:**
```bash
celery -A notifications.daemon.tasks worker --loglevel=info --pool=solo
```

**Terminal 4 - Notification Beat (Scheduler):**
```bash
celery -A notifications.daemon.scheduler beat --loglevel=info
```

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
│   ├── daemon/           # Celery tasks
│   └── utils/            # Utilities
├── notifications/        # Notification system
│   ├── templates/        # Email templates
│   └── daemon/           # Celery tasks
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

## Celery Task Management

```bash
# Trigger manual scrape
celery -A scraper.daemon.tasks call scraper.scrape_college --args='["princeton", "CS"]'

# Trigger notification check
celery -A notifications.daemon.tasks call notifications.check_and_send

# Monitor tasks
celery -A scraper.daemon.tasks inspect active
celery -A scraper.daemon.tasks inspect scheduled
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

- Redis must be running for Celery tasks to work
- AWS SES credentials required for email notifications
- Database migrations are in `alembic/versions/`
- All scrapers implement the `BaseScraper` interface
