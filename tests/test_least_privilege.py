"""The agent's database rules, checked on a tiny in-memory SQLite database."""

import sqlite3

import pytest
from least_privilege import create_views
from schema import metadata
from sqlalchemy import create_engine

from common.db import agent_authorizer


@pytest.fixture
def agent_conn(tmp_path):
    path = tmp_path / "t.db"
    engine = create_engine(f"sqlite:///{path}")
    with engine.begin() as conn:
        metadata.create_all(conn)
        conn.exec_driver_sql("INSERT INTO customers VALUES (1, 'Ramesh Patil', 'r@x.com', '9822011234', 'Pune')")
        conn.exec_driver_sql("INSERT INTO technicians VALUES ('T01', 'Suresh', 'centrifugal', '9822000101')")
        create_views(conn)
    con = sqlite3.connect(path)
    con.set_authorizer(agent_authorizer)
    return con


def test_agent_can_read_views(agent_conn):
    assert agent_conn.execute("SELECT name FROM v_customers").fetchall() == [("Ramesh Patil",)]


@pytest.mark.parametrize("sql", [
    "SELECT * FROM customers",                         # raw table, not a view
    "SELECT phone FROM technicians",                   # technician phone numbers are hidden
    "UPDATE customers SET name = 'x'",
    "DELETE FROM service_tickets",
    "DROP TABLE orders",
    "SELECT * FROM agent_audit_log",                   # the audit log is insert-only for the agent
])
def test_agent_is_blocked(agent_conn, sql):
    with pytest.raises(sqlite3.DatabaseError):
        agent_conn.execute(sql)


def test_agent_can_write_its_two_tables(agent_conn):
    agent_conn.execute("INSERT INTO service_tickets (customer_id, summary, source) VALUES (1, 'test', 'agent')")
    agent_conn.execute("INSERT INTO agent_audit_log (ts, action, actor) VALUES ('2026-10-20', 'test', 'agent')")
