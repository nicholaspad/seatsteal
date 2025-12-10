"""Term codes API routes for fetching available term codes from college websites"""

import re
import json
import base64
from typing import List, Tuple, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from models.user import Profile
from api.middleware.auth import require_admin

router = APIRouter(prefix="/api/admin/term-codes", tags=["admin", "term-codes"])

# HTTP client timeout in seconds
HTTP_TIMEOUT = 10.0


async def fetch_brown_terms() -> Tuple[str, List[dict], Optional[str]]:
    """Fetch term codes from Brown University."""
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.get("https://cab.brown.edu/")
            html = response.text

        # Extract option tags with term codes
        pattern = r'<option[^>]*value="(\d+)"[^>]*>([^<]+)</option>'
        matches = re.findall(pattern, html)

        terms = []
        for code, name in matches:
            name = name.strip()
            if "Any Term" not in name and code.isdigit():
                terms.append({"code": code, "description": name})

        return ("success", terms[:4], None)
    except Exception as e:
        return ("error", [], str(e))


async def fetch_bu_terms() -> Tuple[str, List[dict], Optional[str]]:
    """Fetch term codes from Boston University."""
    try:
        url = "https://public.mybustudent.bu.edu/psc/BUPRD/EMPLOYEE/SA/s/WEBLIB_HCX_CM.H_CLASS_SEARCH.FieldFormula.IScript_Main?institution=BU001"
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.get(
                url, headers={"Cookie": "public-PORTAL-PSJSESSIONID=1;"}
            )
            html = response.text

        # Extract base64-encoded JSON from atob(`...`)
        pattern = r"atob\(`([^`]+)`\)"
        match = re.search(pattern, html)

        if not match:
            return ("error", [], "Could not find base64 data")

        # Decode base64 and parse JSON
        b64_data = match.group(1)
        json_str = base64.b64decode(b64_data).decode("utf-8")
        data = json.loads(json_str)

        # Extract terms from search_options
        terms_data = data.get("search_options", {}).get("terms", [])
        terms = []
        for term in terms_data[:4]:
            code = term.get("strm", "")
            desc = term.get("descr", "")
            terms.append({"code": str(code), "description": desc})

        return ("success", terms, None) if terms else ("error", [], "No terms found")
    except Exception as e:
        return ("error", [], str(e))


async def fetch_cornell_terms() -> Tuple[str, List[dict], Optional[str]]:
    """Fetch term codes from Cornell University."""
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.get(
                "https://classes.cornell.edu/browse/roster/SP26"
            )
            html = response.text

        # Extract roster links with term codes
        pattern = r'href="/browse/roster/([A-Z]{2}\d{2})"[^>]*>([^<]+)</a>'
        matches = re.findall(pattern, html)

        terms = []
        seen = set()
        for code, name in matches:
            name = name.strip()
            if (
                name
                and "clear" not in name.lower()
                and "Roster" not in name
                and code not in seen
            ):
                seen.add(code)
                terms.append({"code": code, "description": name})

        return ("success", terms[:4], None)
    except Exception as e:
        return ("error", [], str(e))


async def fetch_neu_terms() -> Tuple[str, List[dict], Optional[str]]:
    """Fetch term codes from Northeastern University."""
    try:
        url = "https://nubanner.neu.edu/StudentRegistrationSsb/ssb/classSearch/getTerms?offset=1&max=20&searchTerm="
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.get(url)
            data = response.json()

        terms = []
        for term in data[:4]:
            code = term.get("code", "")
            desc = term.get("description", "")
            terms.append({"code": str(code), "description": desc})

        return ("success", terms, None)
    except Exception as e:
        return ("error", [], str(e))


async def fetch_usc_terms() -> Tuple[str, List[dict], Optional[str]]:
    """Fetch term codes from USC."""
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.get("https://classes.usc.edu/api/Terms/All")
            data = response.json()

        terms = []
        for term in data[:4]:
            code = term.get("termCode", "")
            season = term.get("season", "")
            year = term.get("year", "")
            status_val = term.get("status", "")
            name = f"{season} {year} ({status_val})"
            terms.append({"code": str(code), "description": name})

        return ("success", terms, None)
    except Exception as e:
        return ("error", [], str(e))


async def fetch_umd_terms() -> Tuple[str, List[dict], Optional[str]]:
    """Fetch term codes from University of Maryland."""
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.get("https://app.testudo.umd.edu/soc/")
            html = response.text

        # Find the term dropdown section
        pattern = r'<option value="(\d+)"[^>]*>([^<]+)</option>'
        matches = re.findall(pattern, html)

        terms = []
        for code, name in matches:
            name = name.strip()
            if code.isdigit() and len(code) == 6:  # UMD uses 6-digit codes
                terms.append({"code": code, "description": name})

        return ("success", terms[:4], None)
    except Exception as e:
        return ("error", [], str(e))


async def fetch_rutgers_terms() -> Tuple[str, List[dict], Optional[str]]:
    """Fetch term codes from Rutgers University."""
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.get("https://classes.rutgers.edu/soc/")
            html = response.text

        # Extract currentTermDate from embedded JSON
        pattern = r'"currentTermDate":\s*\{([^}]+)\}'
        match = re.search(pattern, html)

        if not match:
            return ("error", [], "Could not find currentTermDate")

        # Parse the JSON object
        json_str = "{" + match.group(1) + "}"
        term_data = json.loads(json_str)

        year = term_data.get("year", 2025)
        term = term_data.get("term", 9)

        # Generate term codes (current + previous 3)
        term_names = {0: "Winter", 1: "Spring", 7: "Summer", 9: "Fall"}
        term_order = {9: 7, 7: 1, 1: 0, 0: 9}  # Reverse chronological

        terms = []
        for _ in range(4):
            code = f"{year}:{term}:NB"
            name = f"{term_names.get(term, 'Unknown')} {year}"
            terms.append({"code": code, "description": name})

            # Move to previous term
            if term == 0:
                year -= 1
            term = term_order.get(term, 9)

        return ("success", terms, None)
    except Exception as e:
        return ("error", [], str(e))


async def fetch_upenn_terms() -> Tuple[str, List[dict], Optional[str]]:
    """Fetch term codes from University of Pennsylvania."""
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.get("https://courses.upenn.edu/")
            html = response.text

        # Extract option tags with term codes
        pattern = r'<option[^>]*value="(\d+)"[^>]*>([^<]+)</option>'
        matches = re.findall(pattern, html)

        terms = []
        for code, name in matches:
            name = name.strip()
            # Filter out non-term options (instruction methods, etc.)
            if code.isdigit() and len(code) == 6:
                terms.append({"code": code, "description": name})

        return ("success", terms[:4], None)
    except Exception as e:
        return ("error", [], str(e))


# College fetch function mapping
COLLEGE_FETCHERS = {
    "brown": fetch_brown_terms,
    "bu": fetch_bu_terms,
    "cornell": fetch_cornell_terms,
    "neu": fetch_neu_terms,
    "usc": fetch_usc_terms,
    "umd": fetch_umd_terms,
    "rutgers": fetch_rutgers_terms,
    "upenn": fetch_upenn_terms,
}


@router.get("/{short_name}")
async def get_term_codes(
    short_name: str,
    admin: Profile = Depends(require_admin),
):
    """
    Fetch available term codes from a college's website.

    This endpoint scrapes the college's class search page to find
    available term codes. Results are not cached - each request
    fetches fresh data from the college website.

    Returns:
    - college: The college short name
    - terms: List of term codes with descriptions (up to 4)
    - status: "success", "error", or "manual"
    - error: Error message if status is "error"
    """
    short_name_lower = short_name.lower()

    # Check if college is supported
    if short_name_lower not in COLLEGE_FETCHERS:
        # Check for Princeton which requires manual lookup
        if short_name_lower == "princeton":
            return {
                "success": True,
                "data": {
                    "college": short_name_lower,
                    "terms": [],
                    "status": "manual",
                    "error": "Princeton has Cloudflare protection - requires manual lookup",
                },
            }

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"College '{short_name}' not found. Supported colleges: {', '.join(COLLEGE_FETCHERS.keys())}",
        )

    # Fetch term codes
    fetch_func = COLLEGE_FETCHERS[short_name_lower]
    status_val, terms, error = await fetch_func()

    return {
        "success": True,
        "data": {
            "college": short_name_lower,
            "terms": terms,
            "status": status_val,
            "error": error,
        },
    }
