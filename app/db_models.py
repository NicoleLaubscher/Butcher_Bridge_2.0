"""Normalised relational data model for the MySQL persistence layer."""

from __future__ import annotations

from datetime import date, datetime

from flask_login import UserMixin
from sqlalchemy import CheckConstraint, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(190), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False, default="retailer")
    active: Mapped[bool] = mapped_column(default=True, nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self) -> bool:
        return self.active


class Scenario(TimestampMixin, db.Model):
    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    code: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    expected_outcome: Mapped[str] = mapped_column(String(80), nullable=False)
    product: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    window_open: Mapped[date] = mapped_column(Date, nullable=False)
    window_close: Mapped[date] = mapped_column(Date, nullable=False)
    commitment_deadline: Mapped[date] = mapped_column(Date, nullable=False)
    compatibility_days: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    minimum_fill_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.95)
    minimum_on_time_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.95)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open")

    demands: Mapped[list["Demand"]] = relationship(back_populates="scenario", cascade="all, delete-orphan")
    quotes: Mapped[list["SupplierQuote"]] = relationship(back_populates="scenario", cascade="all, delete-orphan")
    evaluation_runs: Mapped[list["EvaluationRun"]] = relationship(back_populates="scenario", cascade="all, delete-orphan")
    fulfilment_records: Mapped[list["FulfilmentRecord"]] = relationship(back_populates="scenario", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("compatibility_days >= 0", name="ck_scenario_compatibility_days"),
        CheckConstraint("minimum_fill_rate >= 0 AND minimum_fill_rate <= 1", name="ck_scenario_fill_rate"),
        CheckConstraint("minimum_on_time_rate >= 0 AND minimum_on_time_rate <= 1", name="ck_scenario_on_time"),
    )


class Retailer(TimestampMixin, db.Model):
    __tablename__ = "retailers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    area: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    contact_email: Mapped[str | None] = mapped_column(String(190))

    demands: Mapped[list["Demand"]] = relationship(back_populates="retailer")

    __table_args__ = (UniqueConstraint("name", "area", name="uq_retailer_name_area"),)


class Demand(TimestampMixin, db.Model):
    __tablename__ = "demands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False)
    retailer_id: Mapped[int] = mapped_column(ForeignKey("retailers.id", ondelete="RESTRICT"), nullable=False)
    product: Mapped[str] = mapped_column(String(120), nullable=False)
    quantity_kg: Mapped[float] = mapped_column(Float, nullable=False)
    required_date: Mapped[date] = mapped_column(Date, nullable=False)
    submitted_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    baseline_price_per_kg: Mapped[float] = mapped_column(Float, nullable=False)
    baseline_logistics_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    baseline_handling_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    baseline_distance_km: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    baseline_trips: Mapped[float] = mapped_column(Float, nullable=False, default=1)
    baseline_fill_rate: Mapped[float] = mapped_column(Float, nullable=False, default=1)
    baseline_on_time_rate: Mapped[float] = mapped_column(Float, nullable=False, default=1)
    orders_per_month: Mapped[float] = mapped_column(Float, nullable=False, default=1)
    individual_procurement_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime)

    scenario: Mapped[Scenario] = relationship(back_populates="demands")
    retailer: Mapped[Retailer] = relationship(back_populates="demands")

    __table_args__ = (
        CheckConstraint("quantity_kg > 0", name="ck_demand_positive_quantity"),
        CheckConstraint("baseline_price_per_kg >= 0", name="ck_demand_baseline_price"),
        CheckConstraint("baseline_fill_rate >= 0 AND baseline_fill_rate <= 1", name="ck_demand_fill_rate"),
        CheckConstraint("baseline_on_time_rate >= 0 AND baseline_on_time_rate <= 1", name="ck_demand_on_time"),
        Index("ix_demand_scenario_product_status", "scenario_id", "product", "status"),
    )


class Supplier(TimestampMixin, db.Model):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(190))

    quotes: Mapped[list["SupplierQuote"]] = relationship(back_populates="supplier")


class SupplierQuote(TimestampMixin, db.Model):
    __tablename__ = "supplier_quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False)
    product: Mapped[str] = mapped_column(String(120), nullable=False)
    capacity_kg: Mapped[float] = mapped_column(Float, nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False)
    fixed_fulfilment_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    variable_fulfilment_per_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    handling_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    route_distance_km: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    expected_fill_rate: Mapped[float] = mapped_column(Float, nullable=False, default=1)
    expected_on_time_rate: Mapped[float] = mapped_column(Float, nullable=False, default=1)
    fulfilment_mode: Mapped[str] = mapped_column(String(30), nullable=False, default="delivery")

    scenario: Mapped[Scenario] = relationship(back_populates="quotes")
    supplier: Mapped[Supplier] = relationship(back_populates="quotes")
    price_tiers: Mapped[list["PriceTier"]] = relationship(
        back_populates="quote", cascade="all, delete-orphan", order_by="PriceTier.minimum_kg"
    )
    service_areas: Mapped[list["SupplierServiceArea"]] = relationship(back_populates="quote", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("scenario_id", "supplier_id", "product", name="uq_quote_scenario_supplier_product"),
        CheckConstraint("capacity_kg > 0", name="ck_quote_capacity"),
        CheckConstraint("lead_time_days >= 0", name="ck_quote_lead_time"),
        CheckConstraint("expected_fill_rate >= 0 AND expected_fill_rate <= 1", name="ck_quote_fill_rate"),
        CheckConstraint("expected_on_time_rate >= 0 AND expected_on_time_rate <= 1", name="ck_quote_on_time"),
        Index("ix_quote_scenario_product", "scenario_id", "product"),
    )


class PriceTier(TimestampMixin, db.Model):
    __tablename__ = "price_tiers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quote_id: Mapped[int] = mapped_column(ForeignKey("supplier_quotes.id", ondelete="CASCADE"), nullable=False)
    minimum_kg: Mapped[float] = mapped_column(Float, nullable=False)
    price_per_kg: Mapped[float] = mapped_column(Float, nullable=False)

    quote: Mapped[SupplierQuote] = relationship(back_populates="price_tiers")

    __table_args__ = (
        UniqueConstraint("quote_id", "minimum_kg", name="uq_price_tier_minimum"),
        CheckConstraint("minimum_kg >= 0", name="ck_tier_minimum"),
        CheckConstraint("price_per_kg >= 0", name="ck_tier_price"),
    )


class SupplierServiceArea(TimestampMixin, db.Model):
    __tablename__ = "supplier_service_areas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quote_id: Mapped[int] = mapped_column(ForeignKey("supplier_quotes.id", ondelete="CASCADE"), nullable=False)
    area: Mapped[str] = mapped_column(String(120), nullable=False)

    quote: Mapped[SupplierQuote] = relationship(back_populates="service_areas")

    __table_args__ = (UniqueConstraint("quote_id", "area", name="uq_quote_service_area"),)


class EvaluationRun(TimestampMixin, db.Model):
    __tablename__ = "evaluation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False)
    run_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    decision: Mapped[str] = mapped_column(String(60), nullable=False)
    input_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    result_snapshot: Mapped[str] = mapped_column(Text, nullable=False)

    scenario: Mapped[Scenario] = relationship(back_populates="evaluation_runs")


class FulfilmentRecord(TimestampMixin, db.Model):
    __tablename__ = "fulfilment_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False)
    supplier_name: Mapped[str] = mapped_column(String(160), nullable=False)
    ordered_quantity_kg: Mapped[float] = mapped_column(Float, nullable=False)
    delivered_quantity_kg: Mapped[float] = mapped_column(Float, nullable=False)
    actual_total_cost: Mapped[float] = mapped_column(Float, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    delivered_date: Mapped[date] = mapped_column(Date, nullable=False)
    actual_logistics_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    actual_trips: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    actual_distance_km: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    exception_notes: Mapped[str | None] = mapped_column(Text)

    scenario: Mapped[Scenario] = relationship(back_populates="fulfilment_records")

    __table_args__ = (
        CheckConstraint("ordered_quantity_kg > 0", name="ck_fulfilment_ordered_quantity"),
        CheckConstraint("delivered_quantity_kg >= 0", name="ck_fulfilment_delivered_quantity"),
    )

