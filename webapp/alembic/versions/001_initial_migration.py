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
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create colleges table
    op.create_table(
        "colleges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("short_name", sa.String(), nullable=False),
        sa.Column("domain", sa.String(), nullable=True),
        sa.Column("term_code", sa.String(), nullable=True),
        sa.Column("term_name", sa.String(), nullable=True),
        sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sms_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_colleges_id"), "colleges", ["id"], unique=False)
    op.create_index("colleges_short_name_idx", "colleges", ["short_name"], unique=True)

    # Create profiles table (users)
    op.create_table(
        "profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("college_id", sa.Integer(), nullable=True),
        sa.Column("role", sa.String(), nullable=False, server_default="user"),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ["college_id"],
            ["colleges.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("profiles_email_idx", "profiles", ["email"], unique=True)

    # Create courses table
    op.create_table(
        "courses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("course_code", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.ForeignKeyConstraint(
            ["college_id"],
            ["colleges.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_courses_college_id"), "courses", ["college_id"], unique=False
    )
    op.create_index(
        op.f("ix_courses_course_code"), "courses", ["course_code"], unique=False
    )
    op.create_index(op.f("ix_courses_id"), "courses", ["id"], unique=False)
    op.create_index(op.f("ix_courses_title"), "courses", ["title"], unique=False)
    op.create_index(
        "courses_college_course_code_idx",
        "courses",
        ["college_id", "course_code"],
        unique=True,
    )
    op.create_index("courses_course_code_idx", "courses", ["course_code"], unique=False)
    op.create_index("courses_title_idx", "courses", ["title"], unique=False)
    # Trigram indexes for fuzzy search (requires pg_trgm extension)
    op.execute(
        "CREATE INDEX courses_course_code_trgm_idx ON courses USING gin (course_code gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX courses_title_trgm_idx ON courses USING gin (title gin_trgm_ops)"
    )
    # Composite indexes
    op.create_index(
        "courses_college_active_idx",
        "courses",
        ["college_id", "is_active"],
        unique=False,
    )
    op.create_index(
        "courses_college_active_updated_idx",
        "courses",
        ["college_id", "is_active", "updated_at"],
        unique=False,
    )

    # Create classes table
    op.create_table(
        "classes",
        sa.Column("class_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("class_number", sa.String(), nullable=False),
        sa.Column("section_code", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
        ),
        sa.PrimaryKeyConstraint("class_id"),
    )
    op.create_index(op.f("ix_classes_class_id"), "classes", ["class_id"], unique=False)
    op.create_index(
        op.f("ix_classes_course_id"), "classes", ["course_id"], unique=False
    )
    op.create_index(
        "classes_course_class_number_idx",
        "classes",
        ["course_id", "class_number"],
        unique=True,
    )

    # Create enrollments table
    op.create_table(
        "enrollments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("class_id", sa.Integer(), nullable=False),
        sa.Column("enrollment_status", sa.String(), nullable=False),
        sa.Column(
            "scraped_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["class_id"],
            ["classes.class_id"],
        ),
        sa.ForeignKeyConstraint(
            ["college_id"],
            ["colleges.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_enrollments_class_id"), "enrollments", ["class_id"], unique=False
    )
    op.create_index(
        op.f("ix_enrollments_college_id"), "enrollments", ["college_id"], unique=False
    )
    op.create_index(op.f("ix_enrollments_id"), "enrollments", ["id"], unique=False)
    op.create_index(
        "enrollments_class_id_idx", "enrollments", ["class_id"], unique=False
    )
    op.create_index(
        "enrollments_scraped_at_idx", "enrollments", ["scraped_at"], unique=False
    )
    op.create_index(
        "enrollments_status_idx", "enrollments", ["enrollment_status"], unique=False
    )
    op.create_index(
        "enrollments_college_status_idx",
        "enrollments",
        ["college_id", "enrollment_status"],
        unique=False,
    )
    op.create_index(
        "enrollments_class_scraped_idx",
        "enrollments",
        ["class_id", "scraped_at"],
        unique=False,
    )
    op.create_index(
        "enrollments_class_status_scraped_idx",
        "enrollments",
        ["class_id", "enrollment_status", "scraped_at"],
        unique=False,
    )
    op.create_index(
        "enrollments_college_scraped_idx",
        "enrollments",
        ["college_id", "scraped_at"],
        unique=False,
    )
    op.create_index(
        "enrollments_status_scraped_idx",
        "enrollments",
        ["enrollment_status", "scraped_at"],
        unique=False,
    )

    # Create subscriptions table
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("class_id", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_notified", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "notification_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["class_id"],
            ["classes.class_id"],
        ),
        sa.ForeignKeyConstraint(
            ["college_id"],
            ["colleges.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["profiles.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_subscriptions_class_id"), "subscriptions", ["class_id"], unique=False
    )
    op.create_index(
        op.f("ix_subscriptions_college_id"),
        "subscriptions",
        ["college_id"],
        unique=False,
    )
    op.create_index(op.f("ix_subscriptions_id"), "subscriptions", ["id"], unique=False)
    op.create_index(
        op.f("ix_subscriptions_user_id"), "subscriptions", ["user_id"], unique=False
    )
    op.create_index(
        "subscriptions_active_idx", "subscriptions", ["is_active"], unique=False
    )
    op.create_index(
        "subscriptions_class_active_idx",
        "subscriptions",
        ["class_id", "is_active"],
        unique=False,
    )
    op.create_index(
        "subscriptions_user_active_idx",
        "subscriptions",
        ["user_id", "is_active"],
        unique=False,
    )
    op.create_index(
        "subscriptions_college_active_idx",
        "subscriptions",
        ["college_id", "is_active"],
        unique=False,
    )
    op.create_index(
        "subscriptions_class_college_active_idx",
        "subscriptions",
        ["class_id", "college_id", "is_active"],
        unique=False,
    )

    # Create notification_logs table
    op.create_table(
        "notification_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=False),
        sa.Column("notification_type", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("seats_remaining", sa.Integer(), nullable=True),
        sa.Column("enrollment_status", sa.String(), nullable=True),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["college_id"],
            ["colleges.id"],
        ),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["subscriptions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_notification_logs_college_id"),
        "notification_logs",
        ["college_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notification_logs_id"), "notification_logs", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_notification_logs_subscription_id"),
        "notification_logs",
        ["subscription_id"],
        unique=False,
    )
    op.create_index(
        "notification_logs_sent_at_idx", "notification_logs", ["sent_at"], unique=False
    )
    op.create_index(
        "notification_logs_subscription_sent_idx",
        "notification_logs",
        ["subscription_id", "sent_at"],
        unique=False,
    )
    op.create_index(
        "notification_logs_college_sent_idx",
        "notification_logs",
        ["college_id", "sent_at"],
        unique=False,
    )
    op.create_index(
        "notification_logs_status_sent_idx",
        "notification_logs",
        ["status", "sent_at"],
        unique=False,
    )
    op.create_index(
        "notification_logs_college_status_sent_idx",
        "notification_logs",
        ["college_id", "status", "sent_at"],
        unique=False,
    )

    # Create scrapers table
    op.create_table(
        "scrapers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="idle"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("run_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("last_run_duration_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["college_id"],
            ["colleges.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_scrapers_college_id"), "scrapers", ["college_id"], unique=False
    )
    op.create_index(op.f("ix_scrapers_id"), "scrapers", ["id"], unique=False)
    op.create_index("scrapers_college_id_idx", "scrapers", ["college_id"], unique=True)
    op.create_index("scrapers_status_idx", "scrapers", ["status"], unique=False)
    op.create_index("scrapers_next_run_idx", "scrapers", ["next_run_at"], unique=False)

    # Create scraper_logs table
    op.create_table(
        "scraper_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scraper_id", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("stack_trace", sa.Text(), nullable=True),
        sa.Column("courses_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("classes_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "enrollments_saved", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["scraper_id"],
            ["scrapers.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scraper_logs_id"), "scraper_logs", ["id"], unique=False)
    op.create_index(
        op.f("ix_scraper_logs_scraper_id"), "scraper_logs", ["scraper_id"], unique=False
    )
    op.create_index(
        "scraper_logs_scraper_id_idx", "scraper_logs", ["scraper_id"], unique=False
    )
    op.create_index(
        "scraper_logs_outcome_idx", "scraper_logs", ["outcome"], unique=False
    )
    op.create_index(
        "scraper_logs_started_at_idx", "scraper_logs", ["started_at"], unique=False
    )
    op.create_index(
        "scraper_logs_scraper_started_idx",
        "scraper_logs",
        ["scraper_id", "started_at"],
        unique=False,
    )

    # Create early_access_emails table
    op.create_table(
        "early_access_emails",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_early_access_emails_id"), "early_access_emails", ["id"], unique=False
    )
    op.create_index(
        "early_access_emails_email_idx", "early_access_emails", ["email"], unique=True
    )

    # Create stripe_customers table
    op.create_table(
        "stripe_customers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stripe_customer_id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["profiles.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
        sa.UniqueConstraint("stripe_customer_id"),
    )
    op.create_index(
        op.f("ix_stripe_customers_id"), "stripe_customers", ["id"], unique=False
    )
    op.create_index(
        "stripe_customers_user_id_idx", "stripe_customers", ["user_id"], unique=True
    )
    op.create_index(
        "stripe_customers_stripe_id_idx",
        "stripe_customers",
        ["stripe_customer_id"],
        unique=True,
    )

    # Create stripe_subscriptions table
    op.create_table(
        "stripe_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stripe_subscription_id", sa.String(), nullable=False),
        sa.Column("stripe_customer_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("price_id", sa.String(), nullable=False),
        sa.Column("tier", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["stripe_customer_id"],
            ["stripe_customers.stripe_customer_id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["profiles.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stripe_subscription_id"),
    )
    op.create_index(
        op.f("ix_stripe_subscriptions_id"), "stripe_subscriptions", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_stripe_subscriptions_user_id"),
        "stripe_subscriptions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "stripe_subscriptions_user_id_idx",
        "stripe_subscriptions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "stripe_subscriptions_stripe_id_idx",
        "stripe_subscriptions",
        ["stripe_subscription_id"],
        unique=True,
    )
    op.create_index(
        "stripe_subscriptions_status_idx",
        "stripe_subscriptions",
        ["status"],
        unique=False,
    )

    # Create query_performance_metrics table
    op.create_table(
        "query_performance_metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("query_name", sa.String(), nullable=False),
        sa.Column("execution_time", sa.Integer(), nullable=False),
        sa.Column("result_count", sa.Integer(), nullable=True),
        sa.Column("parameters", sa.Text(), nullable=True),
        sa.Column(
            "executed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_query_performance_metrics_id"),
        "query_performance_metrics",
        ["id"],
        unique=False,
    )
    op.create_index(
        "qpm_query_name_executed_idx",
        "query_performance_metrics",
        ["query_name", "executed_at"],
        unique=False,
    )
    op.create_index(
        "qpm_executed_at_idx",
        "query_performance_metrics",
        ["executed_at"],
        unique=False,
    )
    op.create_index(
        "qpm_query_exec_time_idx",
        "query_performance_metrics",
        ["query_name", "execution_time"],
        unique=False,
    )
    op.create_index(
        "qpm_query_time_exec_idx",
        "query_performance_metrics",
        ["query_name", "executed_at", "execution_time"],
        unique=False,
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("query_performance_metrics")
    op.drop_table("stripe_subscriptions")
    op.drop_table("stripe_customers")
    op.drop_table("early_access_emails")
    op.drop_table("scraper_logs")
    op.drop_table("scrapers")
    op.drop_table("notification_logs")
    op.drop_table("subscriptions")
    op.drop_table("enrollments")
    op.drop_table("classes")
    op.drop_table("courses")
    op.drop_table("profiles")
    op.drop_table("colleges")
