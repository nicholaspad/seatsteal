# Adding a New College to SeatSteal

This guide documents the complete process for onboarding a new college to the SeatSteal platform.

Prompt: I want to onboard a new college. Please look at ADD_COLLEGE.md for requirements for the college, especially the notes section. Please
target large colleges with a large userbase opportunity. Please present me with several options. Feel free to send curl requests to test
APIs.

---

## Requirements for New Colleges

Before adding a college, verify it meets these requirements:

1. **Publicly accessible API or website** for course catalog data
   - Can be a REST API, GraphQL, or HTML pages to scrape
   - Must not require authentication to access course data
   - Must be accessible if SeatSteal/1.0 is used as the User-Agent

2. **Enrollment status per class/section**
   - Must indicate whether a class is closed or open, either directly or via seat counts
   - Actual seat counts are NOT required - just open/closed status
   - The only statuses we care about are Open and Closed.

3. **Basic metadata available**
   - Course code (e.g., "CS 101", "MATH 200")
   - Course title (e.g., "Introduction to Computer Science")
   - Section/class identifier (e.g., "LEC 001", CRN number)
   - Term code


Notes:
- Colleges we tried and failed to scrape: UIUC (blocked with 403 errors), UMD (too slow), UF (blocked when run on AWS)
- Feel free to send curl requests to the college's API or website to verify that it meets the requirements.
- Make sure to target large colleges with a big userbase opportunity.
- Target American colleges only.

---

## Step 1: Register the College (User Manual Step)

The user must run the interactive script to create College and Scraper records in the database:

```bash
cd webapp
source venv/bin/activate
python scripts/add_college_scraper.py
```

**Prompts:**
- Full college name (e.g., "Yale University")
- Short name in lowercase, no spaces (e.g., "yale") - this is the unique identifier
- Domain (optional, e.g., "@yale.edu")
- Current term code (optional, get from Step 4 first if unknown)
- Current term name (optional, e.g., "Spring 2026")

This creates both a `College` record and a linked `Scraper` record.

---

## Step 2: Build the Scraper

Create a new scraper file at `scraper/scrapers/{college}.py`.

### Required Structure

```python
from typing import List, Dict, Any, Optional
import httpx
from scraper.base import BaseScraper
from scraper.utils.logger import scraper_logger as logger
from scraper.utils.term_code_db import get_term_code_from_db


class YaleScraper(BaseScraper):
    """
    Yale University course scraper.

    Scrapes course data from Yale's course catalog.
    """

    BASE_URL = "https://courses.yale.edu"  # Example

    def __init__(self, db_session=None):
        super().__init__("yale")  # Must match short_name in database
        self.current_term = get_term_code_from_db(db_session, "yale")
        self.client: Optional[httpx.AsyncClient] = None

    async def _ensure_client(self):
        """Ensure HTTP client is initialized"""
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "User-Agent": "SeatSteal/1.0",
                    "Accept": "application/json",
                },
            )

    async def scrape_courses(
        self, department: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape courses for a department or all courses.

        Args:
            department: Department code or 'ALL' for all courses
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries (see format below)
        """
        logger.info(
            f"Scraping Yale {department} courses (limit: {limit}, term: {self.current_term})"
        )

        await self._ensure_client()

        try:
            # Implement scraping logic here
            courses = await self._fetch_courses(department, limit)
            return courses
        except Exception as e:
            logger.error(f"Failed to scrape Yale {department}: {e}")
            raise
        finally:
            if self.client:
                await self.client.aclose()
                self.client = None

    async def _fetch_courses(
        self, department: str, limit: Optional[int]
    ) -> List[Dict[str, Any]]:
        """Implement the actual fetching logic here"""
        # Your implementation
        pass
```

### Required Return Format

The `scrape_courses()` method must return a list of dictionaries with this structure:

```python
[
    {
        "course_code": "CS 101",           # Required: course identifier
        "title": "Intro to Computer Science",  # Required: course title
        "classes": [
            {
                "class_number": "12345",   # Required: unique class/CRN identifier
                "section": "LEC 001",      # Required: section code
                "status": "Open"           # Required: "Open", "Closed", or "Waitlist"
            },
            {
                "class_number": "12346",
                "section": "DIS 002",
                "status": "Closed"
            }
        ]
    },
    # ... more courses
]
```

### Common Patterns

Reference existing scrapers for patterns:

| Pattern | Example Scraper | Description |
|---------|-----------------|-------------|
| FOSE API | `brown.py`, `upenn.py` | POST requests with URL-encoded JSON body |
| Banner 9 API | `bu.py`, `neu.py` | Paginated JSON API with session handling |
| HTML Scraping | `cornell.py` | Parse HTML pages with BeautifulSoup |
| REST API | `usc.py`, `rutgers.py` | Standard REST endpoints returning JSON |

### Key Implementation Notes

1. **Always use `get_term_code_from_db()`** to get the term code - no hardcoded values
2. **Use batch processing** for large datasets (process 50-100 courses concurrently)
3. **Add delays between batches** (`await asyncio.sleep(1)`) to avoid rate limiting
4. **Use the logger** for debugging: `from scraper.utils.logger import scraper_logger as logger`
5. **Deduplicate courses** if the API returns duplicate entries for different sections

---

## Step 3: Register the Scraper

Edit `scraper/services/scraper_service.py` to register the new scraper.

### Add Import

At the top of the file, add the import:

```python
from scraper.scrapers.yale import YaleScraper
```

### Add to SCRAPER_MAP

Add an entry to the `SCRAPER_MAP` dictionary (around line 24):

```python
SCRAPER_MAP = {
    "cornell": CornellScraper,
    "brown": BrownScraper,
    "rutgers": RutgersScraper,
    "bu": BuScraper,
    "neu": NeuScraper,
    "usc": UscScraper,
    "upenn": UPennScraper,
    "yale": YaleScraper,  # Add new entry
}
```

---

## Step 4: Add Term Code Fetcher

### Update `api/routes/term_codes.py`

Add a function to fetch term codes from the college's website:

```python
async def fetch_yale_terms() -> Tuple[str, List[dict], Optional[str]]:
    """Fetch term codes from Yale University."""
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.get("https://courses.yale.edu/api/terms")
            data = response.json()

        terms = []
        for term in data[:4]:
            code = term.get("code", "")
            name = term.get("name", "")
            terms.append({"code": str(code), "description": name})

        return ("success", terms, None)
    except Exception as e:
        return ("error", [], str(e))
```

Add to the `COLLEGE_FETCHERS` mapping:

```python
COLLEGE_FETCHERS = {
    "brown": fetch_brown_terms,
    "bu": fetch_bu_terms,
    "cornell": fetch_cornell_terms,
    "neu": fetch_neu_terms,
    "usc": fetch_usc_terms,
    "umd": fetch_umd_terms,
    "rutgers": fetch_rutgers_terms,
    "yale": fetch_yale_terms,  # Add new entry
}
```

### Update `scripts/term_codes_table.py`

Add a function to fetch term codes using curl (for the CLI tool):

```python
def fetch_yale_terms() -> List[Tuple[str, str]]:
    """Fetch term codes from Yale University."""
    try:
        result = subprocess.run(
            ["curl", "-s", "https://courses.yale.edu/api/terms"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        data = json.loads(result.stdout)
        terms = []
        for term in data[:4]:
            code = term.get("code", "")
            name = term.get("name", "")
            terms.append((str(code), name))

        return terms
    except Exception as e:
        return [("ERROR", str(e))]
```

Add to the `colleges` dictionary in `display_term_codes_table()`:

```python
colleges = {
    "brown": fetch_brown_terms,
    "bu": fetch_bu_terms,
    "cornell": fetch_cornell_terms,
    "neu": fetch_neu_terms,
    "usc": fetch_usc_terms,
    "umd": fetch_umd_terms,
    "rutgers": fetch_rutgers_terms,
    "yale": fetch_yale_terms,  # Add new entry
}
```

---

## Step 5: Update TERM_CODES.md

Add documentation for the new college's term code format in `TERM_CODES.md`:

```markdown
### Yale University

**Method:** API call to get available terms

**Steps:**

1. Use curl to get all available terms:
   ```bash
   curl -s "https://courses.yale.edu/api/terms" | python3 -c "import json,sys; [print(f\"{t['code']} - {t['name']}\") for t in json.load(sys.stdin)]"
   ```
2. Term code format: `YYYYTT` where:
   - `YYYY` = 4-digit year
   - `TT` = Term code (`10`=Fall, `20`=Spring, etc.)

**Example output:**

```
202610 - Spring 2026
202520 - Fall 2025
```

**Example term code:** `202610` (Spring 2026)
```

---

## Step 6: Test the Scraper

### Set the Term Code

First, ensure the term code is set in the database. Use the admin API or SQL:

```sql
UPDATE colleges
SET term_code = '202610', term_name = 'Spring 2026'
WHERE short_name = 'yale';
```

### Run the Scraper

```bash
cd webapp
source venv/bin/activate

# Test with a limit first
python scraper/run_scraper.py run --college yale

# Check logs for errors
# Look for: "Using term code from database for yale: 202610"
```

### Verify Data

Check that courses and classes were saved:

```sql
SELECT c.course_code, c.title, cl.class_number, cl.section_code
FROM courses c
JOIN classes cl ON c.id = cl.course_id
JOIN colleges col ON c.college_id = col.id
WHERE col.short_name = 'yale'
LIMIT 10;
```

---

## Checklist

- [ ] College meets requirements (public API, enrollment status, metadata)
- [ ] User ran `scripts/add_college_scraper.py` to register college
- [ ] Created `scraper/scrapers/{college}.py` with scraper implementation
- [ ] Added import and entry to `SCRAPER_MAP` in `scraper/services/scraper_service.py`
- [ ] Added `fetch_{college}_terms()` to `api/routes/term_codes.py`
- [ ] Added `fetch_{college}_terms()` to `scripts/term_codes_table.py`
- [ ] Added documentation to `TERM_CODES.md`
- [ ] Set term code in database
- [ ] Tested scraper with `python scraper/run_scraper.py run --college {college}`
- [ ] Verified data in database

---

## Troubleshooting

### "College not found in database"
Run `python scripts/add_college_scraper.py` to create the college record.

### "Term code for college is empty"
Set the term code using SQL or the admin API.

### "No scraper implementation found"
Add the scraper to `SCRAPER_MAP` in `scraper/services/scraper_service.py`.

### Scraper times out
- Increase timeout in the scraper's HTTP client
- Add more delays between batches
- Reduce batch size

### Rate limited by college API
- Increase delays between requests (`await asyncio.sleep()`)
- Use the base class's rate-limited methods (`fetch_json()`, `fetch_html()`)
