"""Fix RLS policy performance issues

Revision ID: 007
Revises: 006
Create Date: 2025-12-02 00:00:00

This migration fixes Supabase RLS policy performance issues:
1. Wraps auth.uid() and auth.role() calls in (select ...) to prevent per-row re-evaluation
2. Consolidates multiple permissive policies for the same role/action into single policies

See: https://supabase.com/docs/guides/database/postgres/row-level-security#call-functions-with-select
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ===========================================
    # PROFILES TABLE - Consolidate and fix policies
    # ===========================================

    # Drop existing policies
    op.execute('DROP POLICY IF EXISTS "Users can view own data" ON profiles')
    op.execute('DROP POLICY IF EXISTS "Users can view own profile" ON profiles')
    op.execute('DROP POLICY IF EXISTS "Users can update own data" ON profiles')
    op.execute('DROP POLICY IF EXISTS "Users can update own profile" ON profiles')
    op.execute('DROP POLICY IF EXISTS "Authenticated users can insert" ON profiles')
    op.execute('DROP POLICY IF EXISTS "Admins can view all users" ON profiles')
    op.execute('DROP POLICY IF EXISTS "Service role full access" ON profiles')

    # Create consolidated policies with (select auth.uid()) pattern
    # SELECT: Users can view their own profile OR admins can view all
    op.execute(
        """
        CREATE POLICY "Users can view own profile" ON profiles
        FOR SELECT USING (
            (select auth.uid()) = id 
            OR EXISTS (
                SELECT 1 FROM profiles 
                WHERE id = (select auth.uid()) AND role = 'admin'
            )
        )
    """
    )

    # INSERT: Authenticated users can insert their own profile
    op.execute(
        """
        CREATE POLICY "Users can insert own profile" ON profiles
        FOR INSERT WITH CHECK (
            (select auth.uid()) = id
        )
    """
    )

    # UPDATE: Users can update their own profile
    op.execute(
        """
        CREATE POLICY "Users can update own profile" ON profiles
        FOR UPDATE USING (
            (select auth.uid()) = id
        )
    """
    )

    # Service role bypass (for backend operations)
    op.execute(
        """
        CREATE POLICY "Service role full access" ON profiles
        FOR ALL USING (
            (select auth.role()) = 'service_role'
        )
    """
    )

    # ===========================================
    # SUBSCRIPTIONS TABLE - Consolidate and fix policies
    # ===========================================

    # Drop existing policies
    op.execute(
        'DROP POLICY IF EXISTS "Users can view own subscriptions" ON subscriptions'
    )
    op.execute(
        'DROP POLICY IF EXISTS "Users can create own subscriptions" ON subscriptions'
    )
    op.execute(
        'DROP POLICY IF EXISTS "Users can update own subscriptions" ON subscriptions'
    )
    op.execute(
        'DROP POLICY IF EXISTS "Users can delete own subscriptions" ON subscriptions'
    )
    op.execute(
        'DROP POLICY IF EXISTS "Admins can view all subscriptions" ON subscriptions'
    )

    # Create consolidated policies with (select auth.uid()) pattern
    # SELECT: Users can view their own subscriptions OR admins can view all
    op.execute(
        """
        CREATE POLICY "Users can view subscriptions" ON subscriptions
        FOR SELECT USING (
            (select auth.uid()) = user_id
            OR EXISTS (
                SELECT 1 FROM profiles 
                WHERE id = (select auth.uid()) AND role = 'admin'
            )
        )
    """
    )

    # INSERT: Users can create their own subscriptions
    op.execute(
        """
        CREATE POLICY "Users can create own subscriptions" ON subscriptions
        FOR INSERT WITH CHECK (
            (select auth.uid()) = user_id
        )
    """
    )

    # UPDATE: Users can update their own subscriptions
    op.execute(
        """
        CREATE POLICY "Users can update own subscriptions" ON subscriptions
        FOR UPDATE USING (
            (select auth.uid()) = user_id
        )
    """
    )

    # DELETE: Users can delete their own subscriptions
    op.execute(
        """
        CREATE POLICY "Users can delete own subscriptions" ON subscriptions
        FOR DELETE USING (
            (select auth.uid()) = user_id
        )
    """
    )

    # ===========================================
    # COLLEGES TABLE - Fix policy
    # ===========================================

    op.execute(
        'DROP POLICY IF EXISTS "Authenticated users can view colleges" ON colleges'
    )

    op.execute(
        """
        CREATE POLICY "Authenticated users can view colleges" ON colleges
        FOR SELECT USING (
            (select auth.role()) = 'authenticated'
            OR (select auth.role()) = 'service_role'
        )
    """
    )

    # ===========================================
    # COURSES TABLE - Fix policy
    # ===========================================

    op.execute(
        'DROP POLICY IF EXISTS "Authenticated users can view courses" ON courses'
    )

    op.execute(
        """
        CREATE POLICY "Authenticated users can view courses" ON courses
        FOR SELECT USING (
            (select auth.role()) = 'authenticated'
            OR (select auth.role()) = 'service_role'
        )
    """
    )

    # ===========================================
    # CLASSES TABLE - Fix policy
    # ===========================================

    op.execute(
        'DROP POLICY IF EXISTS "Authenticated users can view classes" ON classes'
    )

    op.execute(
        """
        CREATE POLICY "Authenticated users can view classes" ON classes
        FOR SELECT USING (
            (select auth.role()) = 'authenticated'
            OR (select auth.role()) = 'service_role'
        )
    """
    )

    # ===========================================
    # ENROLLMENTS TABLE - Fix policy
    # ===========================================

    op.execute(
        'DROP POLICY IF EXISTS "Authenticated users can view enrollments" ON enrollments'
    )

    op.execute(
        """
        CREATE POLICY "Authenticated users can view enrollments" ON enrollments
        FOR SELECT USING (
            (select auth.role()) = 'authenticated'
            OR (select auth.role()) = 'service_role'
        )
    """
    )

    # ===========================================
    # NOTIFICATION_LOGS TABLE - Consolidate and fix policies
    # ===========================================

    op.execute(
        'DROP POLICY IF EXISTS "Admins can view notification logs" ON notification_logs'
    )
    op.execute(
        'DROP POLICY IF EXISTS "Service role can manage all data" ON notification_logs'
    )

    # Consolidated policy: Admins can view, service role can manage all
    op.execute(
        """
        CREATE POLICY "Admins and service role access" ON notification_logs
        FOR ALL USING (
            (select auth.role()) = 'service_role'
            OR EXISTS (
                SELECT 1 FROM profiles 
                WHERE id = (select auth.uid()) AND role = 'admin'
            )
        )
    """
    )

    # ===========================================
    # SCRAPERS TABLE - Fix policy
    # ===========================================

    op.execute(
        'DROP POLICY IF EXISTS "Only nicholaspad@gmail.com can read scrapers" ON scrapers'
    )

    op.execute(
        """
        CREATE POLICY "Admin email can read scrapers" ON scrapers
        FOR SELECT USING (
            EXISTS (
                SELECT 1 FROM profiles 
                WHERE id = (select auth.uid()) AND email = 'nicholaspad@gmail.com'
            )
            OR (select auth.role()) = 'service_role'
        )
    """
    )

    # ===========================================
    # SCRAPER_LOGS TABLE - Fix policy
    # ===========================================

    op.execute(
        'DROP POLICY IF EXISTS "Only nicholaspad@gmail.com can read scraper_logs" ON scraper_logs'
    )

    op.execute(
        """
        CREATE POLICY "Admin email can read scraper_logs" ON scraper_logs
        FOR SELECT USING (
            EXISTS (
                SELECT 1 FROM profiles 
                WHERE id = (select auth.uid()) AND email = 'nicholaspad@gmail.com'
            )
            OR (select auth.role()) = 'service_role'
        )
    """
    )


def downgrade() -> None:
    # ===========================================
    # PROFILES TABLE - Restore original policies
    # ===========================================

    op.execute('DROP POLICY IF EXISTS "Users can view own profile" ON profiles')
    op.execute('DROP POLICY IF EXISTS "Users can insert own profile" ON profiles')
    op.execute('DROP POLICY IF EXISTS "Users can update own profile" ON profiles')
    op.execute('DROP POLICY IF EXISTS "Service role full access" ON profiles')

    # Restore original (non-optimized) policies
    op.execute(
        """
        CREATE POLICY "Users can view own data" ON profiles
        FOR SELECT USING (auth.uid() = id)
    """
    )
    op.execute(
        """
        CREATE POLICY "Users can view own profile" ON profiles
        FOR SELECT USING (auth.uid() = id)
    """
    )
    op.execute(
        """
        CREATE POLICY "Users can update own data" ON profiles
        FOR UPDATE USING (auth.uid() = id)
    """
    )
    op.execute(
        """
        CREATE POLICY "Users can update own profile" ON profiles
        FOR UPDATE USING (auth.uid() = id)
    """
    )
    op.execute(
        """
        CREATE POLICY "Authenticated users can insert" ON profiles
        FOR INSERT WITH CHECK (auth.uid() = id)
    """
    )
    op.execute(
        """
        CREATE POLICY "Admins can view all users" ON profiles
        FOR SELECT USING (
            EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin')
        )
    """
    )
    op.execute(
        """
        CREATE POLICY "Service role full access" ON profiles
        FOR ALL USING (auth.role() = 'service_role')
    """
    )

    # ===========================================
    # SUBSCRIPTIONS TABLE - Restore original policies
    # ===========================================

    op.execute('DROP POLICY IF EXISTS "Users can view subscriptions" ON subscriptions')
    op.execute(
        'DROP POLICY IF EXISTS "Users can create own subscriptions" ON subscriptions'
    )
    op.execute(
        'DROP POLICY IF EXISTS "Users can update own subscriptions" ON subscriptions'
    )
    op.execute(
        'DROP POLICY IF EXISTS "Users can delete own subscriptions" ON subscriptions'
    )

    op.execute(
        """
        CREATE POLICY "Users can view own subscriptions" ON subscriptions
        FOR SELECT USING (auth.uid() = user_id)
    """
    )
    op.execute(
        """
        CREATE POLICY "Users can create own subscriptions" ON subscriptions
        FOR INSERT WITH CHECK (auth.uid() = user_id)
    """
    )
    op.execute(
        """
        CREATE POLICY "Users can update own subscriptions" ON subscriptions
        FOR UPDATE USING (auth.uid() = user_id)
    """
    )
    op.execute(
        """
        CREATE POLICY "Users can delete own subscriptions" ON subscriptions
        FOR DELETE USING (auth.uid() = user_id)
    """
    )
    op.execute(
        """
        CREATE POLICY "Admins can view all subscriptions" ON subscriptions
        FOR SELECT USING (
            EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin')
        )
    """
    )

    # ===========================================
    # COLLEGES TABLE - Restore original policy
    # ===========================================

    op.execute(
        'DROP POLICY IF EXISTS "Authenticated users can view colleges" ON colleges'
    )

    op.execute(
        """
        CREATE POLICY "Authenticated users can view colleges" ON colleges
        FOR SELECT USING (
            auth.role() = 'authenticated'
            OR auth.role() = 'service_role'
        )
    """
    )

    # ===========================================
    # COURSES TABLE - Restore original policy
    # ===========================================

    op.execute(
        'DROP POLICY IF EXISTS "Authenticated users can view courses" ON courses'
    )

    op.execute(
        """
        CREATE POLICY "Authenticated users can view courses" ON courses
        FOR SELECT USING (
            auth.role() = 'authenticated'
            OR auth.role() = 'service_role'
        )
    """
    )

    # ===========================================
    # CLASSES TABLE - Restore original policy
    # ===========================================

    op.execute(
        'DROP POLICY IF EXISTS "Authenticated users can view classes" ON classes'
    )

    op.execute(
        """
        CREATE POLICY "Authenticated users can view classes" ON classes
        FOR SELECT USING (
            auth.role() = 'authenticated'
            OR auth.role() = 'service_role'
        )
    """
    )

    # ===========================================
    # ENROLLMENTS TABLE - Restore original policy
    # ===========================================

    op.execute(
        'DROP POLICY IF EXISTS "Authenticated users can view enrollments" ON enrollments'
    )

    op.execute(
        """
        CREATE POLICY "Authenticated users can view enrollments" ON enrollments
        FOR SELECT USING (
            auth.role() = 'authenticated'
            OR auth.role() = 'service_role'
        )
    """
    )

    # ===========================================
    # NOTIFICATION_LOGS TABLE - Restore original policies
    # ===========================================

    op.execute(
        'DROP POLICY IF EXISTS "Admins and service role access" ON notification_logs'
    )

    op.execute(
        """
        CREATE POLICY "Admins can view notification logs" ON notification_logs
        FOR SELECT USING (
            EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin')
        )
    """
    )
    op.execute(
        """
        CREATE POLICY "Service role can manage all data" ON notification_logs
        FOR ALL USING (auth.role() = 'service_role')
    """
    )

    # ===========================================
    # SCRAPERS TABLE - Restore original policy
    # ===========================================

    op.execute('DROP POLICY IF EXISTS "Admin email can read scrapers" ON scrapers')

    op.execute(
        """
        CREATE POLICY "Only nicholaspad@gmail.com can read scrapers" ON scrapers
        FOR SELECT USING (
            EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND email = 'nicholaspad@gmail.com')
        )
    """
    )

    # ===========================================
    # SCRAPER_LOGS TABLE - Restore original policy
    # ===========================================

    op.execute(
        'DROP POLICY IF EXISTS "Admin email can read scraper_logs" ON scraper_logs'
    )

    op.execute(
        """
        CREATE POLICY "Only nicholaspad@gmail.com can read scraper_logs" ON scraper_logs
        FOR SELECT USING (
            EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND email = 'nicholaspad@gmail.com')
        )
    """
    )
