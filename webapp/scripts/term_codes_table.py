#!/usr/bin/env python3
"""
Fetch and display current term codes for all colleges.

This script fetches the actual term codes from each college's API/website
and displays the 4 most recent term codes in a formatted table.

Usage:
    python term_codes_table.py
"""

import re
import json
import subprocess
import base64
from typing import List, Tuple


def fetch_brown_terms() -> List[Tuple[str, str]]:
    """Fetch term codes from Brown University."""
    try:
        result = subprocess.run(
            ["curl", "-s", "https://cab.brown.edu/"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        html = result.stdout

        # Extract option tags with term codes
        pattern = r'<option[^>]*value="(\d+)"[^>]*>([^<]+)</option>'
        matches = re.findall(pattern, html)

        terms = []
        for code, name in matches:
            name = name.strip()
            if "Any Term" not in name and code.isdigit():
                terms.append((code, name))

        return terms[:4]
    except Exception as e:
        return [("ERROR", str(e))]


def fetch_bu_terms() -> List[Tuple[str, str]]:
    """Fetch term codes from Boston University."""
    try:
        url = "https://public.mybustudent.bu.edu/psc/BUPRD/EMPLOYEE/SA/s/WEBLIB_HCX_CM.H_CLASS_SEARCH.FieldFormula.IScript_Main?institution=BU001"
        result = subprocess.run(
            ["curl", "-s", "-H", "Cookie: public-PORTAL-PSJSESSIONID=1;", url],
            capture_output=True,
            text=True,
            timeout=10,
        )
        html = result.stdout

        # Extract base64-encoded JSON from atob(`...`)
        pattern = r"atob\(`([^`]+)`\)"
        match = re.search(pattern, html)

        if not match:
            return [("ERROR", "Could not find base64 data")]

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
            terms.append((str(code), desc))

        return terms if terms else [("ERROR", "No terms found")]
    except Exception as e:
        return [("ERROR", str(e))]


def fetch_cornell_terms() -> List[Tuple[str, str]]:
    """Fetch term codes from Cornell University."""
    try:
        result = subprocess.run(
            ["curl", "-s", "https://classes.cornell.edu/browse/roster/SP26"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        html = result.stdout

        # Extract roster links with term codes
        pattern = r'href="/browse/roster/([A-Z]{2}\d{2})"[^>]*>([^<]+)</a>'
        matches = re.findall(pattern, html)

        terms = []
        for code, name in matches:
            name = name.strip()
            if name and "clear" not in name.lower() and "Roster" not in name:
                terms.append((code, name))

        # Remove duplicates while preserving order
        seen = set()
        unique_terms = []
        for term in terms:
            if term[0] not in seen:
                seen.add(term[0])
                unique_terms.append(term)

        return unique_terms[:4]
    except Exception as e:
        return [("ERROR", str(e))]


def fetch_neu_terms() -> List[Tuple[str, str]]:
    """Fetch term codes from Northeastern University."""
    try:
        url = "https://nubanner.neu.edu/StudentRegistrationSsb/ssb/classSearch/getTerms?offset=1&max=20&searchTerm="
        result = subprocess.run(
            ["curl", "-s", url], capture_output=True, text=True, timeout=10
        )

        data = json.loads(result.stdout)
        terms = []
        for term in data[:4]:
            code = term.get("code", "")
            desc = term.get("description", "")
            terms.append((str(code), desc))

        return terms
    except Exception as e:
        return [("ERROR", str(e))]


def fetch_princeton_terms() -> List[Tuple[str, str]]:
    """Princeton has Cloudflare protection - cannot fetch automatically."""
    return [("MANUAL", "Has Cloudflare protection - see TERM_CODES.md")]


def fetch_usc_terms() -> List[Tuple[str, str]]:
    """Fetch term codes from USC."""
    try:
        result = subprocess.run(
            ["curl", "-s", "https://classes.usc.edu/api/Terms/All"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        data = json.loads(result.stdout)
        terms = []
        for term in data[:4]:
            code = term.get("termCode", "")
            season = term.get("season", "")
            year = term.get("year", "")
            status = term.get("status", "")
            name = f"{season} {year} ({status})"
            terms.append((str(code), name))

        return terms
    except Exception as e:
        return [("ERROR", str(e))]


def fetch_umd_terms() -> List[Tuple[str, str]]:
    """Fetch term codes from University of Maryland."""
    try:
        result = subprocess.run(
            ["curl", "-s", "https://app.testudo.umd.edu/soc/"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        html = result.stdout

        # Find the term dropdown section
        pattern = r'<option value="(\d+)"[^>]*>([^<]+)</option>'
        matches = re.findall(pattern, html)

        terms = []
        for code, name in matches:
            name = name.strip()
            if code.isdigit() and len(code) == 6:  # UMD uses 6-digit codes
                terms.append((code, name))

        return terms[:4]
    except Exception as e:
        return [("ERROR", str(e))]


def fetch_rutgers_terms() -> List[Tuple[str, str]]:
    """Fetch term codes from Rutgers University."""
    try:
        result = subprocess.run(
            ["curl", "-s", "https://classes.rutgers.edu/soc/"],
            capture_output=True,
            timeout=10,
        )
        # Handle potential encoding issues
        html = result.stdout.decode("utf-8", errors="ignore")

        # Extract currentTermDate from embedded JSON
        pattern = r'"currentTermDate":\s*\{([^}]+)\}'
        match = re.search(pattern, html)

        if not match:
            return [("ERROR", "Could not find currentTermDate")]

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
            terms.append((code, name))

            # Move to previous term
            if term == 0:
                year -= 1
            term = term_order.get(term, 9)

        return terms
    except Exception as e:
        return [("ERROR", str(e))]


def fetch_upenn_terms() -> List[Tuple[str, str]]:
    """Fetch term codes from University of Pennsylvania."""
    try:
        result = subprocess.run(
            ["curl", "-s", "https://courses.upenn.edu/"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        html = result.stdout

        # Extract option tags with term codes
        pattern = r'<option[^>]*value="(\d+)"[^>]*>([^<]+)</option>'
        matches = re.findall(pattern, html)

        terms = []
        for code, name in matches:
            name = name.strip()
            # Filter out non-term options (instruction methods, etc.)
            if code.isdigit() and len(code) == 6:
                terms.append((code, name))

        return terms[:4]
    except Exception as e:
        return [("ERROR", str(e))]


def fetch_uci_terms() -> List[Tuple[str, str]]:
    """
    Generate term codes for UC Irvine.

    UCI uses a quarter system with codes in format: YYYY:Quarter
    Quarters: Fall, Winter, Spring, Summer1, Summer10wk, Summer2
    """
    try:
        from datetime import datetime

        # Get current date to determine current quarter
        now = datetime.now()
        year = now.year
        month = now.month

        # Determine current quarter based on month
        # Fall: Sep-Dec, Winter: Jan-Mar, Spring: Apr-Jun, Summer: Jul-Aug
        if month >= 9:
            current_quarter = "Fall"
        elif month >= 6:
            current_quarter = "Summer2"
        elif month >= 4:
            current_quarter = "Spring"
        elif month >= 1:
            current_quarter = "Winter"
        else:
            current_quarter = "Fall"
            year -= 1

        # Generate next 4 quarters starting from current
        quarter_order = ["Winter", "Spring", "Summer1", "Summer2", "Fall"]
        terms = []

        quarter_idx = quarter_order.index(current_quarter)
        current_year = year

        for _ in range(4):
            quarter = quarter_order[quarter_idx]
            code = f"{current_year}:{quarter}"
            description = f"{quarter} {current_year}"
            terms.append((code, description))

            # Move to next quarter
            quarter_idx = (quarter_idx + 1) % len(quarter_order)
            if quarter_idx == 0:  # Wrapped to Winter, increment year
                current_year += 1

        return terms
    except Exception as e:
        return [("ERROR", str(e))]


def fetch_uf_terms() -> List[Tuple[str, str]]:
    """Fetch term codes from University of Florida."""
    try:
        result = subprocess.run(
            ["curl", "-s", "https://one.uf.edu/apix/soc/terms"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        data = json.loads(result.stdout)
        terms = []
        for term in data[:4]:
            code = str(term.get("term", ""))
            name = term.get("termName", "")
            terms.append((code, name))

        return terms if terms else [("ERROR", "No terms found")]
    except Exception as e:
        return [("ERROR", str(e))]


def display_term_codes_table():
    """Fetch and display a formatted table of term codes for all colleges."""

    print("Fetching Current Term Codes...")
    print("=" * 100)
    print()

    # Fetch term codes from all colleges
    colleges = {
        # "brown": fetch_brown_terms, // Disabled for now due to AWS blocking requests
        "bu": fetch_bu_terms,
        "cornell": fetch_cornell_terms,
        "neu": fetch_neu_terms,
        # "princeton": fetch_princeton_terms,
        "usc": fetch_usc_terms,
        "umd": fetch_umd_terms,
        "rutgers": fetch_rutgers_terms,
        "upenn": fetch_upenn_terms,
        "uci": fetch_uci_terms,
        "uf": fetch_uf_terms,
    }

    term_data = {}
    for college, fetch_func in colleges.items():
        print(f"  Fetching {college}...", end=" ", flush=True)
        terms = fetch_func()
        term_data[college] = terms
        if terms and terms[0][0] not in ("ERROR", "MANUAL"):
            print(f"OK ({len(terms)} terms)")
        elif terms and terms[0][0] == "MANUAL":
            print("MANUAL")
        else:
            print(f"FAILED: {terms[0][1] if terms else 'Unknown error'}")

    print()
    print("Recent Term Codes by College")
    print("=" * 100)
    print()

    # Column widths
    college_width = 12
    code_width = 20

    # Print header
    header = f"{'College':<{college_width}}"
    for i in range(4):
        header += f"  {'Term ' + str(i + 1):<{code_width}}"
    print(header)
    print("-" * 100)

    # Print each college's term codes
    for college, terms in term_data.items():
        row = f"{college:<{college_width}}"

        if terms and terms[0][0] in ("ERROR", "MANUAL"):
            # Show error/manual message spanning all columns
            msg = terms[0][1][:75] + "..." if len(terms[0][1]) > 75 else terms[0][1]
            row += f"  {msg}"
        else:
            # Pad with empty entries if fewer than 4 terms
            padded_terms = terms + [("", "")] * (4 - len(terms))
            for code, name in padded_terms[:4]:
                if code:
                    cell = f"{code} ({name})"
                    if len(cell) > code_width:
                        cell = cell[: code_width - 3] + "..."
                else:
                    cell = ""
                row += f"  {cell:<{code_width}}"
        print(row)

    print()
    print("Notes:")
    print("  - Term codes are listed from most recent (Term 1) to oldest (Term 4)")
    print("  - MANUAL: Requires browser inspection due to JavaScript/Cloudflare")
    print("  - Use these codes when updating the colleges table in the database")
    print("  - Refer to webapp/TERM_CODES.md for detailed format explanations")
    print()


def main():
    display_term_codes_table()


if __name__ == "__main__":
    main()
