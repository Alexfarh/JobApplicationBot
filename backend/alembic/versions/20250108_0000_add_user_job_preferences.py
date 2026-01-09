"""add_user_job_preferences

Revision ID: add_user_job_preferences
Revises: add_companies_job_ingestion
Create Date: 2025-01-08 00:00:00.000000+00:00

"""
from alembic import op
import sqlalchemy as sa
from app.database_types import JSON, GUID


revision = 'add_user_job_preferences'
down_revision = 'add_companies_job_ingestion'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('users')]
    
    with op.batch_alter_table('users', schema=None) as batch_op:
        if 'target_companies' not in columns:
            batch_op.add_column(sa.Column('target_companies', JSON(), nullable=True))
        if 'expected_salary_hourly_min' not in columns:
            batch_op.add_column(sa.Column('expected_salary_hourly_min', sa.Integer(), nullable=True, server_default='30'))
        if 'expected_salary_annual_min' not in columns:
            batch_op.add_column(sa.Column('expected_salary_annual_min', sa.Integer(), nullable=True, server_default='65000'))
        if 'expected_salary_currency' not in columns:
            batch_op.add_column(sa.Column('expected_salary_currency', sa.String(10), nullable=True, server_default='CAD'))
        if 'salary_flexibility_note' not in columns:
            batch_op.add_column(sa.Column('salary_flexibility_note', sa.String(), nullable=True))
        if 'internship_only' not in columns:
            batch_op.add_column(sa.Column('internship_only', sa.Boolean(), nullable=False, server_default='true'))
        if 'preferred_job_types' not in columns:
            batch_op.add_column(sa.Column('preferred_job_types', JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('resume_data')
        batch_op.drop_column('preferred_job_types')
        batch_op.drop_column('internship_only')
        batch_op.drop_column('salary_flexibility_note')
        batch_op.drop_column('expected_salary_currency')
        batch_op.drop_column('expected_salary_annual_min')
        batch_op.drop_column('expected_salary_hourly_min')
        batch_op.drop_column('target_companies')
