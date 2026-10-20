"""The clean, modern schema. Works on Postgres and on the SQLite fallback."""

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, MetaData, String, Table, Text

metadata = MetaData()

customers = Table(
    "customers", metadata,
    Column("customer_id", Integer, primary_key=True),
    Column("name", String(120), nullable=False),
    Column("email", String(200)),          # can be empty: the old system didn't always ask
    Column("phone", String(10), nullable=False, unique=True),  # 10 digits, our dedupe key
    Column("city", String(80)),
)

pumps = Table(
    "pumps", metadata,
    Column("pump_id", Integer, primary_key=True),
    Column("serial", String(20), nullable=False, unique=True),
    Column("model", String(10), nullable=False),           # VP-100 / VS-200 / VB-300
    Column("customer_id", Integer, ForeignKey("customers.customer_id"), nullable=False),
    Column("install_date", Date),
    Column("warranty_until", Date),
)

orders = Table(
    "orders", metadata,
    Column("order_id", String(12), primary_key=True),       # always "ORD-12345"
    Column("customer_id", Integer, ForeignKey("customers.customer_id"), nullable=False),
    Column("item", String(200)),
    Column("amount_inr", Float),
    Column("status", String(20), nullable=False),           # one of ORDER_STATUSES
    Column("status_note", String(120)),                     # the original free text, e.g. "on hold - payment"
    Column("order_date", Date),
    Column("expected_delivery", Date),
    Column("courier", String(60)),
    Column("awb", String(40)),                              # courier tracking number
    Column("source", String(20)),                           # legacy_db / shop_csv
)

technicians = Table(
    "technicians", metadata,
    Column("tech_id", String(5), primary_key=True),
    Column("name", String(80), nullable=False),
    Column("skills", String(120)),                          # "centrifugal;booster"
    Column("phone", String(10)),
)

# The agent may INSERT/UPDATE here (new tickets from complaints and bookings).
service_tickets = Table(
    "service_tickets", metadata,
    Column("ticket_id", Integer, primary_key=True),
    Column("customer_id", Integer, ForeignKey("customers.customer_id")),
    Column("pump_serial", String(20)),
    Column("created_at", DateTime),
    Column("ticket_type", String(20)),                      # installation / repair / complaint / visit
    Column("priority", String(10)),                         # low / normal / high
    Column("status", String(20)),                           # closed / open / scheduled
    Column("summary", Text),
    Column("technician", String(80)),
    Column("source", String(10)),                           # legacy / agent
)

# The agent may only INSERT here. Every action it takes is recorded.
agent_audit_log = Table(
    "agent_audit_log", metadata,
    Column("log_id", Integer, primary_key=True),
    Column("ts", DateTime, nullable=False),
    Column("email_id", String(40)),
    Column("intent", String(30)),
    Column("confidence", Float),
    Column("action", String(40)),                           # classified / drafted / approved / rejected / sent / booked ...
    Column("actor", String(20)),                            # agent / human
    Column("detail", Text),                                 # JSON
)

ORDER_STATUSES = ["pending", "on_hold", "dispatched", "in_transit", "delivered", "cancelled"]
