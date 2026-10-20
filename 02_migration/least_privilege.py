"""Views + a read-only role for the agent (least privilege).

The agent can:
  - SELECT from the v_* views only
  - INSERT / UPDATE service_tickets
  - INSERT agent_audit_log
Nothing else. On Postgres this is a real database role. On the SQLite fallback
(no roles) the same rules are enforced in common/db.py with a SQLite authorizer.
"""

from sqlalchemy import text

VIEWS = {
    "v_customers": "SELECT customer_id, name, email, phone, city FROM customers",
    "v_pumps": """SELECT p.serial, p.model, p.install_date, p.warranty_until, p.customer_id, c.name AS customer_name, c.email
                  FROM pumps p JOIN customers c ON c.customer_id = p.customer_id""",
    "v_orders": """SELECT o.order_id, o.item, o.amount_inr, o.status, o.status_note, o.order_date, o.expected_delivery, o.courier, o.awb,
                          o.customer_id, c.name AS customer_name, c.email
                   FROM orders o JOIN customers c ON c.customer_id = o.customer_id""",
    "v_service_history": """SELECT t.ticket_id, t.pump_serial, t.created_at, t.ticket_type, t.priority, t.status, t.summary,
                                   t.technician, t.customer_id
                            FROM service_tickets t""",
    "v_technicians": "SELECT tech_id, name, skills FROM technicians",  # no phone numbers for the agent
}

AGENT_READABLE_VIEWS = set(VIEWS)
AGENT_WRITABLE_TABLES = {"service_tickets", "agent_audit_log"}


def create_views(conn) -> None:
    for name, sql in VIEWS.items():
        conn.execute(text(f"DROP VIEW IF EXISTS {name}"))
        conn.execute(text(f"CREATE VIEW {name} AS {sql}"))


def create_agent_role(conn, password: str) -> None:
    """Postgres only: a login role that can read views and write two tables."""
    safe_password = password.replace("'", "''")
    conn.execute(text(f"""
        DO $$ BEGIN
          IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'copilot_agent') THEN
            CREATE ROLE copilot_agent LOGIN PASSWORD '{safe_password}';
          END IF;
        END $$;"""))
    conn.execute(text("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM copilot_agent"))
    conn.execute(text("GRANT USAGE ON SCHEMA public TO copilot_agent"))
    conn.execute(text(f"GRANT SELECT ON {', '.join(sorted(VIEWS))} TO copilot_agent"))
    conn.execute(text("GRANT SELECT, INSERT, UPDATE ON service_tickets TO copilot_agent"))
    conn.execute(text("GRANT INSERT ON agent_audit_log TO copilot_agent"))
    conn.execute(text("GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO copilot_agent"))
