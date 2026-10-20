"""Database connections.

admin_engine()  full access. Used by the migration and the human-facing UI (audit log page).
agent_engine()  least privilege. Used by the company-db MCP server, i.e. by the agent.

On Postgres the agent connects as the `copilot_agent` role (see 02_migration/least_privilege.py).
On the SQLite fallback there are no roles, so we install a SQLite "authorizer": a function
SQLite calls before every read/write, which can say yes or no.
"""

import sqlite3
from functools import lru_cache

from sqlalchemy import create_engine, event

from common.config import AGENT_DATABASE_URL, DATABASE_URL

AGENT_WRITABLE_TABLES = {"service_tickets", "agent_audit_log"}
WRITE_ACTIONS = {sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE}
DENIED_ACTIONS = {
    sqlite3.SQLITE_DELETE, sqlite3.SQLITE_DROP_TABLE, sqlite3.SQLITE_DROP_VIEW, sqlite3.SQLITE_CREATE_TABLE,
    sqlite3.SQLITE_CREATE_VIEW, sqlite3.SQLITE_ALTER_TABLE, sqlite3.SQLITE_CREATE_INDEX, sqlite3.SQLITE_DROP_INDEX,
    sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH, sqlite3.SQLITE_CREATE_TRIGGER,
}


def agent_authorizer(action, arg1, arg2, db_name, source_view):
    """SQLite calls this for every operation. Same rules as the Postgres role."""
    if action in DENIED_ACTIONS:
        return sqlite3.SQLITE_DENY
    if action in WRITE_ACTIONS:
        return sqlite3.SQLITE_OK if arg1 in AGENT_WRITABLE_TABLES else sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_READ:
        table = arg1 or ""
        allowed = (
            (source_view or "").startswith("v_")      # reading a table through one of our views
            or table.startswith("v_")
            or table == "service_tickets"              # may read tickets it creates; the audit log is insert-only
            or table.startswith("sqlite_")             # SQLite's own catalogue
            or arg2 == ""                              # table touched but no column value read (join plumbing)
        )
        return sqlite3.SQLITE_OK if allowed else sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


@lru_cache
def admin_engine():
    return create_engine(DATABASE_URL)


@lru_cache
def agent_engine():
    engine = create_engine(AGENT_DATABASE_URL)
    if engine.dialect.name == "sqlite":
        @event.listens_for(engine, "connect")
        def _install_authorizer(dbapi_conn, _record):
            dbapi_conn.set_authorizer(agent_authorizer)
    return engine
