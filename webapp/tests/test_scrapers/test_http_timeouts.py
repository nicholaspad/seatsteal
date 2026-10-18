"""Guard: every scraper HTTP client must set a timeout."""

import ast
from pathlib import Path

SCRAPER_ROOT = Path(__file__).resolve().parents[2] / "scraper"


def _async_client_calls_without_timeout(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(), filename=str(path))
    missing: list[int] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_async_client = (
            isinstance(func, ast.Attribute)
            and func.attr == "AsyncClient"
            and isinstance(func.value, ast.Name)
            and func.value.id == "httpx"
        )
        if not is_async_client:
            continue
        has_timeout = any(kw.arg == "timeout" for kw in node.keywords)
        if not has_timeout:
            missing.append(node.lineno)
    return missing


def test_all_httpx_async_clients_set_timeout():
    missing = []
    for path in [
        SCRAPER_ROOT / "base.py",
        *sorted((SCRAPER_ROOT / "scrapers").glob("*.py")),
    ]:
        for lineno in _async_client_calls_without_timeout(path):
            missing.append(f"{path.relative_to(SCRAPER_ROOT)}:{lineno}")
    assert missing == []
