#!/usr/bin/env python3
"""
Automated component migration script from Next.js to React+Ionic.
Handles transformation of imports and removes Next.js-specific code.
"""

import os
import re
from pathlib import Path

# Source and destination paths
SOURCE_BASE = "/Users/nicholaspad/Sandbox/course-watcher/course-watcher/src/components"
DEST_BASE = "/Users/nicholaspad/Sandbox/seatsteal/seatsteal/src/components"

# Transformation rules
TRANSFORMATIONS = [
    # Remove Next.js directives
    (r'"use client";\n\n', ''),
    (r'"use server";\n\n', ''),

    # Replace Next.js imports
    (r'import\s+Link\s+from\s+"next/link"', 'import { Link } from "react-router-dom"'),
    (r'import\s+\{([^}]+)\}\s+from\s+"next/navigation"', r'import { useHistory, useLocation } from "react-router-dom"'),
    (r'import\s+Image\s+from\s+"next/image"', ''),
    (r'import\s+dynamic\s+from\s+"next/dynamic"', ''),

    # Replace hooks
    (r'useRouter\(\)', 'useHistory()'),
    (r'usePathname\(\)', 'useLocation().pathname'),
    (r'router\.push\(', 'history.push('),
    (r'router\.refresh\(\)', 'window.location.reload()'),

    # Replace Link component props
    (r'<Link\s+href=', '<Link to='),
    (r'Link\s+href=', 'Link to='),

    # Fix provider imports (capitalize component names)
    (r'@/components/providers/session-provider', '@/components/providers/SessionProvider'),
    (r'@/components/providers/theme-provider', '@/components/providers/ThemeProvider'),

    # Remove Image component usage (replace with img)
    (r'<Image\s+', '<img '),
    (r'</Image>', '</img>'),

    # Remove &apos; HTML entities (use straight quotes)
    (r'&apos;', "'"),
]

def transform_content(content):
    """Apply all transformations to file content."""
    for pattern, replacement in TRANSFORMATIONS:
        content = re.sub(pattern, replacement, content)
    return content

def migrate_component(source_path, dest_path):
    """Migrate a single component file."""
    # Read source file
    with open(source_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Apply transformations
    content = transform_content(content)

    # Create destination directory if needed
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # Write transformed content
    with open(dest_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Migrated: {source_path.name} -> {dest_path}")

def migrate_directory(source_dir, dest_dir, recursive=True):
    """Migrate all components in a directory."""
    source_path = Path(source_dir)
    dest_path = Path(dest_dir)

    if not source_path.exists():
        print(f"Source directory does not exist: {source_dir}")
        return

    # Get all .tsx and .ts files
    pattern = "**/*.tsx" if recursive else "*.tsx"
    tsx_files = list(source_path.glob(pattern))
    pattern = "**/*.ts" if recursive else "*.ts"
    ts_files = list(source_path.glob(pattern))

    all_files = tsx_files + ts_files

    for source_file in all_files:
        # Calculate relative path
        rel_path = source_file.relative_to(source_path)
        dest_file = dest_path / rel_path

        # Skip if already exists
        if dest_file.exists():
            print(f"Skipped (exists): {rel_path}")
            continue

        migrate_component(source_file, dest_file)

# Component directories to migrate
DIRECTORIES_TO_MIGRATE = [
    ("course", "course"),
    ("class", "class"),
    ("home", "home"),
    ("admin", "admin"),
]

if __name__ == "__main__":
    print("Starting component migration...\n")

    for source_dir, dest_dir in DIRECTORIES_TO_MIGRATE:
        print(f"\nMigrating {source_dir} components...")
        source = os.path.join(SOURCE_BASE, source_dir)
        dest = os.path.join(DEST_BASE, dest_dir)
        migrate_directory(source, dest, recursive=False)

    print("\n\nMigration complete!")
