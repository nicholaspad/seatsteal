# Term Codes Reference

This document describes the term code formats for each supported college.

---

## UC Irvine

**Format:** `YYYY:Quarter`

**Quarters:**
- `Winter` - Winter quarter (Jan-Mar)
- `Spring` - Spring quarter (Apr-Jun)
- `Summer1` - Summer Session 1
- `Summer10wk` - Summer 10-week session
- `Summer2` - Summer Session 2
- `Fall` - Fall quarter (Sep-Dec)

**Examples:**
- `2026:Spring` - Spring 2026
- `2025:Fall` - Fall 2025
- `2026:Winter` - Winter 2026

**API:** Uses the Anteater API (https://anteaterapi.com)

---

## Rutgers University

**Format:** `YYYY:T:CAMPUS`

**Term codes:**
- `0` - Winter
- `1` - Spring
- `7` - Summer
- `9` - Fall

**Campus codes:**
- `NB` - New Brunswick
- `NK` - Newark
- `CM` - Camden

**Examples:**
- `2025:9:NB` - Fall 2025, New Brunswick
- `2026:1:NB` - Spring 2026, New Brunswick

---

## Boston University

**Format:** 4-digit code (STRM format)

**Examples:**
- `2258` - Fall 2025
- `2262` - Spring 2026

---

## Cornell University

**Format:** `SSYY` (Season + 2-digit year)

**Season codes:**
- `SP` - Spring
- `SU` - Summer
- `FA` - Fall

**Examples:**
- `SP26` - Spring 2026
- `FA25` - Fall 2025

---

## Northeastern University

**Format:** 6-digit Banner code (YYYYTT)

**Examples:**
- `202610` - Spring 2026
- `202530` - Fall 2025

---

## USC

**Format:** 5-digit code (YYYYT)

**Examples:**
- `20261` - Spring 2026
- `20253` - Fall 2025

---

## University of Pennsylvania

**Format:** 6-digit code (YYYYTT)

**Examples:**
- `202610` - Spring 2026
- `202530` - Fall 2025

---

## Brown University

**Format:** 6-digit code (YYYYMM)

**Examples:**
- `202620` - Spring 2026
- `202510` - Fall 2025

---

## University of Maryland

**Format:** 6-digit code (YYYYMM)

**Examples:**
- `202601` - Spring 2026
- `202508` - Fall 2025

---

## University of Florida

**Format:** 4-digit code (TTTY where TTT=decade, Y=term)

**Term codes:**
- `1` = Spring
- `5` = Summer
- `8` = Fall

**Examples:**
- `2251` - Spring 2025 (225 + 1)
- `2258` - Fall 2025 (225 + 8)
- `2261` - Spring 2026 (226 + 1)

**API Method:** Fetch from public API

```bash
curl -s "https://one.uf.edu/apix/soc/terms" | python3 -c "import json,sys; [print(f\"{t['term']} - {t['termName']}\") for t in json.load(sys.stdin)[:4]]"
```

**Example output:**
```
2258 - Fall 2025
2251 - Spring 2025
2248 - Summer 2024
```

---

## Ohio State University

**Format:** `YYSN` (2-digit year + season + sequence digit)

**Season codes:**
- `2` - Spring
- `4` - Summer
- `6` - Autumn (Fall)

**Examples:**
- `1268` - Autumn 2026 (26 + 6 + 8)
- `1262` - Spring 2026 (26 + 2 + 2)
- `1264` - Summer 2026 (26 + 4 + 4)
- `1248` - Autumn 2024 (24 + 4 + 8)

**API:** Uses content.osu.edu public API (https://content.osu.edu/v2/classes/search)

**Note:** Term codes follow a YYSN pattern where YY is the year minus 2000, S is the season indicator, and N is typically 2 or 8 (sequence digit, purpose unknown).

---

## Arizona State University

**Format:** `2YYX` (4-digit STRM format)

**Pattern:**
- `2YY` - 200 + (year minus 2000), e.g., 226 for 2026
- `X` - Semester indicator:
  - `1` = Spring
  - `4` = Summer
  - `7` = Fall

**Examples:**
- `2267` - Fall 2026 (226 + 7)
- `2261` - Spring 2026 (226 + 1)
- `2264` - Summer 2026 (226 + 4)
- `2257` - Fall 2025 (225 + 7)

**API:** Uses eAdvs-CSCC Catalog API (https://eadvs-cscc-catalog-api.apps.asu.edu/catalog-microservices/api/v1)

**Note:** API requires `Authorization: Bearer null` header (returns 401 without it).

---

## Purdue University

**Format:** `YYYYTT` (6-digit Banner code)

**Pattern:**
- `YYYY` - 4-digit year
- `TT` - Term code:
  - `10` = Fall
  - `13` = Winter (intersession)
  - `20` = Spring
  - `30` = Summer

**Examples:**
- `202710` - Fall 2026
- `202713` - Winter 2026 (intersession)
- `202620` - Spring 2026
- `202530` - Summer 2025

**Source:** Uses official Banner self-service HTML pages (https://selfservice.mypurdue.purdue.edu/prod/)

**Method:** Banner term picker → POST course search by subject → parse CRN list → fetch detail pages for seat availability

**Important Notes:**
- **Term selection**: Banner term picker shows terms with and without "(View only)" suffix. Only terms WITHOUT "(View only)" are registerable. The scraper should use registerable terms.
- **Purdue.io API**: A public API exists at purdue.io but it is catalog-only (no real-time seat availability). Must use official Banner self-service for Open/Closed status.

---

## University of Illinois Urbana-Champaign

**Format:** `1202YYS` (6-digit code)

**Pattern:**
- `1202` - Prefix (constant)
- `YY` - 2-digit year (68 = 2026, 61 = 2026)
- `S` - Semester indicator:
  - `8` = Fall
  - `1` = Spring
  - `5` = Summer
  - `0` = Winter

**Examples:**
- `120268` - Fall 2026 (1202 + 68 + 8) → URL: `2026/fall`
- `120261` - Spring 2026 (1202 + 61 + 1) → URL: `2026/spring`
- `120265` - Summer 2026 (1202 + 65 + 5) → URL: `2026/summer`
- `120260` - Winter 2026 (1202 + 60 + 0) → URL: `2026/winter`

**Source:** https://courses.illinois.edu

**API Strategy:**
1. Discovery XML: `/cisapp/explorer/schedule/{year}/{season}.xml` (subject index)
2. Summary XML: `/cisapp/explorer/schedule/{year}/{season}/{subject}.xml` (course IDs per subject)
3. Detail HTML: `/schedule/{year}/{season}/{subject}/{course}` (parse CRN, section, availability from table)

**Status Mapping:**
- HTML Availability field used (NOT XML statusCode/sectionStatusCode):
  - `Open`, `Open (Restricted)`, `CrossListOpen`, `CrossListOpen (Restricted)` → Open
  - `Closed`, `Pending`, `Unknown`, missing/malformed → Closed

**Notes:**
- Do NOT use XML `statusCode` or `sectionStatusCode` for availability (observed "A" on Closed sections)
- Always parse HTML `#schedule-course-table` → `Availability` dd element or status icon `aria-label`
- Global CRN deduplication required (cross-listed courses share CRNs)
- Bounded concurrency (4 course pages max) + retry/backoff for 429/5xx
- Request budget: 10,000 max to prevent runaway scraping

---

## NC State University

**Format:** `YYYS` (4-digit STRM format)

**Pattern:**
- `YYY` - Year since 1900 (e.g., 226 = 2026)
- `S` - Session digit:
  - `8` = Fall
  - `1` = Spring
  - `5` = Summer I
  - `6` = Summer II

**Examples:**
- `2268` - Fall 2026 (226 + 8)
- `2271` - Spring 2027 (227 + 1)
- `2265` - Summer I 2026 (226 + 5)
- `2258` - Fall 2025 (225 + 8)

**Source:** Public ACS Class Search (PeopleSoft) at https://webappprd.acs.ncsu.edu/php/coursecat

**API Strategy:**
1. POST `subjects.php` with `strm=<TERM>` to get subject list
2. POST `search.php` with form data (term, subject, etc.) to search courses
   - Do NOT send `open-classes=1` (would drop Closed sections)
3. Parse JSON response: Content-Type may say `text/html` but body is JSON `{"html":..., "json":...}`
4. Deduplicate globally by Class # (class_nbr) before grouping by course

**Status Mapping:**
- `Open` → Open
- `Closed`, `Reserved`, `Waitlist`, unknown → Closed
  - Reserved→Closed enables reserve-release alerts

**CRITICAL Department Trap:**
- **CS = Crop Science** (NOT Computer Science!)
- **CSC = Computer Science**
- ONLY allowlist CSC for Computer Science courses
- Never allowlist CS as CompSci

**Notes:**
- Use Class # (class_nbr) as the unique identifier, not section alone
- User-Agent: SeatSteal/1.0
- Request budget: 50 max for single-department scraping (CSC)
- ALL department maps to CSC allowlist only (never expands to full ~199-subject catalog)

---

## Quick Reference Tool

Run the term codes table script to fetch current term codes for all colleges:

```bash
cd webapp
source venv/bin/activate
python scripts/term_codes_table.py
```
