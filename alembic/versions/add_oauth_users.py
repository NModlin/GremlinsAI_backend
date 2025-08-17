"""Add OAuth users table

Revision ID: oauth_users_2024
Revises: 7df615c12ca9
Create Date: 2024-01-16 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision = 'oauth_users_2024'
down_revision = '7df615c12ca9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create oauth_users table."""
    op.create_table(
        'oauth_users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('provider_id', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('api_key', sa.String(255), nullable=False),
        sa.Column('api_key_hash', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('permissions', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=func.now()),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
        
        # Primary key
        sa.PrimaryKeyConstraint('id'),
        
        # Unique constraints
        sa.UniqueConstraint('email', 'provider', name='uq_oauth_users_email_provider'),
        sa.UniqueConstraint('provider_id', 'provider', name='uq_oauth_users_provider_id_provider'),
        sa.UniqueConstraint('api_key_hash', name='uq_oauth_users_api_key_hash'),
        
        # Indexes for performance
        sa.Index('ix_oauth_users_email', 'email'),
        sa.Index('ix_oauth_users_provider', 'provider'),
        sa.Index('ix_oauth_users_api_key_hash', 'api_key_hash'),
        sa.Index('ix_oauth_users_created_at', 'created_at'),
        sa.Index('ix_oauth_users_last_login', 'last_login'),
    )


def downgrade() -> None:
    """Drop oauth_users table."""
    op.drop_table('oauth_users')
