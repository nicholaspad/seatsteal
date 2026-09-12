# Rutgers Term Flip Operations Guide

## Problem Context

Rutgers is currently on Spring 2026 term `2026:1:NB` while the Fall 2026 Schedule of Classes (SOC) already exists. This causes leftover classes from the old term to persist in the database without enrollment snapshots, resulting in "?" status in the UI.

**Example leftover classes:**
- Rutgers Odasis 01:001:161 sections Z4/Z2
- CRNs: 24073, 24075
- Created: December 2025
- Last touched: ~February 5 (freeze)
- Not in current Fall 2026 SOC
- No enrollment snapshots → UI shows "?"

## Root Cause

The `term_code` lives only on the `colleges` table (no term column on `courses`/`classes`/`enrollments`). When a college's term flips to a new semester:
1. Scraper starts fetching the new term's SOC
2. Old term classes remain in the database
3. Classes without enrollment snapshots show "?" in the UI (fixed by this PR)

## Solution (After This PR Lands)

After the API filter fix (this PR) is deployed, classes without enrollment will be hidden from the UI. However, stale data will remain in the database. To clean up:

### Step 1: Verify Current Rutgers Term

```bash
# Check current term_code for Rutgers
psql $DATABASE_URL -c "SELECT id, name, short_name, term_code, term_name FROM colleges WHERE short_name = 'rutgers';"
```

Expected current state: `2026:1:NB` (Spring 2026)
Target state: `2026:9:NB` (Fall 2026)

### Step 2: Dry-Run Purge (Preview Deletions)

```bash
cd webapp

# Preview what will be deleted - enrollments scraped before Feb 1, 2026
python scripts/purge_stale_term_enrollments.py \
  --college rutgers \
  --before-scraped-at "2026-02-01T00:00:00Z"
```

**Review the output:**
- Stale enrollments count
- Orphan classes count (classes with no remaining enrollments)
- Empty courses count (courses with no remaining classes)
- ⚠️ **CRITICAL:** Blocking subscriptions count (classes with active subscriptions)

**If blocking subscriptions exist:**
- Users are still subscribed to old-term classes
- Script will abort by default (safe behavior)
- Options:
  1. **Recommended:** Manually deactivate those subscriptions in admin panel first
  2. **Advanced:** Use `--force-skip-subscribed` to skip (not delete) subscribed classes

### Step 3: Execute Purge (After Review)

```bash
# Only run after reviewing dry-run output and confirming it's safe
python scripts/purge_stale_term_enrollments.py \
  --college rutgers \
  --before-scraped-at "2026-02-01T00:00:00Z" \
  --confirm
```

**What gets deleted:**
- ✅ Enrollments scraped before cutoff
- ✅ Classes with no remaining enrollments (NEVER classes with subscriptions)
- ✅ Courses with no remaining classes
- ❌ NEVER deletes subscriptions
- ❌ NEVER deletes notification_logs
- ❌ NEVER deletes classes with active subscriptions

### Step 4: Update Rutgers Term Code

```bash
# Update college term_code to Fall 2026
psql $DATABASE_URL -c "UPDATE colleges SET term_code = '2026:9:NB', term_name = 'Fall 2026' WHERE short_name = 'rutgers';"
```

### Step 5: Verify Scraper

Trigger a scraper run for Rutgers to verify it fetches Fall 2026 classes correctly:

```bash
# Check scraper logs after next scheduled run
# Or manually trigger if scraper supports manual runs
```

### Step 6: Verify UI

1. Navigate to Rutgers courses in the UI
2. Confirm:
   - No "?" statuses appear (handled by this PR's filter)
   - Only Fall 2026 classes are visible
   - Classes have valid enrollment statuses (open/closed)

## Safeguards

The purge script has multiple safety measures:

1. **Dry-run by default** - requires `--confirm` to delete
2. **Subscription guard** - aborts if subscriptions exist (unless `--force-skip-subscribed`)
3. **Never deletes subscriptions** - even with `--force-skip-subscribed`
4. **Never deletes notification_logs** - preserved for audit trail
5. **Only deletes classes without enrollments** - classes with new-term enrollments are kept

## Alternative: Wait for Natural Cleanup

If the purge is deemed too risky, the stale classes will naturally become invisible after this PR:
- ✅ UI filter hides classes without enrollment (this PR)
- ✅ No "?" statuses appear
- ⚠️ Stale data remains in database (low priority)

The database cleanup can be performed later during a scheduled maintenance window.

## Emergency Rollback

If issues arise after the purge:

```bash
# Restore from backup taken before Step 3
# Contact DBA team with timestamp of purge execution
```

**Important:** Take a database backup before running `--confirm` in production!

## Timeline

1. **Now:** Deploy this PR (API filter for hiding no-enrollment classes)
2. **After deployment:** Verify UI no longer shows "?"
3. **Scheduled maintenance:** Execute purge + term flip (Steps 1-6)
4. **Post-verification:** Monitor scraper and user reports

## References

- Purge script: `webapp/scripts/purge_stale_term_enrollments.py`
- Original issue: #222 (purge pattern)
- This PR: Implements general hide rule for classes without enrollment
