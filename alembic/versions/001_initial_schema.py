"""001 initial schema

Revision ID: 001
Revises:
Create Date: 2025-04-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ── GROUP 1: Architecture ────────────────────────────────────
    op.create_table("hotels",
        sa.Column("id",         UUID(as_uuid=False), primary_key=True),
        sa.Column("name",       sa.String(255),       nullable=False),
        sa.Column("address",    sa.Text),
        sa.Column("created_at", sa.DateTime),
    )

    op.create_table("blocks",
        sa.Column("id",         UUID(as_uuid=False), primary_key=True),
        sa.Column("hotel_id",   UUID(as_uuid=False), sa.ForeignKey("hotels.id"), nullable=False),
        sa.Column("name",       sa.String(100)),
        sa.Column("block_code", sa.String(10), nullable=False),
    )

    op.create_table("floors",
        sa.Column("id",          UUID(as_uuid=False), primary_key=True),
        sa.Column("block_id",    UUID(as_uuid=False), sa.ForeignKey("blocks.id"), nullable=False),
        sa.Column("level",       sa.Integer, nullable=False),
        sa.Column("grid_width",  sa.Integer, nullable=False),
        sa.Column("grid_height", sa.Integer, nullable=False),
        sa.Column("static_grid", JSON, nullable=False),
    )

    op.create_table("pois",
        sa.Column("id",          UUID(as_uuid=False), primary_key=True),
        sa.Column("floor_id",    UUID(as_uuid=False), sa.ForeignKey("floors.id"), nullable=False),
        sa.Column("name",        sa.String(100), nullable=False),
        sa.Column("type",        sa.String(30),  nullable=False),
        sa.Column("coord_x",     sa.Integer, nullable=False),
        sa.Column("coord_y",     sa.Integer, nullable=False),
        sa.Column("is_safe_exit", sa.Boolean, default=False),
    )

    # ── GROUP 2: Surveillance ────────────────────────────────────
    op.create_table("staff",
        sa.Column("id",               UUID(as_uuid=False), primary_key=True),
        sa.Column("hotel_id",         UUID(as_uuid=False), sa.ForeignKey("hotels.id"), nullable=False),
        sa.Column("name",             sa.String(255), nullable=False),
        sa.Column("role",             sa.String(50)),
        sa.Column("phone",            sa.String(30)),
        sa.Column("current_floor_id", UUID(as_uuid=False), sa.ForeignKey("floors.id"), nullable=True),
        sa.Column("current_block_id", UUID(as_uuid=False), sa.ForeignKey("blocks.id"), nullable=True),
        sa.Column("current_status",   sa.String(30), default="available"),
        sa.Column("on_duty",          sa.Boolean, default=False),
    )

    op.create_table("cameras",
        sa.Column("id",         UUID(as_uuid=False), primary_key=True),
        sa.Column("block_id",   UUID(as_uuid=False), sa.ForeignKey("blocks.id"), nullable=False),
        sa.Column("floor_id",   UUID(as_uuid=False), sa.ForeignKey("floors.id"), nullable=False),
        sa.Column("coord_x",    sa.Integer),
        sa.Column("coord_y",    sa.Integer),
        sa.Column("stream_url", sa.Text),
        sa.Column("active",     sa.Boolean, default=True),
    )

    op.create_table("camera_coverage_zones",
        sa.Column("id",        UUID(as_uuid=False), primary_key=True),
        sa.Column("camera_id", UUID(as_uuid=False), sa.ForeignKey("cameras.id"), nullable=False),
        sa.Column("zone_name", sa.String(100)),
        sa.Column("start_x",   sa.Integer, nullable=False),
        sa.Column("start_y",   sa.Integer, nullable=False),
        sa.Column("end_x",     sa.Integer, nullable=False),
        sa.Column("end_y",     sa.Integer, nullable=False),
    )

    op.create_table("guard_posts",
        sa.Column("id",              UUID(as_uuid=False), primary_key=True),
        sa.Column("camera_id",       UUID(as_uuid=False), sa.ForeignKey("cameras.id"), nullable=False),
        sa.Column("staff_id",        UUID(as_uuid=False), sa.ForeignKey("staff.id"), nullable=True),
        sa.Column("bbox_zone",       JSON),
        sa.Column("shift_start",     sa.Time),
        sa.Column("shift_end",       sa.Time),
        sa.Column("weapon_expected", sa.Boolean, default=True),
        sa.Column("uniform_color",   sa.String(50)),
        sa.Column("active",          sa.Boolean, default=True),
    )

    op.create_table("suppression_logs",
        sa.Column("id",                   UUID(as_uuid=False), primary_key=True),
        sa.Column("camera_id",            UUID(as_uuid=False), sa.ForeignKey("cameras.id"), nullable=False),
        sa.Column("matched_post_id",      UUID(as_uuid=False), sa.ForeignKey("guard_posts.id"), nullable=True),
        sa.Column("detection_class",      sa.String(50)),
        sa.Column("confidence",           sa.Float),
        sa.Column("bbox",                 JSON),
        sa.Column("suppression_reason",   sa.String(50)),
        sa.Column("was_inside_bbox_zone", sa.Boolean),
        sa.Column("timestamp",            sa.DateTime),
    )

    # ── GROUP 3: Occupants ───────────────────────────────────────
    op.create_table("guests",
        sa.Column("id",         UUID(as_uuid=False), primary_key=True),
        sa.Column("hotel_id",   UUID(as_uuid=False), sa.ForeignKey("hotels.id"), nullable=False),
        sa.Column("poi_id",     UUID(as_uuid=False), sa.ForeignKey("pois.id"), nullable=True),
        sa.Column("name",       sa.String(255)),
        sa.Column("phone",      sa.String(30)),
        sa.Column("language",   sa.String(10), default="en"),
        sa.Column("session_id", sa.String(100)),
        sa.Column("check_in",   sa.DateTime),
        sa.Column("check_out",  sa.DateTime),
    )

    op.create_table("staff_assignments",
        sa.Column("id",       UUID(as_uuid=False), primary_key=True),
        sa.Column("staff_id", UUID(as_uuid=False), sa.ForeignKey("staff.id"), nullable=False),
        sa.Column("block_id", UUID(as_uuid=False), sa.ForeignKey("blocks.id"), nullable=False),
        sa.Column("floor_id", UUID(as_uuid=False), sa.ForeignKey("floors.id"), nullable=True),
    )

    # ── GROUP 4: Crisis Response ─────────────────────────────────
    op.create_table("chat_sessions",
        sa.Column("id",          UUID(as_uuid=False), primary_key=True),
        sa.Column("hotel_id",    UUID(as_uuid=False), sa.ForeignKey("hotels.id"), nullable=False),
        sa.Column("guest_id",    UUID(as_uuid=False), sa.ForeignKey("guests.id"), nullable=True),
        sa.Column("poi_id",      UUID(as_uuid=False), sa.ForeignKey("pois.id"), nullable=True),
        sa.Column("sender_type", sa.String(20), nullable=False),
        sa.Column("started_at",  sa.DateTime),
        sa.Column("last_active", sa.DateTime),
    )

    op.create_table("chat_messages",
        sa.Column("id",             UUID(as_uuid=False), primary_key=True),
        sa.Column("session_id",     UUID(as_uuid=False), sa.ForeignKey("chat_sessions.id"), nullable=False),
        sa.Column("raw_text",       sa.Text, nullable=False),
        sa.Column("language",       sa.String(10), default="en"),
        sa.Column("threat_type",    sa.String(50)),
        sa.Column("severity",       sa.String(20)),
        sa.Column("nlp_confidence", sa.Float),
        sa.Column("victim_entity",  sa.String(100)),
        sa.Column("symptom_entity", sa.String(100)),
        sa.Column("sent_at",        sa.DateTime),
    )

    op.create_table("incidents",
        sa.Column("id",            UUID(as_uuid=False), primary_key=True),
        sa.Column("hotel_id",      UUID(as_uuid=False), sa.ForeignKey("hotels.id"), nullable=False),
        sa.Column("floor_id",      UUID(as_uuid=False), sa.ForeignKey("floors.id"), nullable=True),
        sa.Column("camera_id",     UUID(as_uuid=False), sa.ForeignKey("cameras.id"), nullable=True),
        sa.Column("message_id",    UUID(as_uuid=False), sa.ForeignKey("chat_messages.id"), nullable=True),
        sa.Column("origin_poi_id", UUID(as_uuid=False), sa.ForeignKey("pois.id"), nullable=True),
        sa.Column("type",          sa.String(50), nullable=False),
        sa.Column("severity",      sa.Integer, nullable=False),
        sa.Column("status",        sa.String(30), default="active"),
        sa.Column("source",        sa.String(10), nullable=False),
        sa.Column("full_location", sa.Text),
        sa.Column("blocked_nodes", JSON),
        sa.Column("detected_at",   sa.DateTime),
        sa.Column("resolved_at",   sa.DateTime, nullable=True),
    )

    op.create_table("emergency_alerts",
        sa.Column("id",            UUID(as_uuid=False), primary_key=True),
        sa.Column("incident_id",   UUID(as_uuid=False), sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column("floor_id",      UUID(as_uuid=False), sa.ForeignKey("floors.id"), nullable=False),
        sa.Column("blocked_nodes", JSON, nullable=False),
        sa.Column("radius",        sa.Float),
        sa.Column("created_at",    sa.DateTime),
    )

    op.create_table("dispatches",
        sa.Column("id",           UUID(as_uuid=False), primary_key=True),
        sa.Column("incident_id",  UUID(as_uuid=False), sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column("staff_id",     UUID(as_uuid=False), sa.ForeignKey("staff.id"), nullable=False),
        sa.Column("message_text", sa.Text),
        sa.Column("ack_status",   sa.String(20), default="PENDING"),
        sa.Column("sent_at",      sa.DateTime),
        sa.Column("acked_at",     sa.DateTime, nullable=True),
    )


def downgrade():
    for table in [
        "dispatches", "emergency_alerts", "incidents",
        "chat_messages", "chat_sessions",
        "staff_assignments", "guests",
        "suppression_logs", "guard_posts",
        "camera_coverage_zones", "cameras",
        "staff", "pois", "floors", "blocks", "hotels",
    ]:
        op.drop_table(table)