#!/usr/bin/env python3
"""
Convert relative imports to absolute imports in the webapp directory.

This script processes all Python files in webapp/ and converts relative imports
(e.g., from .config import settings) to absolute imports (e.g., from config import settings).
"""

import re
from pathlib import Path

WEBAPP_DIR = Path(__file__).parent / "webapp"


def get_module_path(file_path: Path) -> str:
    """Get the module path for a file relative to webapp directory."""
    rel_path = file_path.relative_to(WEBAPP_DIR)
    # Remove .py extension and convert path to module notation
    module_parts = list(rel_path.parent.parts)
    if rel_path.stem != "__init__":
        module_parts.append(rel_path.stem)
    return ".".join(module_parts) if module_parts and module_parts != ["."] else ""


def resolve_relative_import(file_path: Path, import_line: str) -> str:
    """
    Convert a relative import to an absolute import.

    Args:
        file_path: Path to the file containing the import
        import_line: The import line to convert

    Returns:
        The converted import line
    """
    # Get the directory path for this file relative to webapp
    rel_path = file_path.relative_to(WEBAPP_DIR)
    # Directory parts (not including the file itself)
    dir_parts = list(rel_path.parent.parts) if rel_path.parent != Path(".") else []

    # Match relative imports
    # Pattern: from (dots) module import ...
    match = re.match(r'^from (\.*)([\w.]*) import (.+)$', import_line)
    if not match:
        return import_line

    dots, module, imports = match.groups()
    num_dots = len(dots)

    if num_dots == 0:
        # Not a relative import
        return import_line

    # Calculate how many levels to go up
    # One dot means current package, two dots means parent, etc.
    levels_up = num_dots - 1

    # Go up from current directory location
    if levels_up > len(dir_parts):
        print(f"Warning: Import goes up too many levels in {file_path}: {import_line}")
        return import_line

    # Start from the base (after going up)
    if levels_up > 0:
        base_parts = dir_parts[:-levels_up]
    else:
        base_parts = dir_parts

    # Add the module being imported
    if module:
        absolute_module = ".".join(base_parts + [module]) if base_parts else module
    else:
        absolute_module = ".".join(base_parts) if base_parts else ""

    # Construct the new import line
    if absolute_module:
        return f"from {absolute_module} import {imports}"
    else:
        # Importing from the root package
        return f"from {module} import {imports}" if module else import_line


def convert_file(file_path: Path, dry_run=False):
    """Convert relative imports in a single file."""
    try:
        content = file_path.read_text()
        lines = content.split("\n")
        modified = False
        new_lines = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("from ."):
                new_line = line.replace(stripped, resolve_relative_import(file_path, stripped), 1)
                if new_line != line:
                    modified = True
                    if not dry_run:
                        print(f"  {file_path.relative_to(WEBAPP_DIR)}:")
                        print(f"    - {stripped}")
                        print(f"    + {new_line.strip()}")
                new_lines.append(new_line)
            else:
                new_lines.append(line)

        if modified and not dry_run:
            file_path.write_text("\n".join(new_lines))
            return True
        return modified
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Main conversion function."""
    print("Converting relative imports to absolute imports in webapp/\n")

    # Find all Python files (excluding venv, __pycache__, etc.)
    python_files = [
        f for f in WEBAPP_DIR.rglob("*.py")
        if "venv" not in f.parts
        and "__pycache__" not in f.parts
        and ".pytest_cache" not in f.parts
    ]
    files_to_convert = []

    # Filter files with relative imports
    for file_path in python_files:
        try:
            content = file_path.read_text()
            if re.search(r'^from \.', content, re.MULTILINE):
                files_to_convert.append(file_path)
        except Exception as e:
            print(f"Skipping {file_path}: {e}")

    print(f"Found {len(files_to_convert)} files with relative imports\n")

    # Convert each file
    converted_count = 0
    for file_path in files_to_convert:
        if convert_file(file_path):
            converted_count += 1

    print(f"\n✅ Converted {converted_count} files")


if __name__ == "__main__":
    main()
