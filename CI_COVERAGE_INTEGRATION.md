# CI Coverage Integration

## Summary

This document describes the implementation of automated PR coverage comments for both frontend and backend CI workflows.

## Changes Made

### 1. Backend CI (`/.github/workflows/backend-ci.yml`)

#### Added Permissions
```yaml
permissions:
  contents: read
  pull-requests: write
```
Required for the workflow to post comments on pull requests.

#### Updated Coverage Reporting
- Modified `pytest.ini` to generate JSON coverage reports (`--cov-report=json`)
- Added `coverage.json` to uploaded artifacts
- Enhanced coverage summary in workflow summary

#### PR Comment Feature
- Posts a formatted coverage report comment on every PR
- Includes:
  - Overall coverage percentage
  - Total statements covered/missing
  - Table of 10 files with lowest coverage
  - Link to full coverage artifacts
- Updates existing comment instead of creating duplicates (searches for comment with "🐍 Backend Coverage Report")

### 2. Frontend CI (`/.github/workflows/frontend-ci.yml`)

#### Added Permissions
```yaml
permissions:
  contents: read
  pull-requests: write
```

#### PR Comment Feature
- Posts a formatted coverage report comment on every PR
- Includes:
  - Overall coverage percentage
  - Detailed metrics table (Lines, Statements, Functions, Branches)
  - Table of 10 files with lowest coverage with per-metric breakdown
  - Link to full coverage artifacts
- Updates existing comment instead of creating duplicates (searches for comment with "⚛️ Frontend Coverage Report")

### 3. Backend Configuration (`/webapp/pytest.ini`)

Added JSON output format for coverage reports:
```ini
--cov-report=json
```

## How It Works

### Backend Flow
1. Tests run in Docker container with `pytest --cov`
2. Coverage data saved to `.coverage`, `htmlcov/`, and `coverage.json`
3. Artifacts uploaded for later review
4. Coverage summary added to workflow summary (visible in Actions UI)
5. **If on PR**: GitHub Actions bot posts/updates coverage comment using `actions/github-script@v7`

### Frontend Flow
1. Tests run with `vitest --coverage`
2. Coverage data saved to `coverage/` directory with `coverage-summary.json`
3. Artifacts uploaded for later review
4. Coverage summary added to workflow summary (visible in Actions UI)
5. **If on PR**: GitHub Actions bot posts/updates coverage comment using `actions/github-script@v7`

## Example PR Comments

### Backend Coverage Comment
```
## 🐍 Backend Coverage Report

**Overall Coverage: 85.32%**

- **Statements:** 1234/1447
- **Missing Lines:** 213

### Files with Lowest Coverage
| File | Statements | Missing | Coverage |
|------|------------|---------|----------|
| `auth.py` | 45/67 | 22 | 67.2% |
| `cache.py` | 89/112 | 23 | 79.5% |
...

📊 Full coverage report available in workflow artifacts
```

### Frontend Coverage Comment
```
## ⚛️ Frontend Coverage Report

**Overall Coverage: 78.45%**

| Metric | Covered | Total | Percentage |
|--------|---------|-------|------------|
| Lines | 1567 | 1998 | 78.45% |
| Statements | 1589 | 2034 | 78.12% |
| Functions | 234 | 312 | 75.00% |
| Branches | 156 | 234 | 66.67% |

### Files with Lowest Coverage
| File | Lines | Statements | Functions | Branches | Coverage |
|------|-------|------------|-----------|----------|----------|
| `Auth.tsx` | 65.3% | 64.2% | 60.0% | 55.5% | 61.3% |
| `Cache.ts` | 71.2% | 70.8% | 68.4% | 65.2% | 68.9% |
...

📊 Full coverage report available in workflow artifacts
```

## Benefits

1. **Visibility**: Coverage metrics are immediately visible in PR comments
2. **Tracking**: Can track coverage changes across commits (comment updates on each push)
3. **Focus**: Highlights files with lowest coverage that need attention
4. **Clean**: Updates existing comment rather than spamming multiple comments
5. **Accessible**: Full HTML coverage reports still available as artifacts for detailed analysis

## Technical Details

- Uses `actions/github-script@v7` for GitHub API interactions
- Comments only added on `pull_request` events, not on `push` to `main`
- Uses `if: always()` to ensure comments are posted even if tests fail
- Identifies bot comments by content marker (emoji + title) to update correctly
- Filters test files from coverage tables to focus on source files

## Testing

To test these changes:
1. Create a PR with code changes in `webapp/**` or `seatsteal/**`
2. Wait for CI to complete
3. Check PR comments for coverage reports
4. Push another commit to verify comment updates (doesn't create duplicates)
