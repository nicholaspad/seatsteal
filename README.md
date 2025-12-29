# ⚡ SeatSteal

**Never miss an open seat again.**

SeatSteal is a course enrollment notification system that helps college students track and get notified when seats become available in full classes. Monitor courses across multiple universities and receive instant alerts via email or SMS when spots open up.

## Overview

Students often struggle to enroll in popular courses that fill up quickly. SeatSteal continuously monitors course enrollment data and sends real-time notifications when seats become available, giving users a competitive edge in securing their desired classes.

### Key Features

- **Real-time monitoring** - Automated scrapers check enrollment status every 5 minutes
- **Multi-channel notifications** - Email and SMS alerts when seats open
- **Tiered notification speed** - Pro users get notified first (1 min), Plus users next (5 min), Free users last (30 min)
- **Multi-university support** - Princeton, Brown, Northeastern, USC, Cornell, Boston University
- **Subscription management** - Track multiple courses from a single dashboard
- **Referral program** - Earn rewards by inviting friends

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USERS                                          │
│                      (Web Browser / Mobile)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Vercel)                                   │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  React 19 + TypeScript + Ionic + Tailwind CSS + Radix UI             │  │
│  │  • Landing page with pricing                                          │  │
│  │  • Course search & subscription management                            │  │
│  │  • User dashboard & settings                                          │  │
│  │  • Admin panel (users, scrapers, notifications)                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
┌───────────────────────────────────┐   ┌─────────────────────────────────────┐
│      BACKEND API (Vercel)         │   │     TERMINAL SERVER (Render)        │
│  ┌─────────────────────────────┐  │   │  ┌─────────────────────────────────┐│
│  │  FastAPI + SQLAlchemy       │  │   │  │  WebSocket-based CLI            ││
│  │  • REST API endpoints       │  │   │  │  • Remote server management     ││
│  │  • Authentication           │  │   │  │  • Admin operations             ││
│  │  • Stripe webhooks          │  │   │  └─────────────────────────────────┘│
│  │  • Rate limiting            │  │   └─────────────────────────────────────┘
│  └─────────────────────────────┘  │
└───────────────────────────────────┘
                    │
    ┌───────────────┼───────────────┬───────────────────────┐
    ▼               ▼               ▼                       ▼
┌─────────┐  ┌────────────┐  ┌────────────┐         ┌─────────────┐
│PostgreSQL│  │  Supabase  │  │   Stripe   │         │   Redis     │
│ Database │  │   Auth     │  │  Payments  │         │   Cache     │
│          │  │            │  │            │         │  (optional) │
│ • Users  │  │ • JWT      │  │ • Billing  │         │             │
│ • Courses│  │ • Magic    │  │ • Plans    │         │ • Sessions  │
│ • Classes│  │   Links    │  │ • Webhooks │         │ • Profiles  │
│ • Subs   │  │ • OAuth    │  │            │         │             │
└─────────┘  └────────────┘  └────────────┘         └─────────────┘
      ▲
      │
      │ Writes enrollment data
      │
┌─────┴───────────────────────────────────────────────────────────────────────┐
│                        BACKGROUND JOBS                                       │
│  ┌─────────────────────────────────┐  ┌─────────────────────────────────┐   │
│  │         SCRAPER                 │  │      NOTIFICATION SERVICE       │   │
│  │  (Runs every 5 minutes)         │  │  (Runs every 1 minute)          │   │
│  │                                 │  │                                 │   │
│  │  • Fetches enrollment data      │  │  • Checks for status changes    │   │
│  │  • College-specific parsers     │  │  • Tier-based delivery timing   │   │
│  │  • Rate-limited requests        │  │  • Routes to Email/SMS          │   │
│  │  • Database locking             │  │  • Logs all notifications       │   │
│  └─────────────────────────────────┘  └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                                │
                        ┌───────────────────────┴───────────────────────┐
                        ▼                                               ▼
              ┌─────────────────────┐                         ┌─────────────────┐
              │      AWS SES        │                         │     Twilio      │
              │   (Email Service)   │                         │  (SMS Service)  │
              │                     │                         │                 │
              │  • Transactional    │                         │  • SMS alerts   │
              │    emails           │                         │  • Rate limited │
              │  • HTML templates   │                         │                 │
              └─────────────────────┘                         └─────────────────┘
                        │                                               │
                        └───────────────────────┬───────────────────────┘
                                                ▼
                                    ┌───────────────────────┐
                                    │        USERS          │
                                    │  (Email/SMS Inbox)    │
                                    └───────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL DATA SOURCES                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  University Registration Systems (scraped)                              ││
│  │  • Princeton • Brown • Northeastern • USC • Cornell • Boston University ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Third-Party Dependencies

### Infrastructure & Hosting

| Service | Purpose |
|---------|---------|
| **Vercel** | Frontend and backend API hosting (serverless) |
| **Render** | WebSocket terminal server hosting |
| **Supabase** | PostgreSQL database hosting |

### Authentication & Security

| Service | Purpose |
|---------|---------|
| **Supabase Auth** | User authentication (magic links, JWT tokens, OAuth) |

### Payments

| Service | Purpose |
|---------|---------|
| **Stripe** | Subscription billing, payment processing, webhooks |

### Notifications

| Service | Purpose |
|---------|---------|
| **AWS SES** | Transactional email delivery |
| **Twilio** | SMS notifications |

### Database & Caching

| Service | Purpose |
|---------|---------|
| **PostgreSQL** | Primary relational database (via Supabase) |
| **Redis** | Session and profile caching (optional) |

### Frontend Stack

| Technology | Purpose |
|------------|---------|
| **React 19** | UI framework |
| **TypeScript** | Type safety |
| **Ionic** | Mobile-first UI components |
| **Tailwind CSS** | Styling |
| **Radix UI** | Accessible UI primitives |
| **Vite** | Build tooling |

### Backend Stack

| Technology | Purpose |
|------------|---------|
| **FastAPI** | Python web framework |
| **SQLAlchemy** | ORM and database toolkit |
| **Alembic** | Database migrations |
| **Pydantic** | Data validation |
| **BeautifulSoup4** | HTML parsing for scrapers |

---

## Project Structure

```
seatsteal/
├── seatsteal/              # Frontend (React + Ionic)
│   ├── src/
│   │   ├── pages/          # Page components
│   │   ├── components/     # Reusable UI components
│   │   ├── lib/            # Utilities and API client
│   │   └── hooks/          # Custom React hooks
│   └── public/             # Static assets
│
├── webapp/                 # Backend (FastAPI)
│   ├── api/
│   │   ├── routes/         # API endpoints
│   │   └── middleware/     # Auth, rate limiting
│   ├── models/             # SQLAlchemy models
│   ├── scraper/            # Course data scrapers
│   │   └── scrapers/       # College-specific implementations
│   ├── notifications/      # Email/SMS notification service
│   ├── db/                 # Database connection
│   ├── alembic/            # Database migrations
│   └── tests/              # Backend tests
│
└── README.md
```

---

## License

Proprietary - All rights reserved.
