"""SQLAlchemy ORM models for synthetic CRE domain data."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agent_gateway.storage.database import Base


class Building(Base):
    """Commercial building in the portfolio."""

    __tablename__ = "buildings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String(512), nullable=False)
    city: Mapped[str] = mapped_column(String(128), nullable=False, default="Chicago")
    state: Mapped[str] = mapped_column(String(2), nullable=False, default="IL")
    zip_code: Mapped[str] = mapped_column(String(10), nullable=False)
    square_feet: Mapped[int] = mapped_column(Integer, nullable=False)
    property_type: Mapped[str] = mapped_column(String(64), nullable=False)
    year_built: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    work_orders: Mapped[list["WorkOrder"]] = relationship(back_populates="building")


class WorkOrder(Base):
    """Maintenance or service work order."""

    __tablename__ = "work_orders"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    building_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("buildings.id"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    priority: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    assigned_to: Mapped[str | None] = mapped_column(String(128), nullable=True)
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    building: Mapped["Building"] = relationship(back_populates="work_orders")


class PolicyDocument(Base):
    """Governance or operational policy document."""

    __tablename__ = "policy_documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    effective_date: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class MaintenanceRequest(Base):
    """Maintenance request created through the agent write tool."""

    __tablename__ = "maintenance_requests"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_maint_idempotency"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    building_id: Mapped[str] = mapped_column(String(64), ForeignKey("buildings.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
