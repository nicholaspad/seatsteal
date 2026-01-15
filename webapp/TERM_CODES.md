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

## Quick Reference Tool

Run the term codes table script to fetch current term codes for all colleges:

```bash
cd webapp
source venv/bin/activate
python scripts/term_codes_table.py
```
