# Dependency Audit Report
**Generated:** 2025-12-30

## Executive Summary

This audit analyzed dependencies for both the frontend (Node.js/npm) and backend (Python) components of the seatsteal project. Key findings:

- **Frontend:** ✅ No security vulnerabilities detected
- **Backend:** ⚠️ **CRITICAL security vulnerabilities found** requiring immediate attention
- **Outdated Packages:** Multiple packages have significant updates available
- **Bloat Assessment:** Dependencies are generally lean and appropriate

---

## 🚨 Critical Security Vulnerabilities (Backend)

### 1. cryptography (v41.0.7 → v43.0.1+ required)
**Severity:** CRITICAL

**Vulnerabilities:**
- **CVE-2024-26130** (PYSEC-2024-225): NULL pointer dereference in PKCS12 serialization
- **CVE-2023-50782** (GHSA-3ww4-gg4f-jr7f): RSA key exchange weakness allowing message decryption
- **CVE-2024-0727** (GHSA-9v9h-cgj8-h64p): PKCS12 format parsing DoS vulnerability
- **GHSA-h4gh-qq45-vh27**: OpenSSL static linking vulnerability

**Impact:** Remote attackers could decrypt TLS traffic, cause denial of service, or crash the application.

**Recommendation:**
```
pip install cryptography>=43.0.1
```

### 2. setuptools (v68.1.2 → v78.1.1+ required)
**Severity:** HIGH

**Vulnerabilities:**
- **CVE-2025-47273** (PYSEC-2025-49): Path traversal allowing arbitrary file writes
- **CVE-2024-6345** (GHSA-cx63-2mw6-8hw5): Remote code execution via package_index module

**Impact:** Attackers could execute arbitrary code or write files to any location on the filesystem.

**Recommendation:**
```
pip install setuptools>=78.1.1
```

### 3. pip (v24.0 → v25.3+ required)
**Severity:** MEDIUM-HIGH

**Vulnerabilities:**
- **CVE-2025-8869**: Symbolic link traversal in tar extraction (fallback implementation)

**Impact:** Malicious packages could write files outside extraction directory.

**Recommendation:**
```
pip install --upgrade pip>=25.3
```

---

## 📦 Frontend Dependencies (Node.js)

### Security Status
✅ **No vulnerabilities detected** (npm audit clean)

### Major Version Updates Available

#### 1. Capacitor Ecosystem (v7 → v8)
**All Capacitor packages can be upgraded to v8.0.0:**
- `@capacitor/app`: 7.1.0 → 8.0.0
- `@capacitor/core`: 7.4.3 → 8.0.0
- `@capacitor/haptics`: 7.0.2 → 8.0.0
- `@capacitor/ios`: 7.4.4 → 8.0.0
- `@capacitor/keyboard`: 7.0.3 → 8.0.0
- `@capacitor/status-bar`: 7.0.3 → 8.0.0
- `@capacitor/cli`: 7.4.3 → 8.0.0 (dev)

**Priority:** Medium
**Recommendation:** Upgrade together as a single update. Review [Capacitor 8 migration guide](https://capacitorjs.com/docs/updating/8-0) for breaking changes.

#### 2. React Router (v5 → v7)
- `react-router`: 5.3.4 → 7.11.0
- `react-router-dom`: 5.3.4 → 7.11.0

**Priority:** Medium
**Recommendation:** This is a **major version jump** (v5 → v7). Review migration guides carefully:
- [v5 to v6 migration](https://reactrouter.com/upgrading/v5)
- [v6 to v7 migration](https://reactrouter.com/upgrading/v6)

**Breaking changes expected.** Consider deferring unless new features are needed.

#### 3. Tailwind CSS (v3 → v4)
- `tailwindcss`: 3.4.19 → 4.1.18
- `tailwind-merge`: 2.6.0 → 3.4.0

**Priority:** Low-Medium
**Recommendation:** Tailwind CSS v4 is a major rewrite with significant breaking changes. Review the [v4 upgrade guide](https://tailwindcss.com/docs/upgrade-guide).

**Effort required:** High. Consider deferring unless specific v4 features are needed.

#### 4. xterm.js (v5 → v6)
- `@xterm/xterm`: 5.5.0 → 6.0.0
- `@xterm/addon-fit`: 0.10.0 → 0.11.0
- `@xterm/addon-web-links`: 0.11.0 → 0.12.0

**Priority:** Low
**Recommendation:** Review changelog for breaking changes. If terminal functionality is working well, consider deferring.

#### 5. Minor Updates (Safe to upgrade)
- `lucide-react`: 0.525.0 → 0.562.0
- `typescript`: 5.8.3 → 5.9.3

**Priority:** Low
**Recommendation:** Safe to upgrade. These are minor/patch updates.

---

## 🐍 Backend Dependencies (Python)

### Outdated Packages in requirements.txt

The following packages in `requirements.txt` and `requirements-full.txt` are outdated and should be reviewed:

#### Web Framework
| Package | Current | Recommended | Priority |
|---------|---------|-------------|----------|
| `fastapi` | 0.109.0 | 0.115.x+ | High |
| `uvicorn` | 0.27.0 | 0.34.x+ | Medium |
| `python-multipart` | 0.0.18 | 0.0.20+ | Low |

**Notes:**
- FastAPI 0.115+ includes performance improvements and bug fixes
- Uvicorn 0.34+ has HTTP/2 improvements

#### Database
| Package | Current | Recommended | Priority |
|---------|---------|-------------|----------|
| `sqlalchemy` | 2.0.25 | 2.0.37+ | Medium |
| `alembic` | 1.13.1 | 1.14.x+ | Low |
| `asyncpg` | 0.29.0 | 0.30.x+ | Low |
| `psycopg2-binary` | 2.9.9 | 2.9.10+ | Low |

#### Authentication & Security
| Package | Current | Recommended | Priority |
|---------|---------|-------------|----------|
| `pyjwt` | 2.8.0 | 2.10.1+ | Medium |
| `python-jose` | 3.3.0 | 3.3.0 | ✅ Current |
| `supabase` | >=2.9.0 | Latest | Medium |

**Notes:**
- PyJWT 2.10+ includes security improvements and bug fixes

#### Utilities & Core Libraries
| Package | Current | Recommended | Priority |
|---------|---------|-------------|----------|
| `pydantic` | 2.5.3 | 2.10.x+ | High |
| `pydantic-settings` | 2.1.0 | 2.7.x+ | Medium |
| `python-dotenv` | 1.0.1 | 1.0.2+ | Low |
| `email-validator` | 2.3.0 | 2.4.x+ | Low |
| `loguru` | 0.7.2 | 0.7.3+ | Low |
| `redis` | 5.0.1 | 5.2.x+ | Medium |

**Notes:**
- Pydantic 2.10+ has significant performance improvements and new features

#### External Services
| Package | Current | Recommended | Priority |
|---------|---------|-------------|----------|
| `stripe` | 13.0.0 | 14.x+ | Medium |
| `boto3` | 1.34.34 | 1.36.x+ | Medium |
| `twilio` | 9.3.0 | 9.6.x+ | Low |

#### Scraping (requirements-full.txt)
| Package | Current | Recommended | Priority |
|---------|---------|-------------|----------|
| `beautifulsoup4` | 4.12.3 | 4.13.x+ | Low |
| `requests` | 2.32.4 | 2.32.5+ | Low |
| `lxml` | 5.1.0 | 5.4.x+ | Low |

#### Development Tools (requirements-full.txt)
| Package | Current | Recommended | Priority |
|---------|---------|-------------|----------|
| `pytest` | 7.4.4 | 8.3.x+ | Medium |
| `pytest-asyncio` | 0.23.3 | 0.25.x+ | Low |
| `pytest-cov` | 7.0.0 | 7.0.1+ | Low |
| `httpx` | 0.27.2 | 0.29.x+ | Low |
| `black` | 24.3.0 | 25.x+ | Low |
| `mypy` | 1.8.0 | 1.15.x+ | Low |

---

## 🔍 Dependency Bloat Analysis

### Frontend
**Assessment:** ✅ **Lean and appropriate**

The frontend dependencies are well-justified:
- Core framework: React 19, Ionic 8
- UI components: Radix UI (accessible, unstyled components)
- Styling: Tailwind CSS (utility-first, tree-shakeable)
- Terminal: xterm.js (essential for terminal feature)
- Charts: Recharts (for analytics)
- Dev tools: Appropriate testing and linting setup

**No bloat detected.** All dependencies serve clear purposes.

### Backend
**Assessment:** ✅ **Well-organized with clear separation**

The backend has good dependency management:
- `requirements.txt`: Production-optimized (excludes scrapers, dev tools)
- `requirements-full.txt`: Complete set for local development

**Observations:**
- Smart separation reduces Vercel deployment size
- No unnecessary dependencies detected
- All packages serve clear purposes

**Minor consideration:**
- `python-jose` and `pyjwt` provide overlapping functionality. Consider standardizing on one if possible (both are currently used).

---

## 📋 Recommended Actions

### Immediate (Do Now)
1. ⚠️ **Update cryptography to v43.0.1+** (CRITICAL security fix)
   ```bash
   cd webapp
   pip install 'cryptography>=43.0.1'
   ```

2. ⚠️ **Update setuptools to v78.1.1+** (HIGH security fix)
   ```bash
   pip install 'setuptools>=78.1.1'
   ```

3. ⚠️ **Update pip to v25.3+**
   ```bash
   pip install --upgrade 'pip>=25.3'
   ```

4. **Update requirements.txt with fixed versions**
   - Update pinned versions for security packages
   - Test thoroughly after updates

### High Priority (This Sprint)
1. **Update FastAPI** (0.109.0 → 0.115.x)
   - Performance improvements and bug fixes
   - Review breaking changes in release notes

2. **Update Pydantic** (2.5.3 → 2.10.x)
   - Significant performance improvements
   - Review migration guide for v2.10

3. **Update PyJWT** (2.8.0 → 2.10.x)
   - Security improvements

### Medium Priority (Next Sprint)
1. **Capacitor v8 migration**
   - Plan for coordinated upgrade of all Capacitor packages
   - Review breaking changes
   - Test on iOS devices

2. **Update remaining Python packages**
   - SQLAlchemy, Uvicorn, Stripe, Boto3, Redis
   - Group related updates together

### Low Priority (Future)
1. **React Router v7 migration**
   - Research effort required (v5 → v7 is significant)
   - Consider ROI vs. effort

2. **Tailwind CSS v4 migration**
   - Major rewrite with breaking changes
   - Defer unless specific features needed

3. **Minor package updates**
   - lucide-react, typescript, and other minor versions

---

## 🛡️ Security Best Practices

### Recommendations for Ongoing Maintenance

1. **Automated Dependency Scanning**
   - Set up GitHub Dependabot for automated security alerts
   - Run `npm audit` and `pip-audit` in CI/CD pipeline

2. **Regular Update Cadence**
   - Monthly: Review and apply security updates
   - Quarterly: Review and plan major version upgrades
   - Always: Test thoroughly after updates

3. **Pin Exact Versions**
   - ✅ Already doing this in requirements.txt (good!)
   - Consider using `package-lock.json` (already present for frontend)

4. **Separate Production Dependencies**
   - ✅ Already doing this (requirements.txt vs requirements-full.txt)
   - Consider similar approach for frontend if dev dependencies grow

---

## 📊 Summary Statistics

### Frontend (npm)
- **Total dependencies:** 58 direct dependencies
- **Security vulnerabilities:** 0 🎉
- **Major updates available:** 15 packages
- **Minor updates available:** 10+ packages

### Backend (Python)
- **Total dependencies (requirements.txt):** 20 packages
- **Total dependencies (requirements-full.txt):** 30 packages
- **Critical vulnerabilities:** 3 packages 🚨
- **Security fixes needed:** Immediate action required
- **Outdated packages:** 20+ packages with updates available

---

## 🔗 Useful Resources

- [npm audit documentation](https://docs.npmjs.com/cli/v10/commands/npm-audit)
- [pip-audit GitHub](https://github.com/pypa/pip-audit)
- [CVE Database](https://cve.mitre.org/)
- [Snyk Vulnerability Database](https://snyk.io/vuln/)
- [GitHub Advisory Database](https://github.com/advisories)
