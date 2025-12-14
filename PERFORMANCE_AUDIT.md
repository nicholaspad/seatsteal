# SeatSteal Performance Audit Report

**Date**: December 14, 2025
**Auditor**: Claude
**Stack**: Vercel (Frontend/Backend), Supabase (PostgreSQL), AWS (SES/Lambda), Twilio (SMS), Redis (Cache)

---

## Executive Summary

SeatSteal has a solid foundation for scalability with several optimizations already in place. This audit identifies what's working well and areas that need attention before significant scale.

**Overall Assessment**: **Ready for moderate scale (10K-50K users)** with some improvements needed for high scale (100K+ users).

---

## 1. Database Performance

### 1.1 Indexes - GOOD

The database schema has comprehensive indexing already in place:

**Courses Table**:
- `courses_college_course_code_idx` (UNIQUE) - Composite for upserts
- `courses_college_active_idx` - For filtered queries
- `courses_college_active_updated_idx` - For time-based queries
- `courses_course_code_trgm_idx` (GIN) - Fuzzy search
- `courses_title_trgm_idx` (GIN) - Fuzzy search

**Enrollments Table** (high-volume):
- `enrollments_class_scraped_idx` - Critical for latest enrollment lookups
- `enrollments_class_status_scraped_idx` - For status filtering
- `enrollments_college_scraped_idx` - For college-wide queries

**Subscriptions Table**:
- `subscriptions_class_college_active_idx` - For notification queries
- `subscriptions_user_active_idx` - For user dashboard

**Recommendations**:
- Indexes appear well-designed for current query patterns
- Migration 008 already removed duplicate indexes
- Consider adding a partial index for active-only queries: `CREATE INDEX subscriptions_active_only_idx ON subscriptions (user_id, class_id) WHERE is_active = true`

### 1.2 Query Patterns - GOOD

**Positive Findings**:
1. **Bulk operations** in scraper service use batch upserts with `ON CONFLICT` (100 records per batch)
2. **Window functions** used for latest enrollment queries instead of correlated subqueries
3. **DISTINCT ON** used for efficient latest-record-per-group queries
4. **No N+1 queries** detected - bulk fetching with `IN` clauses throughout

**Code Examples of Good Patterns**:

```python
# courses.py:150-184 - Efficient bulk enrollment fetch
enrollment_ranked = (
    select(...)
    .where(Enrollment.class_id.in_(class_ids))
    .subquery()
)
```

```python
# scraper_service.py:673-680 - Efficient latest enrollment
SELECT DISTINCT ON (class_id) class_id, id, enrollment_status
FROM enrollments
WHERE class_id = ANY(:class_ids)
ORDER BY class_id, scraped_at DESC
```

### 1.3 Enrollment Table Growth - ATTENTION NEEDED

**Current Strategy**: Status-change-only storage (new row only when status changes)
**Estimated Reduction**: ~90% vs storing every scrape

**Potential Issue**: Even with this optimization, enrollments table will grow significantly:
- 8 colleges x 5,000 classes = 40,000 classes
- 48 scrapes/day x 40,000 = 1.9M potential rows/day (mitigated by status-change strategy)
- Realistic: ~50,000-100,000 new rows/day with status changes

**Recommendations**:
1. Add pg_cron job to delete old enrollment data (>30 days already configured in migration 005)
2. Consider table partitioning by `scraped_at` if table exceeds 50M rows
3. Monitor query performance on `enrollments_class_scraped_idx`

---

## 2. Connection Pooling - GOOD

**Configuration** (`db/connection.py`):
```python
pool_size=20,
max_overflow=30,
pool_pre_ping=True,
pool_recycle=3600,
pool_timeout=30,
```

**Supabase Note**: Supabase uses PgBouncer in transaction mode by default. The current config is compatible.

**Recommendations**:
- Current pool size (20 + 30 overflow = 50 max) is appropriate for Vercel serverless
- For high scale, consider Supabase's dedicated pooler connection limits

---

## 3. Caching Strategy - GOOD with IMPROVEMENTS

### 3.1 Current Implementation

**Redis Caching** (`utils/cache.py`):
- User profile caching (5 min TTL)
- User tier caching (5 min TTL)
- Course listings (15 min TTL for listings, 3 min for search)
- Course details (5 min TTL)
- Class details (5 min TTL)

**Positive**:
- Cache invalidation on subscription changes
- Graceful fallback when Redis unavailable
- MD5-hashed cache keys for consistent length

### 3.2 Recommendations

1. **Add college list caching** - Colleges rarely change but are fetched frequently:
```python
# colleges.py - Consider adding
@cache_response(prefix='colleges', ttl=3600)  # 1 hour
async def get_colleges(...):
```

2. **Consider cache warming** after scraper runs for frequently-accessed courses

3. **Missing cache invalidation** - When scrapers update enrollments, cached course/class data becomes stale. Consider:
   - Invalidating course caches after successful scraper runs
   - Or accepting 5-minute staleness as acceptable

---

## 4. API Performance - GOOD

### 4.1 Response Compression

GZip middleware configured with 1KB minimum threshold - GOOD

### 4.2 Query Optimization

**Positive Patterns**:
- `joinedload` used for eager loading relationships
- Pagination with offset/limit
- Trigram similarity search with configurable threshold

### 4.3 Potential Bottlenecks

1. **`/api/courses/` with search** - Trigram similarity is expensive:
   - GIN indexes help but still requires full scan for similarity scoring
   - Consider: ElasticSearch/Meilisearch for very high search volume

2. **`/api/classes/{id}/enrollment-analysis`** - Complex CTE queries:
   - Currently Pro-only (limited users)
   - Monitor as Pro user base grows

---

## 5. Background Jobs - GOOD

### 5.1 Scraper Architecture

**Positive**:
- Distributed locking prevents concurrent scrapes
- Exponential backoff retry (3 attempts)
- Batch operations (100 records/batch)
- Status-change detection reduces writes by ~90%
- Connection retry logic for transient failures

**Configuration**:
- Lock timeout: 15 minutes
- Statement timeout: 5 minutes
- Keepalive settings for long connections

### 5.2 Notification Job

**Positive**:
- Tier-based notification cadence (Pro: 1min, Plus: 5min, Free: 30min)
- Pro priority (30s head start)
- Bulk subscription deactivation
- Email timeout protection (30s)

**Potential Issue**: Single-threaded notification sending could become bottleneck:
- At 1000 notifications/minute, with 1s per email = ~17 notifications/second max
- Consider: Async batch sending or queue-based approach for >10K active users

---

## 6. Frontend Performance - NEEDS ATTENTION

### 6.1 Bundle Analysis

**Current Issues**:
1. **No lazy loading** - All pages imported eagerly in `main.tsx`
2. **Large dependencies**:
   - `@ionic/react` - Heavy UI framework
   - `recharts` - Chart library loaded for all users (only needed in admin/Pro)
   - `@supabase/supabase-js` - Always loaded

### 6.2 Recommendations

1. **Implement code splitting** with React.lazy:
```tsx
// main.tsx - Use lazy loading for routes
const Admin = lazy(() => import("@/pages/admin/Admin"));
const CourseDetails = lazy(() => import("@/pages/CourseDetails"));
```

2. **Split vendor chunks** in Vite config:
```ts
// vite.config.ts
build: {
  rollupOptions: {
    output: {
      manualChunks: {
        'vendor-ionic': ['@ionic/react', '@ionic/react-router'],
        'vendor-supabase': ['@supabase/supabase-js'],
        'vendor-charts': ['recharts'],
      },
    },
  },
},
```

3. **Defer non-critical scripts**:
   - Move analytics initialization to after first paint
   - Consider dynamic import for `recharts` only when needed

---

## 7. RLS Policy Performance - ALREADY OPTIMIZED

Migration 007 already optimized Supabase RLS policies:
- Wrapped `auth.uid()` and `auth.role()` in `(select ...)` to prevent per-row re-evaluation
- Consolidated multiple permissive policies

---

## 8. Scalability Recommendations Summary

### Immediate (Before 10K users)

| Priority | Item | Effort | Impact |
|----------|------|--------|--------|
| HIGH | Add frontend code splitting | Medium | Faster initial load |
| HIGH | Add partial index for active subscriptions | Low | Faster dashboard queries |
| MEDIUM | Cache college listings | Low | Reduce DB load |

### Medium-term (10K-50K users)

| Priority | Item | Effort | Impact |
|----------|------|--------|--------|
| HIGH | Async notification sending | Medium | Handle notification volume |
| MEDIUM | Consider read replicas | High | Distribute read load |
| MEDIUM | Add query performance monitoring | Medium | Identify bottlenecks |

### Long-term (50K+ users)

| Priority | Item | Effort | Impact |
|----------|------|--------|--------|
| HIGH | Table partitioning for enrollments | High | Query performance |
| HIGH | Dedicated search service | High | Search scalability |
| MEDIUM | Message queue for notifications | High | Reliability at scale |

---

## 9. Monitoring Recommendations

1. **Database Metrics to Track**:
   - `enrollments` table size and row count
   - Query execution times (already have `query_performance_metrics` table)
   - Connection pool utilization
   - Cache hit rates

2. **Application Metrics**:
   - Notification send latency
   - Scraper duration and success rate
   - API response times by endpoint

3. **Vercel/Supabase Dashboards**:
   - Function execution duration
   - Database connections
   - Bandwidth usage

---

## Conclusion

SeatSteal is well-architected for its current scale with thoughtful optimizations already in place:
- Efficient database indexing
- Status-change-only enrollment storage
- Redis caching layer
- RLS policy optimization
- Batch database operations

The main areas for improvement are:
1. Frontend bundle optimization (code splitting)
2. Preparing for notification volume at scale
3. Monitoring for early detection of bottlenecks

The system should handle 10K-50K users comfortably with current architecture. The recommendations above will prepare it for growth beyond that.
