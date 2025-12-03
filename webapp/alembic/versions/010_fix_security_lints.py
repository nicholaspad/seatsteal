"""Fix security lints from Supabase

Revision ID: 010
Revises: 009
Create Date: 2025-12-02 00:00:00

This migration fixes security warnings from Supabase linter:

1. Function Search Path Mutable (4 functions):
   - public.handle_new_user
   - public.handle_user_update
   - public.handle_user_delete
   - public.sync_user_to_custom_table

   Fix: Set search_path = '' to prevent search path manipulation attacks.

2. Extension in Public (pg_trgm):
   - Move pg_trgm from public schema to extensions schema
   - This requires dropping and recreating trigram indexes

Manual actions required after migration:
- Enable Leaked Password Protection: Auth > Providers > Email > Enable "Prevent use of leaked passwords"
- Upgrade Postgres Version: Settings > Infrastructure > Upgrade to latest patch version
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ===========================================
    # 1. FIX FUNCTION SEARCH PATH (4 functions)
    # ===========================================
    # These functions were created directly in Supabase (auth triggers).
    # Setting search_path = '' prevents search path manipulation attacks.
    # Using IF EXISTS to gracefully handle cases where functions might not exist.

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'handle_new_user' AND pronamespace = 'public'::regnamespace) THEN
                ALTER FUNCTION public.handle_new_user() SET search_path = '';
            END IF;
        END $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'handle_user_update' AND pronamespace = 'public'::regnamespace) THEN
                ALTER FUNCTION public.handle_user_update() SET search_path = '';
            END IF;
        END $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'handle_user_delete' AND pronamespace = 'public'::regnamespace) THEN
                ALTER FUNCTION public.handle_user_delete() SET search_path = '';
            END IF;
        END $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'sync_user_to_custom_table' AND pronamespace = 'public'::regnamespace) THEN
                ALTER FUNCTION public.sync_user_to_custom_table() SET search_path = '';
            END IF;
        END $$;
        """
    )

    # ===========================================
    # 2. MOVE pg_trgm EXTENSION TO extensions SCHEMA
    # ===========================================
    # Extensions should not be in the public schema for security.
    # We need to:
    # a) Create extensions schema
    # b) Drop existing trigram indexes (they depend on pg_trgm operators)
    # c) Drop pg_trgm from public
    # d) Create pg_trgm in extensions schema
    # e) Add extensions to search_path so operators are accessible
    # f) Recreate the trigram indexes

    # a) Create extensions schema if it doesn't exist
    op.execute("CREATE SCHEMA IF NOT EXISTS extensions")

    # b) Drop existing trigram indexes (they use gin_trgm_ops from pg_trgm)
    op.execute("DROP INDEX IF EXISTS courses_course_code_trgm_idx")
    op.execute("DROP INDEX IF EXISTS courses_title_trgm_idx")

    # c) Drop pg_trgm from public schema
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")

    # d) Create pg_trgm in extensions schema
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm SCHEMA extensions")

    # e) Update database search_path to include extensions schema
    # This ensures the trigram operators are found without schema qualification
    op.execute(
        """
        DO $$
        DECLARE
            current_search_path text;
        BEGIN
            -- Get current search_path
            SELECT setting INTO current_search_path 
            FROM pg_settings WHERE name = 'search_path';
            
            -- Only add extensions if not already in search_path
            IF current_search_path NOT LIKE '%extensions%' THEN
                EXECUTE format('ALTER DATABASE %I SET search_path = %s, extensions', 
                    current_database(), current_search_path);
            END IF;
        END $$;
        """
    )

    # Set search_path for current session too
    op.execute("SET search_path = public, extensions")

    # f) Recreate the trigram indexes
    op.execute(
        "CREATE INDEX courses_course_code_trgm_idx ON courses USING gin (course_code gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX courses_title_trgm_idx ON courses USING gin (title gin_trgm_ops)"
    )


def downgrade() -> None:
    # ===========================================
    # 1. RESET FUNCTION SEARCH PATH (restore mutable)
    # ===========================================
    # Reset to default (role's search_path)

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'handle_new_user' AND pronamespace = 'public'::regnamespace) THEN
                ALTER FUNCTION public.handle_new_user() RESET search_path;
            END IF;
        END $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'handle_user_update' AND pronamespace = 'public'::regnamespace) THEN
                ALTER FUNCTION public.handle_user_update() RESET search_path;
            END IF;
        END $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'handle_user_delete' AND pronamespace = 'public'::regnamespace) THEN
                ALTER FUNCTION public.handle_user_delete() RESET search_path;
            END IF;
        END $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'sync_user_to_custom_table' AND pronamespace = 'public'::regnamespace) THEN
                ALTER FUNCTION public.sync_user_to_custom_table() RESET search_path;
            END IF;
        END $$;
        """
    )

    # ===========================================
    # 2. MOVE pg_trgm BACK TO public SCHEMA
    # ===========================================

    # Drop existing trigram indexes
    op.execute("DROP INDEX IF EXISTS courses_course_code_trgm_idx")
    op.execute("DROP INDEX IF EXISTS courses_title_trgm_idx")

    # Drop pg_trgm from extensions schema
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")

    # Create pg_trgm in public schema (default)
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Recreate the trigram indexes
    op.execute(
        "CREATE INDEX courses_course_code_trgm_idx ON courses USING gin (course_code gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX courses_title_trgm_idx ON courses USING gin (title gin_trgm_ops)"
    )

    # Reset database search_path to PostgreSQL default (removes 'extensions' from path)
    # The default search_path is typically '"$user", public'
    op.execute(
        """
        DO $$
        BEGIN
            EXECUTE format('ALTER DATABASE %I RESET search_path', current_database());
        END $$;
        """
    )

    # Note: We don't remove extensions schema as other things might use it
