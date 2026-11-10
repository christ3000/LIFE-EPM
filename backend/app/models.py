from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, LargeBinary, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


# Date et heure par défaut des nouveaux enregistrements.
def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# Tables de l'identité de l'église et des comptes utilisateurs.
class Church(Base):
    __tablename__ = "churches"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(180))
    denomination: Mapped[str] = mapped_column(String(180), default="Église Pentecôte Missionnaire")
    initials: Mapped[str] = mapped_column(String(12), default="EPM")
    city: Mapped[str] = mapped_column(String(100), default="Abidjan")
    logo_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    logo_content_type: Mapped[str | None] = mapped_column(String(32), nullable=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    church_id: Mapped[int] = mapped_column(ForeignKey("churches.id", ondelete="CASCADE"), index=True)
    username: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(180))
    role: Mapped[str] = mapped_column(String(32), default="secretary")
    zone_id: Mapped[int | None] = mapped_column(ForeignKey("zones.id", ondelete="SET NULL"), nullable=True)
    cell_id: Mapped[int | None] = mapped_column(ForeignKey("cells.id", ondelete="SET NULL"), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


# Organisation géographique et registre des fidèles.
class Zone(Base):
    __tablename__ = "zones"
    __table_args__ = (UniqueConstraint("church_id", "name", name="uq_zone_church_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    church_id: Mapped[int] = mapped_column(ForeignKey("churches.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    sectors: Mapped[list["Sector"]] = relationship(back_populates="zone", cascade="all, delete-orphan")


class Sector(Base):
    __tablename__ = "sectors"
    __table_args__ = (UniqueConstraint("zone_id", "name", name="uq_sector_zone_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    zone: Mapped[Zone] = relationship(back_populates="sectors")
    cells: Mapped[list["Cell"]] = relationship(back_populates="sector", cascade="all, delete-orphan")


class Cell(Base):
    __tablename__ = "cells"
    __table_args__ = (UniqueConstraint("sector_id", "name", name="uq_cell_sector_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    sector_id: Mapped[int] = mapped_column(ForeignKey("sectors.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    sector: Mapped[Sector] = relationship(back_populates="cells")


class Member(Base):
    __tablename__ = "members"
    __table_args__ = (UniqueConstraint("church_id", "church_number", name="uq_member_church_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    church_id: Mapped[int] = mapped_column(ForeignKey("churches.id", ondelete="CASCADE"), index=True)
    church_number: Mapped[str] = mapped_column(String(40), index=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    gender: Mapped[str | None] = mapped_column(String(24), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(180), nullable=True)
    sms_opt_in: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    profession: Mapped[str | None] = mapped_column(String(120), nullable=True)
    languages: Mapped[str | None] = mapped_column(String(255), nullable=True)
    marital_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    family_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    zone_id: Mapped[int | None] = mapped_column(ForeignKey("zones.id", ondelete="SET NULL"), nullable=True, index=True)
    cell_id: Mapped[int | None] = mapped_column(ForeignKey("cells.id", ondelete="SET NULL"), nullable=True)
    arrival_date: Mapped[date] = mapped_column(Date, default=date.today)
    conversion_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    water_baptism_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    spirit_baptism_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    origin_church: Mapped[str | None] = mapped_column(String(180), nullable=True)
    spiritual_status: Mapped[str] = mapped_column(String(40), default="néophyte")
    departure_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


# Cultes/programmes, présences, sujets de prière et témoignages.
class ChurchService(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True)
    church_id: Mapped[int] = mapped_column(ForeignKey("churches.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    service_group: Mapped[str] = mapped_column(String(16), default="culte", server_default="culte", index=True)
    service_type: Mapped[str] = mapped_column(String(80), default="Culte dominical")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    speaker: Mapped[str | None] = mapped_column(String(160), nullable=True)
    theme: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(180), nullable=True)
    attendance_count: Mapped[int] = mapped_column(Integer, default=0)


class PrayerRequest(Base):
    __tablename__ = "prayer_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    church_id: Mapped[int] = mapped_column(ForeignKey("churches.id", ondelete="CASCADE"), index=True)
    member_id: Mapped[int | None] = mapped_column(ForeignKey("members.id", ondelete="SET NULL"), nullable=True, index=True)
    author_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    category: Mapped[str] = mapped_column(String(80))
    content: Mapped[str] = mapped_column(Text)
    is_confidential: Mapped[bool] = mapped_column(Boolean, default=True)
    is_answered: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


# Opérations financières et budgets.
class FinanceTransaction(Base):
    __tablename__ = "finance_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    church_id: Mapped[int] = mapped_column(ForeignKey("churches.id", ondelete="CASCADE"), index=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    journal: Mapped[str] = mapped_column(String(40), index=True)
    direction: Mapped[str] = mapped_column(String(12))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3), default="XOF")
    description: Mapped[str] = mapped_column(String(255))
    treasury_account: Mapped[str] = mapped_column(String(12), default="caisse")
    counterparty_account: Mapped[str | None] = mapped_column(String(12), nullable=True)
    occurred_on: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    member_id: Mapped[int | None] = mapped_column(ForeignKey("members.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class BudgetLine(Base):
    __tablename__ = "budget_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    church_id: Mapped[int] = mapped_column(ForeignKey("churches.id", ondelete="CASCADE"), index=True)
    fiscal_year: Mapped[int] = mapped_column(Integer, index=True)
    label: Mapped[str] = mapped_column(String(160))
    budget_class: Mapped[str] = mapped_column(String(16))
    planned_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))


# Messagerie interne réservée aux comptes participants de la même église.
class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    church_id: Mapped[int] = mapped_column(ForeignKey("churches.id", ondelete="CASCADE"), index=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_group: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class ConversationParticipant(Base):
    __tablename__ = "conversation_participants"
    __table_args__ = (UniqueConstraint("conversation_id", "user_id", name="uq_conversation_participant"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    last_read_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


# Historique conservé en base, fonctionnalité retirée de l'interface et de l'API.
class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    church_id: Mapped[int] = mapped_column(ForeignKey("churches.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(180))
    category: Mapped[str] = mapped_column(String(100))
    location: Mapped[str | None] = mapped_column(String(180), nullable=True)
    condition: Mapped[str] = mapped_column(String(40), default="bon")
    acquired_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    church_id: Mapped[int] = mapped_column(ForeignKey("churches.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100))
    entity: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("service_id", "member_id", name="uq_attendance_service_member"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id", ondelete="CASCADE"), index=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), index=True)
    recorded_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    present: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Testimony(Base):
    __tablename__ = "testimonies"

    id: Mapped[int] = mapped_column(primary_key=True)
    church_id: Mapped[int] = mapped_column(ForeignKey("churches.id", ondelete="CASCADE"), index=True)
    member_id: Mapped[int | None] = mapped_column(ForeignKey("members.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(160))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


# Dossiers familiaux.
class MarriageRecord(Base):
    __tablename__ = "marriages"

    id: Mapped[int] = mapped_column(primary_key=True)
    church_id: Mapped[int] = mapped_column(ForeignKey("churches.id", ondelete="CASCADE"), index=True)
    partner_one_id: Mapped[int] = mapped_column(ForeignKey("members.id"))
    partner_two_id: Mapped[int] = mapped_column(ForeignKey("members.id"))
    engagement_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    engagement_status: Mapped[str] = mapped_column(String(32), default="en cours")
    breakup_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    dowry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    civil_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    blessing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class BirthRecord(Base):
    __tablename__ = "births"

    id: Mapped[int] = mapped_column(primary_key=True)
    church_id: Mapped[int] = mapped_column(ForeignKey("churches.id", ondelete="CASCADE"), index=True)
    parent_one_id: Mapped[int | None] = mapped_column(ForeignKey("members.id", ondelete="SET NULL"), nullable=True)
    parent_two_id: Mapped[int | None] = mapped_column(ForeignKey("members.id", ondelete="SET NULL"), nullable=True)
    child_first_name: Mapped[str] = mapped_column(String(100))
    child_last_name: Mapped[str] = mapped_column(String(100))
    birth_date: Mapped[date] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(String(24), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


# Historique conservé en base, fonctionnalité retirée de l'interface et de l'API.
class PastoralFollowup(Base):
    __tablename__ = "pastoral_followups"

    id: Mapped[int] = mapped_column(primary_key=True)
    church_id: Mapped[int] = mapped_column(ForeignKey("churches.id", ondelete="CASCADE"), index=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), index=True)
    recorded_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    followup_type: Mapped[str] = mapped_column(String(24))
    notes: Mapped[str] = mapped_column(Text)
    followed_up_on: Mapped[date] = mapped_column(Date, default=date.today)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
