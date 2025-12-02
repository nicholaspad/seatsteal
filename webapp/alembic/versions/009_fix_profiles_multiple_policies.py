"""Fix profiles table multiple permissive policies

Revision ID: 009
Revises: 008
Create Date: 2025-12-02 00:00:00

This migration fixes the remaining multiple permissive policies warning on the profiles table.
The previous migration (007) created both individual policies (SELECT, INSERT, UPDATE) AND
a "Service role full access" (FOR ALL) policy, which created overlapping policies.

This migration consolidates by:
1. Dropping the "Service role full access" policy
2. Adding service_role check to each individual policy
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the existing policies from migration 007
    op.execute('DROP POLICY IF EXISTS "Users can view own profile" ON profiles')
    op.execute('DROP POLICY IF EXISTS "Users can insert own profile" ON profiles')
    op.execute('DROP POLICY IF EXISTS "Users can update own profile" ON profiles')
    op.execute('DROP POLICY IF EXISTS "Service role full access" ON profiles')

    # Recreate policies with service_role check included in each
    # This avoids multiple permissive policies for the same action

    # SELECT: Users can view their own profile OR admins can view all OR service_role
    op.execute(
        """
        CREATE POLICY "Users can view own profile" ON profiles
        FOR SELECT USING (
            (select auth.role()) = 'service_role'
            OR (select auth.uid()) = id 
            OR EXISTS (
                SELECT 1 FROM profiles 
                WHERE id = (select auth.uid()) AND role = 'admin'
            )
        )
    """
    )

    # INSERT: Authenticated users can insert their own profile OR service_role
    op.execute(
        """
        CREATE POLICY "Users can insert own profile" ON profiles
        FOR INSERT WITH CHECK (
            (select auth.role()) = 'service_role'
            OR (select auth.uid()) = id
        )
    """
    )

    # UPDATE: Users can update their own profile OR service_role
    op.execute(
        """
        CREATE POLICY "Users can update own profile" ON profiles
        FOR UPDATE USING (
            (select auth.role()) = 'service_role'
            OR (select auth.uid()) = id
        )
    """
    )

    # DELETE: Only service_role can delete profiles
    op.execute(
        """
        CREATE POLICY "Service role can delete profiles" ON profiles
        FOR DELETE USING (
            (select auth.role()) = 'service_role'
        )
    """
    )


def downgrade() -> None:
    # Drop the consolidated policies
    op.execute('DROP POLICY IF EXISTS "Users can view own profile" ON profiles')
    op.execute('DROP POLICY IF EXISTS "Users can insert own profile" ON profiles')
    op.execute('DROP POLICY IF EXISTS "Users can update own profile" ON profiles')
    op.execute('DROP POLICY IF EXISTS "Service role can delete profiles" ON profiles')

    # Restore the policies from migration 007 (with separate Service role full access)
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

    op.execute(
        """
        CREATE POLICY "Users can insert own profile" ON profiles
        FOR INSERT WITH CHECK (
            (select auth.uid()) = id
        )
    """
    )

    op.execute(
        """
        CREATE POLICY "Users can update own profile" ON profiles
        FOR UPDATE USING (
            (select auth.uid()) = id
        )
    """
    )

    op.execute(
        """
        CREATE POLICY "Service role full access" ON profiles
        FOR ALL USING (
            (select auth.role()) = 'service_role'
        )
    """
    )
