"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2026-03-31 14:00:00.000000

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
    """Create initial database schema."""
    # Read and execute the schema.sql file
    import os
    from pathlib import Path
    
    schema_file = Path(__file__).parent.parent.parent / "schema.sql"
    with open(schema_file, 'r') as f:
        schema_sql = f.read()
    
    # Execute the schema
    op.execute(schema_sql)


def downgrade() -> None:
    """Drop all tables."""
    # Drop tables in reverse order of dependencies
    op.execute("DROP TABLE IF EXISTS mcp_tool_calls CASCADE")
    op.execute("DROP TABLE IF EXISTS conversation_turns CASCADE")
    op.execute("DROP TABLE IF EXISTS conversations CASCADE")
    op.execute("DROP TABLE IF EXISTS job_parts CASCADE")
    op.execute("DROP TABLE IF EXISTS parts CASCADE")
    op.execute("DROP TABLE IF EXISTS jobs CASCADE")
    op.execute("DROP TABLE IF EXISTS leads CASCADE")
    op.execute("DROP TABLE IF EXISTS technicians CASCADE")
    op.execute("DROP TABLE IF EXISTS customers CASCADE")
    
    # Drop partitioned audit_logs table
    op.execute("DROP TABLE IF EXISTS audit_logs CASCADE")
    
    # Drop function
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column CASCADE")
    
    # Drop extensions
    op.execute("DROP EXTENSION IF EXISTS pg_partman")
    op.execute("DROP EXTENSION IF EXISTS \"uuid-ossp\"")
