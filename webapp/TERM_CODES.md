# Term Code Configuration Guide

This guide explains how to manually retrieve and update term codes for each college scraper.

Term codes are stored in the `colleges` table in the database, with columns `term_code` and `term_name`. **All scrapers read term codes from the database at runtime** - there are no hardcoded fallbacks.

---

## How to Manually Get Term Codes

### Brown University

**Method:** Extract from the course search page dropdown

**Steps:**

1. Use curl to get all available terms:
   ```bash
   curl -s https://cab.brown.edu/ | grep -o '<option[^>]*value="[0-9]*"[^>]*>[^<]*</option>' | sed 's/<option[^>]*value="\([0-9]*\)"[^>]*>\([^<]*\)<.*/\1 - \2/' | grep -v "Any Term"
   ```
2. Term code format: `YYYYSS` where `SS` is semester code
   - `00` = Summer
   - `10` = Fall
   - `15` = Winter
   - `20` = Spring

**Example output:**

```
202520 - Spring 2026
202515 - Winter 2026
202510 - Fall 2025
202500 - Summer 2025
202420 - Spring 2025
```

**Example term code:** `202520` (Spring 2026)

---

### Boston University (BU)

**Method:** Manual browser inspection (requires JavaScript rendering)

**Steps:**

1. Visit: https://public.mybustudent.bu.edu/psp/BUPRD/EMPLOYEE/SA/s/WEBLIB_HCX_CM.H_CLASS_SEARCH.FieldFormula.IScript_Main?institution=BU001
2. Open browser developer tools (F12)
3. Find the term dropdown and inspect the `value` attributes
4. Term code format: `YYSM` where:
   - `YY` = last 2 digits of year
   - `S` = semester digit (2=Spring, 5=Summer, 8=Fall)
   - `M` = 8 (appears constant)

**Note:** BU's portal requires JavaScript and cannot be easily scraped via curl.

**Example term code:** `2258` (Fall 2025), `2618` (Spring 2026)

---

### Cornell University

**Method:** Extract from the class roster page menu

**Steps:**

1. Use curl to get all available terms:
   ```bash
   curl -s "https://classes.cornell.edu/browse/roster/SP26" | grep -o 'href="/browse/roster/[A-Z][A-Z][0-9][0-9]"[^>]*title="[^"]*"[^>]*>[^<]*</a>' | sed 's/.*roster\/\([A-Z][A-Z][0-9][0-9]\)"[^>]*>\([^<]*\)<.*/\1 - \2/' | grep -v 'clear\|Roster'
   ```
2. Term code format: `SSYY` where:
   - `SS` = Season code (`FA`=Fall, `SP`=Spring, `SU`=Summer, `WI`=Winter)
   - `YY` = 2-digit year

**Example output:**

```
SP26 - Spring 2026
WI26 - Winter 2026
FA25 - Fall 2025
SU25 - Summer 2025
```

**Example term code:** `FA25` (Fall 2025), `SP26` (Spring 2026)

---

### Northeastern University (NEU)

**Method:** API call to get available terms

**Steps:**

1. Use curl to get all available terms:
   ```bash
   curl -s "https://nubanner.neu.edu/StudentRegistrationSsb/ssb/classSearch/getTerms?offset=1&max=20&searchTerm=" | python3 -c "import json,sys; [print(f\"{t['code']} - {t['description']}\") for t in json.load(sys.stdin)]"
   ```
2. Term code format: `YYYYTT` where:
   - `YYYY` = 4-digit year
   - `TT` = Term code (`10`=Fall Semester, `30`=Spring Semester, `40`=Summer 1, `60`=Summer 2, etc.)

**Example output:**

```
202630 - Spring 2026 Semester
202625 - Winter 2026 CPS Quarter
202615 - Fall 2025 CPS Quarter
202610 - Fall 2025 Semester
202560 - Summer 2 2025 Semester
```

**Example term code:** `202610` (Fall 2025 Semester), `202630` (Spring 2026 Semester)

---

### Princeton University

**Method:** Manual browser inspection (has Cloudflare protection)

**Steps:**

1. Visit: https://registrar.princeton.edu/course-offerings
2. Open browser developer tools (F12)
3. Find the term dropdown and inspect the `value` attributes
4. Term code format: `1YSS` where:
   - `Y` = year offset (2=2025, 3=2026, etc.)
   - `SS` = Semester code (`62`=Fall, `64`=Spring)

**Note:** Princeton's site has Cloudflare bot protection and cannot be easily scraped via curl.

**Example term code:** `1262` (Fall 2025), `1264` (Spring 2026)

---

### University of Southern California (USC)

**Method:** API call to get all terms

**Steps:**

1. Use curl to get all available terms:
   ```bash
   curl -s "https://classes.usc.edu/api/Terms/All" | python3 -c "import json,sys; [print(f\"{t['termCode']} - {t['season']} {t['year']} ({t['status']})\") for t in json.load(sys.stdin)]"
   ```
2. Term code format: `YYYYT` where:
   - `YYYY` = 4-digit year
   - `T` = Term number (`1`=Spring, `2`=Summer, `3`=Fall)

**Example output:**

```
20261 - Spring 2026 (Active)
20253 - Fall 2025 (Active)
20252 - Summer 2025 (Active)
20251 - Spring 2025 (Inactive)
```

**Example term code:** `20253` (Fall 2025), `20261` (Spring 2026)

---

### University of Maryland (UMD)

**Method:** Scrape the Testudo Schedule of Classes page

**Steps:**

1. Use curl to get all available terms:
   ```bash
   curl -s "https://app.testudo.umd.edu/soc/" | grep 'id="term-id-input"' | grep -o '<option[^>]*>[^<]*</option>' | sed 's/<option value="\([0-9]*\)"[^>]*>\([^<]*\)<\/option>/\1 - \2/'
   ```
2. Term code format: `YYYYMM` where MM is the month the semester starts
   - `01` = Winter/Spring (January)
   - `05` = Summer (May)
   - `08` = Fall (August)
   - `12` = Winter (December)

**Example output:**

```
202505 - Summer 2025
202508 - Fall 2025
202512 - Winter 2026
202601 - Spring 2026
```

**Example term code:** `202601` (Spring 2026)

---

### Rutgers University

**Method:** Extract from embedded JSON and generate available terms (Rutgers uses current + 8 previous semesters)

**Steps:**

1. Use curl to get all available terms:
   ```bash
   curl -s "https://classes.rutgers.edu/soc/" | grep -o '"currentTermDate":{[^}]*}' | python3 -c "
   import json, sys
   d = json.loads('{'+sys.stdin.read()+'}')
   t = d['currentTermDate']
   year, term = t['year'], t['term']
   names = {0:'Winter',1:'Spring',7:'Summer',9:'Fall'}
   order = {9:7, 7:1, 1:0, 0:9}
   terms = []
   for _ in range(9):
       terms.append(f'{year}:{term}:NB - {names[term]} {year}')
       if term == 0: year -= 1
       term = order[term]
   for t in terms: print(t)
   "
   ```
2. Term code format: `year:term:campus`
3. Term codes:
   - `1`=Spring, `7`=Summer, `9`=Fall, `0`=Winter
   - Campus: `NB`=New Brunswick, `NK`=Newark, `CM`=Camden

**Example output:**

```
2026:1:NB - Spring 2026
2026:0:NB - Winter 2026
2025:9:NB - Fall 2025
2025:7:NB - Summer 2025
2025:1:NB - Spring 2025
2025:0:NB - Winter 2025
2024:9:NB - Fall 2024
2024:7:NB - Summer 2024
2024:1:NB - Spring 2024
```

**Note:** Replace `NB` in the script with `NK` or `CM` for Newark or Camden campuses.

**Example term code:** `2026:1:NB` (Spring 2026, New Brunswick campus)

---

### University of Pennsylvania (UPenn)

**Method:** Extract from the course search page dropdown

**Steps:**

1. Use curl to get all available terms:
   ```bash
   curl -s https://courses.upenn.edu/ | grep -o '<option[^>]*value="[0-9]*"[^>]*>[^<]*</option>' | sed 's/<option[^>]*value="\([0-9]*\)"[^>]*>\([^<]*\)<.*/\1 - \2/' | grep -E '^[0-9]{6}'
   ```
2. Term code format: `YYYYSS` where `SS` is semester code
   - `10` = Spring
   - `20` = Summer
   - `30` = Fall

**Example output:**

```
202610 - Spring 2026
202530 - Fall 2025
202520 - Summer 2025
202510 - Spring 2025
202430 - Fall 2024
```

**Example term code:** `202610` (Spring 2026)

---

## Updating Term Codes in the Database

Once you have retrieved the current term code for a college, update it in the database:

### Using SQL

```sql
UPDATE colleges
SET term_code = 'NEW_TERM_CODE',
    term_name = 'Fall 2025'  -- or appropriate term name
WHERE short_name = 'college_short_name';
```

### Using Python Script

```python
from sqlalchemy import select, update
from models.college import College
from database import SessionLocal

db = SessionLocal()
try:
    # Update term code
    db.execute(
        update(College)
        .where(College.short_name == "bu")
        .values(term_code="2258", term_name="Fall 2025")
    )
    db.commit()
    print("Term code updated successfully")
except Exception as e:
    db.rollback()
    print(f"Error updating term code: {e}")
finally:
    db.close()
```

### Verification

After updating, verify the scraper can read the term code:

```bash
cd webapp
source venv/bin/activate
python scraper/run_scraper.py run --college bu --subject CS --limit 5
```

The log should show: `Using term code from database for bu: 2258`

---

## Important Notes

- **No hardcoded fallbacks:** If a term code is missing or empty in the database, scrapers will raise an error rather than using a fallback value
- **Check regularly:** Term codes change each semester (typically Fall, Spring, Summer)
- **Test after updates:** Always test the scraper after updating term codes to ensure it works correctly
- **Consistent format:** Each college has its own term code format - follow the examples above

---

## Troubleshooting

### Error: "College not found in database"

The college doesn't exist in the `colleges` table. Add it using:

```bash
python scripts/add_college.py "College Name" short_name college.edu
```

### Error: "Term code for college is empty"

The `term_code` column is NULL or empty. Update it using the SQL or Python methods above.

### Scraper fails with term code

The term code might be outdated or incorrect. Follow the retrieval steps above to get the current term code and update the database.
