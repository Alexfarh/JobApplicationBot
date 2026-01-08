"""add_companies_table_and_update_job_postings

Revision ID: add_companies_job_ingestion
Revises: 20251225_1823
Create Date: 2025-01-07 00:00:00.000000+00:00

"""
from alembic import op
import sqlalchemy as sa


revision = 'add_companies_job_ingestion'
down_revision = '20251225_1823'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create companies table
    op.create_table(
        'companies',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('company_name', sa.String(), nullable=False),
        sa.Column('ats_type', sa.String(), nullable=False),
        sa.Column('board_token', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('last_ingested_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_name', name='uq_company_name')
    )
    op.create_index(op.f('ix_companies_ats_type'), 'companies', ['ats_type'], unique=False)
    op.create_index(op.f('ix_companies_company_name'), 'companies', ['company_name'], unique=True)

    # Update job_postings table using batch mode for SQLite compatibility
    with op.batch_alter_table('job_postings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('company_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('external_job_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('ats_type', sa.String(), nullable=True, server_default='greenhouse'))
        batch_op.add_column(sa.Column('raw_json', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('first_seen_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('last_seen_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'))
        batch_op.create_index(op.f('ix_job_postings_company_id'), ['company_id'], unique=False)
        batch_op.create_index(op.f('ix_job_postings_external_job_id'), ['external_job_id'], unique=False)
        batch_op.create_index(op.f('ix_job_postings_is_active'), ['is_active'], unique=False)
        batch_op.create_foreign_key('fk_job_postings_company_id', 'companies', ['company_id'], ['id'])
        batch_op.create_unique_constraint('uq_job_postings_apply_url', ['apply_url'])
        batch_op.create_unique_constraint('uq_company_external_id_ats', ['company_id', 'external_job_id', 'ats_type'])


def downgrade() -> None:
    # Update job_postings table using batch mode
    with op.batch_alter_table('job_postings', schema=None) as batch_op:
        batch_op.drop_constraint('uq_company_external_id_ats', type_='unique')
        batch_op.drop_constraint('uq_job_postings_apply_url', type_='unique')
        batch_op.drop_constraint('fk_job_postings_company_id', type_='foreignkey')
        batch_op.drop_index(op.f('ix_job_postings_is_active'))
        batch_op.drop_index(op.f('ix_job_postings_external_job_id'))
        batch_op.drop_index(op.f('ix_job_postings_company_id'))
        batch_op.drop_column('is_active')
        batch_op.drop_column('last_seen_at')
        batch_op.drop_column('first_seen_at')
        batch_op.drop_column('raw_json')
        batch_op.drop_column('ats_type')
        batch_op.drop_column('external_job_id')
        batch_op.drop_column('company_id')
    
    # Drop companies table
    op.drop_index(op.f('ix_companies_company_name'), table_name='companies')
    op.drop_index(op.f('ix_companies_ats_type'), table_name='companies')
    op.drop_table('companies')
