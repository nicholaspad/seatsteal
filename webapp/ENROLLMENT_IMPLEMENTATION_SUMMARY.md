# Enrollment Status-Change Storage Implementation Summary

## Overview

Successfully implemented a status-change-only storage pattern for the enrollments table that reduces table growth by approximately **90-97%** while preserving all meaningful data and tracking the last scrape time for each class.

## Implementation Details

### Approach: INSERT + UPDATE Hybrid

The implementation uses a smart INSERT/UPDATE strategy:

1. **Status Changed** → INSERT new enrollment record
   - Example: closed → open or open → closed
   - Creates new row with new status and scraped_at timestamp

2. **Status Unchanged** → UPDATE existing enrollment's scraped_at
   - Example: closed → closed or open → open  
   - Updates the existing row's timestamp without creating new row

3. **First Scrape** → INSERT first enrollment record
   - Classes with no previous enrollment get their first record inserted

### Files Modified

#### 1. Scraper Service (`webapp/scraper/services/scraper_service.py`)

**Modified Method: `_batch_insert_enrollments()`**
- Added status-change detection logic
- Separates enrollment data into inserts vs updates
- Batch processes both operations efficiently
- Returns count of inserts (not updates)

**New Method: `_get_latest_enrollments()`**
- Fetches most recent enrollment for each class_id
- Uses PostgreSQL's `DISTINCT ON` for efficiency
- Returns dict mapping class_id to {id, status}

**New Method: `_batch_update_enrollment_timestamps()`**
- Updates scraped_at for unchanged statuses
- Processes updates in batches for performance
- Uses raw SQL UPDATE for efficiency

#### 2. Enrollment Model (`webapp/models/enrollment.py`)

**Updated Documentation:**
- Added comprehensive docstring explaining status-change-only behavior
- Clarified that scraped_at represents last scrape time
- Documents that scraped_at may be updated multiple times for same record

#### 3. Migration (`webapp/alembic/versions/006_enrollment_status_change_storage.py`)

**Added:**
- Table comment documenting status-change-only behavior
- Column comment on scraped_at explaining its dual purpose
- Proper upgrade/downgrade functions

#### 4. Tests (`webapp/tests/test_scrapers/test_scraper_service.py`)

**Comprehensive Test Coverage:**
- First enrollment insert for new class
- Status change closed → open (insert)
- Status change open → closed (insert)
- Status unchanged closed → closed (update timestamp only)
- Status unchanged open → open (update timestamp only)
- Batch processing with mixed scenarios (inserts + updates)
- Helper method functionality (`_get_latest_enrollments`)
- Edge cases (empty lists, etc.)

#### 5. Query Verification (`webapp/ENROLLMENT_QUERY_VERIFICATION.md`)

**Verified All Existing Queries:**
- Notification service queries ✅
- Enrollment analysis queries ✅
- Admin analytics queries ✅
- All queries fully compatible, some actually improved

## Expected Impact

### Before Implementation (Every 5 min scraping, 10K classes)
- **Records per day:** 10,000 classes × 288 scrapes/day = 2.88M records/day
- **30-day table size:** ~86.4M rows
- **Write operations:** 2.88M INSERTs/day

### After Implementation (Assuming 10 status changes/class/day avg)
- **Records per day:** 10,000 classes × 10 changes/day = 100K records/day
- **30-day table size:** ~3M rows (**97% reduction!**)
- **Write operations:** 100K INSERTs + 2.78M UPDATEs/day
  - Note: UPDATEs are generally faster than INSERTs
  - Index maintenance only on 100K inserts vs 2.88M

### Benefits

1. **Massive Storage Reduction:** 97% fewer rows in 30-day retention window
2. **Improved Query Performance:** Fewer rows to scan for all queries
3. **Cleaner Analytics:** No consecutive duplicate statuses cluttering data
4. **Maintained Functionality:** All existing queries work without changes
5. **Scrape Tracking:** Can still track when each class was last scraped via scraped_at

### Trade-offs

1. **More Complex Logic:** Scraper now does status comparison before insert/update
2. **Additional Query:** Must fetch latest enrollments before deciding insert vs update
3. **Timestamp Semantics:** scraped_at represents "last scrape" not "exact status change moment" for rows that get updated multiple times

## Deployment Steps

### 1. Run Database Migration
```bash
cd webapp
alembic upgrade head
```

This adds comments to the database documenting the new behavior.

### 2. Deploy Updated Code

The changes are backward compatible and can be deployed immediately after the migration.

### 3. Monitor Performance (24-48 hours)

Watch for:
- Enrollment insert rates (should drop ~90%)
- Update operation performance on enrollments table
- Query performance (should improve with fewer rows)
- Scraper execution time (slight increase due to status comparison)

### 4. Optional: Clean Up Historical Data

Consider running a one-time script to deduplicate historical enrollments:
```sql
-- Example cleanup: Remove consecutive duplicate statuses
-- (Keep first occurrence of each status change)
DELETE FROM enrollments e1
WHERE EXISTS (
    SELECT 1 FROM enrollments e2
    WHERE e2.class_id = e1.class_id
    AND e2.scraped_at > e1.scraped_at
    AND e2.enrollment_status = e1.enrollment_status
    AND NOT EXISTS (
        SELECT 1 FROM enrollments e3
        WHERE e3.class_id = e1.class_id
        AND e3.scraped_at > e1.scraped_at
        AND e3.scraped_at < e2.scraped_at
        AND e3.enrollment_status != e1.enrollment_status
    )
);
```

**Warning:** Test this cleanup query thoroughly before running in production. It will permanently delete data.

## Testing

Run the test suite to verify implementation:
```bash
cd webapp
python -m pytest tests/test_scrapers/test_scraper_service.py -v
```

All 9 test cases should pass, covering:
- Insert scenarios
- Update scenarios  
- Mixed batch processing
- Helper method functionality

## Monitoring Queries

### Check Insert vs Update Ratio
```sql
-- Monitor over time to see the ~90% reduction
SELECT 
    DATE(scraped_at) as date,
    COUNT(*) as total_enrollments,
    COUNT(*) / COUNT(DISTINCT class_id) as avg_records_per_class
FROM enrollments
WHERE scraped_at > NOW() - INTERVAL '7 days'
GROUP BY DATE(scraped_at)
ORDER BY date DESC;
```

### Verify Status Changes Are Captured
```sql
-- Should show status transitions without consecutive duplicates
SELECT 
    class_id,
    enrollment_status,
    scraped_at,
    LAG(enrollment_status) OVER (PARTITION BY class_id ORDER BY scraped_at) as prev_status
FROM enrollments
WHERE class_id = <some_class_id>
ORDER BY scraped_at DESC
LIMIT 20;
```

### Check Table Size Reduction
```sql
-- Compare table size over time
SELECT 
    pg_size_pretty(pg_total_relation_size('enrollments')) as total_size,
    pg_size_pretty(pg_relation_size('enrollments')) as table_size,
    pg_size_pretty(pg_total_relation_size('enrollments') - pg_relation_size('enrollments')) as indexes_size,
    (SELECT COUNT(*) FROM enrollments) as row_count;
```

## Rollback Plan

If issues arise, you can rollback:

### 1. Revert Code Changes
Revert the commits to `scraper_service.py` to restore original insert-only behavior.

### 2. Rollback Migration (Optional)
```bash
alembic downgrade -1
```

This removes the table/column comments but doesn't affect data.

## Success Criteria

✅ **Completed:**
- [x] Modified scraper service with status-change detection
- [x] Added helper methods for fetching latest enrollments
- [x] Added batch timestamp update method
- [x] Updated enrollment model documentation
- [x] Created database migration
- [x] Wrote comprehensive test suite (9 test cases)
- [x] Verified all existing queries remain compatible
- [x] Documented implementation and impact

✅ **Expected Results:**
- 90-97% reduction in enrollment table growth
- All existing queries continue to work
- Scraper can still track last scrape time per class
- No data loss of meaningful status transitions

## Conclusion

The implementation successfully addresses the unbounded growth of the enrollments table while maintaining all critical functionality. The hybrid INSERT/UPDATE approach provides the best of both worlds:
- Minimal storage for stable status periods (UPDATE timestamps)
- Full history of status changes (INSERT new rows)
- Ability to track when classes were last scraped

This should keep your table size manageable even with aggressive scraping schedules and many classes.

