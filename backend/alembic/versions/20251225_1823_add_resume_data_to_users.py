"""
Add resume_data and related fields to users table

Revision ID: 20251225_1823
Revises: c1988511bab1
Create Date: 2025-12-25 18:23:00.000000+00:00
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251225_1823'
down_revision = 'c1988511bab1'
branch_labels = None
depends_on = None

def upgrade():
    # Only add the column if it does not already exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('users')]
    if 'resume_data' not in columns:
        op.add_column('users', sa.Column('resume_data', sa.LargeBinary(), nullable=True))

def downgrade():
    # Only drop the column if it exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('users')]
    if 'resume_data' in columns:
        op.drop_column('users', 'resume_data')
