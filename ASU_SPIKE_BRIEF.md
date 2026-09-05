# ASU Scraper Spike Brief

**Status:** Spike-only PR (no production rollout)

## Goal
Add ASU scraper implementation + registration + unit tests + TERM_CODES docs. Research/impl only.

## HARD CONSTRAINTS (do not violate)
- Do NOT create/seed colleges or scrapers DB rows
- Do NOT set is_active / flip any school live
- Do NOT change EC2 / Docker deploy config for onboard
- Do NOT add marketing copy
- PR description must state: **no live without board OK**
- Keep existing shared class_list dedupe in scraper_service.py (from OSU work) — do not regress it

## Implementation Summary

### API Details
- **Classes endpoint:** `https://eadvs-cscc-catalog-api.apps.asu.edu/catalog-microservices/api/v1/search/classes`
- **Subjects endpoint:** `https://eadvs-cscc-catalog-api.apps.asu.edu/catalog-microservices/api/v1/search/subjects?term=<STRM>`
- **Required headers:**
  - `Authorization: Bearer null` (401 without it)
  - `Accept: application/json`
  - `User-Agent: SeatSteal/1.0`
- **Pagination:** Elasticsearch-style `scrollId` with 200 max page size
- **Strategy:** Fetch subjects for term → for each subject fetch classes with `refine=Y&subject=&term=` then scroll
- **Rate limiting:** 100-200ms between calls, exponential backoff on 429/5xx
- **v1 scope:** All campuses (no campus=TEMPE filter)

### Term Codes
- **Format:** `2YYX` (STRM pattern)
  - `2YY` = 200 + (year - 2000)
  - `X` = semester (1=Spring, 4=Summer, 7=Fall)
- **Example:** `2267` = Fall 2026 (226 + 7)
- **Usage:** `get_term_code_from_db(db_session, "asu")` only — no hardcoded prod terms
- **Tests:** Mock term → `2267` (Fall 2026)

### Field Mapping
- `course_code = f"{SUBJECT} {CATALOGNBR}"`
- `title` from `COURSETITLELONG` (fallback to `TITLE`)
- `CLASSNBR` → `class_number` (string)
- `CLASSSECTION` → `section`
- `ENRLSTAT` mapping:
  - `O` → `Open`
  - `C` → `Closed`
  - Unknown → `Closed` (conservative, logged)
- Deduplicate courses by `course_code`, classes by `class_number` inside transform

### Return Format
```python
[
    {
        "course_code": "CSE 110",
        "title": "Principles of Programming",
        "classes": [
            {
                "class_number": "63179",
                "section": "2101",
                "status": "Open"
            }
        ]
    }
]
```

## Files Added/Modified

### Added
1. `webapp/scraper/scrapers/asu.py` — AsuScraper(BaseScraper), short_name "asu"
2. `webapp/tests/test_scrapers/test_asu.py` — Unit tests with fixtures for:
   - Subject list fetching
   - Multi-page scrollId pagination
   - ENRLSTAT mapping (O→Open, C→Closed, unknown→Closed)
   - CLASSNBR identity verification
   - Title fallback (COURSETITLELONG → TITLE)
   - Class deduplication

### Modified
1. `webapp/scraper/services/scraper_service.py` — Registered `SCRAPER_MAP["asu"] = AsuScraper`
2. `webapp/TERM_CODES.md` — Added ASU section with 2YYX pattern documentation

## Success Criteria
- [x] Unit tests pass
- [x] PR open against main with clear description linking spike scope and no-live gate
- [x] Small focused diff — no Black reformatting across unrelated files
- [x] ASU documentation in TERM_CODES.md
- [ ] Report PR URL when done

## Implementation Notes

### Pagination Strategy
- scrollId-based pagination (Elasticsearch-style)
- First request: no scrollId → returns data + scrollId
- Subsequent requests: include scrollId from previous response
- Stop when: empty classes array OR no scrollId returned
- Safety cap: max 50 pages per subject

### Error Handling
- 429 (rate limit): exponential backoff, retry
- 5xx (server error): log warning, stop pagination for that subject
- Empty page: normal end of pagination
- Missing required fields (SUBJECT, CATALOGNBR, CLASSNBR): skip with warning

### Deduplication
- Courses deduplicated by `course_code` during grouping
- Classes deduplicated by `class_number` within each course
- Maintains existing scraper_service.py class_list dedupe (from OSU work)

## Testing Notes

Test fixtures include:
- Mock DB session with term_code="2267"
- Sample subject list response
- Multi-page scrollId pagination responses
- Various ENRLSTAT values (O, C, unknown)
- Duplicate class_number scenarios

Run tests:
```bash
cd webapp
source venv/bin/activate
pytest tests/test_scrapers/test_asu.py -v
```

## Live API Fixes (2026-09-04)

**CRITICAL:** Two API contract mismatches discovered during live testing and fixed:

### 1. Subjects Endpoint - Nested Structure
**Issue:** API returns subjects nested by college group, not a flat list
```json
{
  "LS": [{"SUBJECT": "ABC", "SUBJECTDESCR": "..."}, ...],
  "BA": [{"SUBJECT": "...", "SUBJECTDESCR": "..."}, ...],
  ...
}
```
**Impact:** Original code only handled flat list → returned empty subjects → zero courses scraped  
**Fix:** Iterate all dict values, flatten, and dedupe subjects. Kept flat list fallback for backward compatibility.

### 2. Classes Endpoint - CLAS Wrapper
**Issue:** Class rows wrap PeopleSoft fields under `CLAS` key
```json
{
  "CLAS": {
    "SUBJECT": "CSE",
    "CATALOGNBR": "110",
    "CLASSNBR": 62688,  // Returns int, not string
    "CLASSSECTION": "...",
    "ENRLSTAT": "O"
  },
  "seatInfo": {...}
}
```
**Impact:** Original code read from top level → all fields missing → skipped all classes  
**Fix:** Extract payload from `CLAS` wrapper if present, handle `CLASSNBR` as int. Kept top-level fallback for test fixtures.

### Test Updates
- **19 tests pass** (up from 14)
- Added nested subjects fixtures
- Added CLAS wrapper fixtures  
- Added backward compatibility tests
- Added full integration test
- **Coverage: 80%** (up from 79%)

## Known Limitations / Future Work

1. **No campus filtering** in v1 — fetches all ASU campuses
2. **scrollId restart behavior** on error not fully validated (may need per-subject restart)
3. **Page size** hard-capped at 200 by API (cannot be increased)
4. **Rate limits** not precisely documented — using conservative 100-200ms delays

## References

- Existing scrapers: `osu.py`, `neu.py`, `uf.py`
- ADD_COLLEGE.md for onboarding patterns
- TERM_CODES.md for term code format standards
