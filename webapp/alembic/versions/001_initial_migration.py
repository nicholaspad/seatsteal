"""Initial migration with all models

Revision ID: 001
Revises:
Create Date: 2025-09-30 17:31:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create colleges table
    op.create_table(
        'colleges',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('short_name', sa.String(), nullable=False),
        sa.Column('domain', sa.String(), nullable=True),
        sa.Column('term_code', sa.String(), nullable=True),
        sa.Column('term_name', sa.String(), nullable=True),
        sa.Column('email_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('sms_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_colleges_id'), 'colleges', ['id'], unique=False)
    op.create_index(op.f('ix_colleges_short_name'), 'colleges', ['short_name'], unique=True)

    # Create profiles table (users)
    op.create_table(
        'profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('avatar_url', sa.String(), nullable=True),
        sa.Column('notification_preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_profiles_email'), 'profiles', ['email'], unique=True)
    op.create_index(op.f('ix_profiles_id'), 'profiles', ['id'], unique=False)

    # Create courses table
    op.create_table(
        'courses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('college_id', sa.Integer(), nullable=False),
        sa.Column('course_code', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['college_id'], ['colleges.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_courses_college_id'), 'courses', ['college_id'], unique=False)
    op.create_index(op.f('ix_courses_course_code'), 'courses', ['course_code'], unique=False)
    op.create_index(op.f('ix_courses_id'), 'courses', ['id'], unique=False)
    op.create_index(op.f('ix_courses_title'), 'courses', ['title'], unique=False)
    op.create_index('courses_college_course_code_idx', 'courses', ['college_id', 'course_code'], unique=True)
    op.create_index('courses_college_active_idx', 'courses', ['college_id', 'is_active'], unique=False)
    op.create_index('courses_college_active_updated_idx', 'courses', ['college_id', 'is_active', 'updated_at'], unique=False)

    # Create scraper_logs table
    op.create_table(
        'scraper_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('college_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('courses_scraped', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('classes_scraped', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['college_id'], ['colleges.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scraper_logs_college_id'), 'scraper_logs', ['college_id'], unique=False)
    op.create_index(op.f('ix_scraper_logs_id'), 'scraper_logs', ['id'], unique=False)
    op.create_index('scraper_logs_college_started_idx', 'scraper_logs', ['college_id', 'started_at'], unique=False)
    op.create_index('scraper_logs_status_started_idx', 'scraper_logs', ['status', 'started_at'], unique=False)

    # Create classes table
    op.create_table(
        'classes',
        sa.Column('class_id', sa.Integer(), nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('class_number', sa.String(), nullable=False),
        sa.Column('section_code', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
        sa.PrimaryKeyConstraint('class_id')
    )
    op.create_index(op.f('ix_classes_class_id'), 'classes', ['class_id'], unique=False)
    op.create_index(op.f('ix_classes_class_number'), 'classes', ['class_number'], unique=False)
    op.create_index(op.f('ix_classes_course_id'), 'classes', ['course_id'], unique=False)
    op.create_index('classes_course_class_number_idx', 'classes', ['course_id', 'class_number'], unique=True)
    op.create_index('classes_course_active_idx', 'classes', ['course_id', 'is_active'], unique=False)

    # Create enrollments table
    op.create_table(
        'enrollments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('class_id', sa.Integer(), nullable=False),
        sa.Column('enrolled', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('capacity', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('waitlist', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('instructor', sa.String(), nullable=True),
        sa.Column('schedule', sa.String(), nullable=True),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['class_id'], ['classes.class_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_enrollments_class_id'), 'enrollments', ['class_id'], unique=False)
    op.create_index(op.f('ix_enrollments_id'), 'enrollments', ['id'], unique=False)
    op.create_index('enrollments_class_recorded_idx', 'enrollments', ['class_id', 'recorded_at'], unique=False)
    op.create_index('enrollments_recorded_idx', 'enrollments', ['recorded_at'], unique=False)

    # Create subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('college_id', sa.Integer(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('class_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_notified', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notification_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['class_id'], ['classes.class_id'], ),
        sa.ForeignKeyConstraint(['college_id'], ['colleges.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['profiles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_subscriptions_class_id'), 'subscriptions', ['class_id'], unique=False)
    op.create_index(op.f('ix_subscriptions_college_id'), 'subscriptions', ['college_id'], unique=False)
    op.create_index(op.f('ix_subscriptions_id'), 'subscriptions', ['id'], unique=False)
    op.create_index(op.f('ix_subscriptions_user_id'), 'subscriptions', ['user_id'], unique=False)
    op.create_index('subscriptions_active_idx', 'subscriptions', ['is_active'], unique=False)
    op.create_index('subscriptions_class_active_idx', 'subscriptions', ['class_id', 'is_active'], unique=False)
    op.create_index('subscriptions_user_active_idx', 'subscriptions', ['user_id', 'is_active'], unique=False)
    op.create_index('subscriptions_college_active_idx', 'subscriptions', ['college_id', 'is_active'], unique=False)
    op.create_index('subscriptions_class_college_active_idx', 'subscriptions', ['class_id', 'college_id', 'is_active'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('subscriptions')
    op.drop_table('enrollments')
    op.drop_table('classes')
    op.drop_table('scraper_logs')
    op.drop_table('courses')
    op.drop_table('profiles')
    op.drop_table('colleges')
