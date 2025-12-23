"""
Custom SQLAlchemy types for cross-database compatibility.
"""
from sqlalchemy import TypeDecorator, CHAR, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB as PostgreSQLJSONB
import uuid
import json


class GUID(TypeDecorator):
    """
    Platform-independent GUID type.
    
    Uses PostgreSQL's UUID type when available, otherwise uses
    CHAR(36) for SQLite and stores as string.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value) if isinstance(value, uuid.UUID) else value
        else:
            if isinstance(value, uuid.UUID):
                return str(value)
            return value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)


class JSON(TypeDecorator):
    """
    Platform-independent JSON type.
    
    Uses PostgreSQL's JSONB type when available, otherwise uses
    TEXT for SQLite and stores as JSON string.
    """
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgreSQLJSONB())
        else:
            return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == 'postgresql':
            return value  # PostgreSQL handles dicts/lists directly
        else:
            return json.dumps(value)  # Convert to JSON string for SQLite

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if dialect.name == 'postgresql':
            return value  # PostgreSQL returns dict/list directly
        else:
            return json.loads(value)  # Parse JSON string from SQLite
