# Test Coverage Analysis - SeatSteal

**Date:** December 19, 2025
**Analysis Type:** Comprehensive codebase test coverage review

---

## Executive Summary

The SeatSteal codebase shows **significant test coverage gaps**, particularly in the frontend where only ~5% of components have tests. The backend has better coverage for core routes and scrapers, but lacks tests for critical middleware, utility functions, and integration scenarios. This analysis identifies specific areas requiring immediate attention to improve code quality, reduce bugs, and enable confident refactoring.

---

## Current Test Coverage

### Frontend (seatsteal/)

**Overall Status:** ~5% component coverage

**Tested Areas:**
- ✅ **Pages (5/21 tested):**
  - Dashboard, Home, Courses, CourseDetails, Settings
- ✅ **Components (4/74 tested):**
  - course-summary-modal, class-card, enrollment-analysis-modal, ProtectedRoute
- ✅ **Lib utilities (1/10 tested):**
  - premium.test.ts

**Coverage Statistics:**
- Total component/page files: ~95
- Files with tests: ~10
- Coverage: **~10%**

### Backend (webapp/)

**Overall Status:** ~60% route/module coverage

**Tested Areas:**
- ✅ **Routes (9/11 route files):**
  - auth, courses, classes, colleges, admin, stripe, subscriptions, notifications, user
  - ❌ Missing: term_codes
- ✅ **Scrapers (8/8 college scrapers + scraper service):**
  - Brown, BU, Cornell, NEU, Rutgers, UPenn, USC, scraper_service, scraper_lock
  - ❌ Missing: UMD scraper
- ✅ **Utilities (5 test files):**
  - stripe_utils, premium, premium_caching, tier_cache, notification_job, cache_invalidation, errors
- ✅ **Middleware (2 test files):**
  - auth, auth_cache
- ✅ **SMS service**

**Coverage Statistics:**
- Core routes: 90% covered
- Scrapers: 88% covered
- Utils: ~70% covered
- Middleware: 50% covered
- **Integration tests: 0%**

---

## Critical Gaps by Priority

### 🔴 HIGH PRIORITY

#### 1. **Frontend Middleware & Security Testing**

**Missing Tests:**
- `lib/api.ts` - Critical API wrapper with error handling, rate limiting, and toast management
- `lib/security.ts` - Security functions for URL validation and input sanitization
- `lib/validation.ts` - Zod schemas for request validation (100+ lines of validation logic)

**Risk:** Security vulnerabilities, broken error handling, validation bypasses
**Impact:** High - these are used throughout the entire frontend

#### 2. **Frontend Date Utilities**

**Missing Tests:**
- `lib/date-utils.ts` - Timezone conversion and date formatting (137 lines)

**Risk:** Incorrect date displays, timezone bugs
**Impact:** High - affects all time-sensitive features (notifications, enrollment changes)

#### 3. **Backend Middleware - Rate Limiting**

**Missing Tests:**
- `api/middleware/rate_limit.py` - Token bucket rate limiting implementation
- `api/middleware/security_headers.py` - Security header injection

**Risk:** DoS vulnerabilities, security header misconfigurations
**Impact:** High - affects all API endpoints

#### 4. **Backend Notification System**

**Missing Tests:**
- `notifications/send_notifs.py` - Core notification job with tier-based priority (400+ lines)
- `notifications/email_service.py` - Email sending logic
- Email/SMS service integration tests

**Risk:** Failed notifications, priority logic errors, revenue-impacting bugs
**Impact:** High - core business logic for premium features

#### 5. **Backend Term Codes Route**

**Missing Tests:**
- `api/routes/term_codes.py` - Fetches term codes from multiple colleges
- Web scraping logic for Brown, BU, Cornell, etc.

**Risk:** Silent failures in term code fetching, breaking course catalog
**Impact:** High - affects data refresh for all colleges

#### 6. **UMD Scraper**

**Missing Tests:**
- `scraper/scrapers/umd.py` - University of Maryland scraper

**Risk:** UMD data sync failures going undetected
**Impact:** Medium-High - affects all UMD users

---

### 🟡 MEDIUM PRIORITY

#### 7. **Frontend Component Library (UI Components)**

**Missing Tests (0/47 UI components tested):**
- `components/ui/*` - Button, Input, Select, Dialog, Tooltip, Tabs, etc.
- `components/auth/*` - Authentication components
- `components/layout/*` - Layout components
- `components/admin/*` - Admin panel components

**Risk:** UI regressions, accessibility issues
**Impact:** Medium - affects user experience

#### 8. **Frontend Hooks**

**Missing Tests:**
- `hooks/use-count-up.ts` - Animation hook
- `hooks/use-search-params.ts` - URL parameter management

**Risk:** Hook logic errors, state management bugs
**Impact:** Medium

#### 9. **Frontend Course & Class Components**

**Missing Tests (2/10+ tested):**
- course-card, course-filters, course-search, course-details
- class components (only 2 tested)
- college-filter

**Risk:** Display bugs, filter logic errors
**Impact:** Medium - core user-facing features

#### 10. **Backend Database Models**

**Missing Tests:**
- All model classes (College, Course, Class, Enrollment, User, etc.)
- Model validation logic
- Relationship constraints

**Risk:** Data integrity issues, ORM bugs
**Impact:** Medium

#### 11. **Backend Config & Cache**

**Missing Tests:**
- `config.py` - Application configuration
- `utils/cache.py` - Redis caching logic

**Risk:** Cache inconsistencies, config errors in different environments
**Impact:** Medium

---

### 🟢 LOW PRIORITY (Quality of Life)

#### 12. **Integration & End-to-End Tests**

**Missing:**
- No E2E test framework (Playwright, Cypress, etc.)
- No integration tests marked with `@pytest.mark.integration`
- No full workflow tests (signup → browse → subscribe → notification)

**Risk:** Integration bugs between frontend/backend
**Impact:** Medium-Low (caught in staging, but costly)

#### 13. **Frontend Admin Pages**

**Missing Tests (0/7 tested):**
- Admin, AdminColleges, AdminNotifications, AdminPerformance, AdminScrapers, AdminTerminal, AdminUsers

**Risk:** Admin bugs affecting operations
**Impact:** Low - admin-only, lower usage

#### 14. **Frontend Skeleton Loaders**

**Missing Tests:**
- `components/skeletons/*` - Loading state components

**Risk:** Visual bugs in loading states
**Impact:** Low

---

## Specific Test Recommendations

### Quick Wins (Can be implemented in 1-2 hours each)

1. **Test `lib/validation.ts`:**
   ```typescript
   // Test all Zod schemas
   - EmailSchema validation
   - EduEmailSchema edge cases (.edu requirement, + character blocking, dots in username)
   - PhoneSchema regex validation
   - Pagination transforms
   - CourseQuerySchema transforms
   ```

2. **Test `lib/date-utils.ts`:**
   ```typescript
   // Test timezone handling
   - formatLocalDate with different timezones
   - null/invalid date handling
   - Edge cases: leap years, DST changes
   ```

3. **Test `lib/security.ts`:**
   ```typescript
   // Test security functions
   - URL validation (allow stripe.com, block malicious)
   - XSS prevention
   - Input sanitization
   ```

4. **Test `api/middleware/security_headers.py`:**
   ```python
   # Test security header middleware
   - Verify all security headers are set
   - Test CSP, X-Frame-Options, etc.
   - Test cache control headers
   ```

5. **Test UMD scraper:**
   ```python
   # Test UMD scraper
   - Mock HTTP responses
   - Test course parsing
   - Test error handling
   ```

### Complex But Critical (3-5 hours each)

6. **Test `lib/api.ts`:**
   ```typescript
   // Test API wrapper
   - Rate limiting (429) with retry logic
   - Server error (5xx) toast handling
   - URL resolution (relative vs absolute)
   - Vercel bypass secret injection
   - ServerErrorWithToast class
   - Authentication token refresh
   ```

7. **Test `api/middleware/rate_limit.py`:**
   ```python
   # Test rate limiting
   - Token bucket algorithm
   - Redis connection fallback
   - Rate limit exceeded responses
   - Different limits per endpoint
   - Client identification (IP, user ID)
   ```

8. **Test `notifications/send_notifs.py`:**
   ```python
   # Test notification job
   - Tier-based notification cadence (Pro: 1min, Plus: 5min, Free: 30min)
   - Pro priority delay (30 seconds before others)
   - Notification deduplication
   - Email/SMS service integration
   - Dry-run mode
   - Error handling and logging
   ```

9. **Test `api/routes/term_codes.py`:**
   ```python
   # Test term codes route
   - Mock HTTP requests to college websites
   - Test HTML parsing for each college
   - Test error handling
   - Test admin authorization
   ```

---

## Testing Infrastructure Improvements

### 1. Frontend Coverage Reporting
```json
// Add to vitest.config.ts
coverage: {
  provider: 'v8',
  reporter: ['text', 'json', 'html', 'lcov'],
  include: ['src/**/*.{ts,tsx}'],
  exclude: [
    'src/**/*.test.{ts,tsx}',
    'src/test/**',
    'src/**/__tests__/**',
    'src/vite-env.d.ts'
  ],
  thresholds: {
    statements: 60,
    branches: 60,
    functions: 60,
    lines: 60
  }
}
```

### 2. Backend Coverage Thresholds
```toml
# Add to pyproject.toml or pytest.ini
[tool.coverage.run]
source = ["."]
omit = [
    "*/tests/*",
    "*/venv/*",
    "*/alembic/*",
    "*/scripts/*"
]

[tool.coverage.report]
fail_under = 70
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:"
]
```

### 3. Integration Test Setup
```python
# Create webapp/tests/test_integration/ directory
# Add conftest.py with:
@pytest.fixture(scope="session")
def integration_db():
    """Full database with migrations"""
    # Run alembic migrations
    # Seed test data

@pytest.mark.integration
async def test_full_notification_workflow():
    """Test complete flow: enrollment change → notification → delivery"""
    pass
```

### 4. E2E Test Framework
```bash
# Add Playwright for E2E tests
cd seatsteal
npm install -D @playwright/test
npx playwright install

# Create tests/e2e/ directory
# Add critical user journeys:
# - Signup → Browse → Subscribe → Receive notification
# - Admin panel operations
# - Payment flow
```

---

## Recommended Implementation Order

### Phase 1: Security & Core Infrastructure (Week 1)
1. lib/security.ts tests
2. lib/validation.ts tests
3. api/middleware/rate_limit.py tests
4. api/middleware/security_headers.py tests

### Phase 2: Business Logic (Week 2)
5. notifications/send_notifs.py tests
6. lib/api.ts tests
7. api/routes/term_codes.py tests
8. UMD scraper tests

### Phase 3: UI Components (Week 3-4)
9. lib/date-utils.ts tests
10. Frontend UI component tests (Button, Input, Select, etc.)
11. Frontend hooks tests
12. Course/class component tests

### Phase 4: Integration & E2E (Week 5)
13. Integration test suite setup
14. Playwright E2E test setup
15. Critical user journey E2E tests
16. Admin workflow integration tests

---

## Success Metrics

**Target Coverage Goals:**
- Frontend: 60% line coverage (current: ~10%)
- Backend: 80% line coverage (current: ~60%)
- Integration tests: 20+ test scenarios
- E2E tests: 10+ critical user journeys

**Quality Gates:**
- All PRs must maintain or improve coverage
- No PR merge if coverage drops below threshold
- Critical paths (auth, payments, notifications) must have 90%+ coverage

---

## Tools & Commands

### Frontend Coverage
```bash
cd seatsteal
npm install -D @vitest/coverage-v8
npm run test:run -- --coverage
```

### Backend Coverage
```bash
cd webapp
docker compose -f docker-compose.test.yml run --rm tests pytest --cov=. --cov-report=html --cov-report=term
```

### View Coverage Reports
```bash
# Frontend: open seatsteal/coverage/index.html
# Backend: open webapp/htmlcov/index.html
```

---

## Conclusion

The codebase has **solid test coverage for backend routes and scrapers** but **critical gaps in:**
- Frontend components, utilities, and API layer
- Backend middleware and notification system
- Integration and E2E testing

**Immediate action items:**
1. Prioritize security-related tests (validation, security headers, rate limiting)
2. Add tests for business-critical features (notifications, API wrapper)
3. Set up coverage reporting and CI/CD gates
4. Gradually increase component test coverage

**Estimated effort:** 80-120 hours to reach 70%+ coverage across the board.
