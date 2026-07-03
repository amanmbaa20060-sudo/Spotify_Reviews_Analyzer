from __future__ import annotations

from sqlalchemy import JSON, String, TypeDecorator
from sqlalchemy.dialects.postgresql import ARRAY


class StringList(TypeDecorator):
    """Store string lists as JSON on SQLite and varchar[] on Postgres."""

    impl = JSON
    cache_ok = True

    def __init__(self, length: int = 128) -> None:
        super().__init__()
        self.length = length

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(String(self.length)))
        return dialect.type_descriptor(JSON())


def string_list(length: int) -> StringList:
    return StringList(length)
