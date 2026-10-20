"""MCP server: company-db. The agent's only door into the company database.

Tools: get_customer, get_order_status, get_pump_history, create_service_ticket.
It connects with the least-privilege agent engine: it can read the v_* views
and write only service_tickets (+ the audit log, written by the agent itself).

Run standalone (stdio):  python 05_mcp_servers/company_db_server.py
"""

import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server import MCPServer  # noqa: E402  (MCPServer is what mcp 1.x called FastMCP)
from sqlalchemy import text  # noqa: E402

from common.db import agent_engine  # noqa: E402

mcp = MCPServer("company-db", log_level="WARNING")


def _rows(sql: str, **params) -> list[dict]:
    with agent_engine().connect() as conn:
        return [dict(r._mapping) for r in conn.execute(text(sql), params)]


def _jsonable(rows: list[dict]) -> list[dict]:
    """Dates -> 'YYYY-MM-DD' strings so they travel as JSON."""
    return [{k: (v.isoformat() if isinstance(v, (date, datetime)) else v) for k, v in r.items()} for r in rows]


def _in_warranty(warranty_until) -> bool | None:
    if not warranty_until:
        return None
    until = warranty_until if isinstance(warranty_until, date) else date.fromisoformat(str(warranty_until)[:10])
    return until >= date.today()


@mcp.tool()
def get_customer(email: str) -> dict:
    """Look up a customer by email. Returns their details and pumps, or found=False."""
    customers = _rows("SELECT * FROM v_customers WHERE lower(email) = lower(:email)", email=email.strip())
    if not customers:
        return {"found": False, "email": email}
    customer = customers[0]
    pumps = _rows("SELECT serial, model, install_date, warranty_until FROM v_pumps WHERE customer_id = :cid",
                  cid=customer["customer_id"])
    return {"found": True, **customer, "pumps": _jsonable(pumps)}


@mcp.tool()
def get_order_status(order_id: str = "", customer_email: str = "") -> dict:
    """Get an order's status, expected delivery and tracking. Give an order id (e.g. ORD-50412),
    or a customer email to get their 3 most recent orders."""
    if order_id:
        digits = "".join(ch for ch in order_id if ch.isdigit())
        orders = _rows("SELECT * FROM v_orders WHERE order_id = :oid", oid=f"ORD-{digits}")
    elif customer_email:
        orders = _rows("SELECT * FROM v_orders WHERE lower(email) = lower(:email) ORDER BY order_date DESC LIMIT 3",
                       email=customer_email.strip())
    else:
        return {"found": False, "error": "Give an order_id or a customer_email."}
    return {"found": bool(orders), "orders": _jsonable(orders)}


@mcp.tool()
def get_pump_history(serial: str = "", customer_email: str = "") -> dict:
    """Get a pump's model, install date, warranty status and service history.
    Give a serial (e.g. VP100-23117) or a customer email (returns all their pumps)."""
    if serial:
        pumps = _rows("SELECT * FROM v_pumps WHERE upper(serial) = upper(:s)", s=serial.strip())
    elif customer_email:
        pumps = _rows("SELECT * FROM v_pumps WHERE lower(email) = lower(:email)", email=customer_email.strip())
    else:
        return {"found": False, "error": "Give a serial or a customer_email."}
    result = []
    for pump in pumps:
        history = _rows("SELECT created_at, ticket_type, summary, technician, status FROM v_service_history "
                        "WHERE pump_serial = :s ORDER BY created_at", s=pump["serial"])
        result.append({**_jsonable([pump])[0], "in_warranty": _in_warranty(pump["warranty_until"]),
                       "service_history": _jsonable(history)})
    return {"found": bool(result), "pumps": result}


@mcp.tool()
def create_service_ticket(customer_email: str, summary: str, ticket_type: str = "repair",
                          priority: str = "normal", pump_serial: str = "", technician: str = "") -> dict:
    """Open a service ticket. ticket_type: repair / complaint / visit. priority: low / normal / high."""
    customer = _rows("SELECT customer_id FROM v_customers WHERE lower(email) = lower(:e)", e=customer_email.strip())
    with agent_engine().begin() as conn:
        result = conn.execute(text("""
            INSERT INTO service_tickets (customer_id, pump_serial, created_at, ticket_type, priority, status, summary, technician, source)
            VALUES (:cid, :serial, :now, :type, :priority, :status, :summary, :tech, 'agent')
            RETURNING ticket_id"""), {
            "cid": customer[0]["customer_id"] if customer else None, "serial": pump_serial or None,
            "now": datetime.now(), "type": ticket_type, "priority": priority,
            "status": "scheduled" if ticket_type == "visit" else "open", "summary": summary, "tech": technician or None,
        })
        ticket_id = result.scalar_one()
    return {"ticket_id": ticket_id, "status": "scheduled" if ticket_type == "visit" else "open", "priority": priority}


if __name__ == "__main__":
    mcp.run()  # stdio transport by default
