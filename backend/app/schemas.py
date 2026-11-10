from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# Modèles d'entrée/sortie pour l'authentification et les utilisateurs.
class LoginInput(BaseModel):
    username: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=1, max_length=256)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=120)
    full_name: str = Field(min_length=2, max_length=180)
    password: str = Field(min_length=12, max_length=256)
    role: str = Field(pattern="^(secretary|treasurer|shepherd)$")
    zone_id: int | None = None
    cell_id: int | None = None


class UserOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    full_name: str
    role: str
    must_change_password: bool
    is_active: bool


# Entrées et sorties de la messagerie interne.
class ConversationCreate(BaseModel):
    recipient_user_ids: list[int] = Field(min_length=1, max_length=20)
    title: str | None = Field(default=None, max_length=120)
    message: str = Field(min_length=1, max_length=4000)

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Le message ne peut pas être vide.")
        return value

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("recipient_user_ids")
    @classmethod
    def unique_recipients(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("Un même destinataire ne peut pas être ajouté plusieurs fois.")
        return value


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)

    @field_validator("body")
    @classmethod
    def strip_body(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Le message ne peut pas être vide.")
        return value


class SmsBroadcastCreate(BaseModel):
    member_ids: list[int] = Field(min_length=1, max_length=500)
    message: str = Field(min_length=1, max_length=1000)

    @field_validator("member_ids")
    @classmethod
    def unique_members(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("Un même fidèle ne peut pas être sélectionné plusieurs fois.")
        return value

    @field_validator("message")
    @classmethod
    def strip_sms(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Le SMS ne peut pas être vide.")
        return value


# Validation de l'identité de l'église et des fiches de fidèles.
class ChurchUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    denomination: str = Field(min_length=2, max_length=180)
    initials: str = Field(min_length=2, max_length=12)
    city: str = Field(min_length=2, max_length=100)

    @field_validator("name", "denomination", "initials", "city")
    @classmethod
    def strip_identity_fields(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Ce champ ne peut pas être vide.")
        return value


class MemberCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    gender: str | None = None
    birth_date: date | None = None
    phone: str | None = Field(default=None, max_length=40)
    sms_opt_in: bool = False
    email: str | None = Field(default=None, max_length=180)
    address: str | None = Field(default=None, max_length=255)
    profession: str | None = Field(default=None, max_length=120)
    languages: str | None = Field(default=None, max_length=255)
    marital_status: str | None = None
    family_name: str | None = None
    zone_id: int | None = None
    cell_id: int | None = None
    arrival_date: date = Field(default_factory=date.today)
    conversion_date: date | None = None
    water_baptism_date: date | None = None
    spirit_baptism_date: date | None = None
    origin_church: str | None = None
    spiritual_status: str = "néophyte"


class MemberUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    gender: str | None = Field(default=None, max_length=24)
    birth_date: date | None = None
    phone: str | None = Field(default=None, max_length=40)
    sms_opt_in: bool | None = None
    email: str | None = Field(default=None, max_length=180)
    address: str | None = Field(default=None, max_length=255)
    profession: str | None = Field(default=None, max_length=120)
    languages: str | None = Field(default=None, max_length=255)
    marital_status: str | None = Field(default=None, max_length=32)
    family_name: str | None = Field(default=None, max_length=120)
    zone_id: int | None = None
    cell_id: int | None = None
    arrival_date: date | None = None
    conversion_date: date | None = None
    water_baptism_date: date | None = None
    spirit_baptism_date: date | None = None
    origin_church: str | None = Field(default=None, max_length=180)
    spiritual_status: str | None = Field(default=None, max_length=40)


class MemberOutput(MemberCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    church_number: str
    departure_status: str | None
    is_demo: bool
    created_at: datetime


# Données des cultes/programmes, présences, prières et témoignages.
class ServiceCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    service_group: str = Field(default="culte", pattern="^(culte|programme)$")
    service_type: str = Field(default="Culte dominical", min_length=1, max_length=80)
    starts_at: datetime
    ends_at: datetime | None = None
    speaker: str | None = None
    theme: str | None = None
    location: str | None = None


class ServiceOutput(ServiceCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    attendance_count: int


class AttendanceUpdate(BaseModel):
    present: bool = True


class PrayerCreate(BaseModel):
    member_id: int | None = None
    author_name: str | None = None
    category: str = Field(min_length=1, max_length=80)
    content: str = Field(min_length=1, max_length=4000)
    is_confidential: bool = True


class PrayerOutput(PrayerCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_answered: bool
    created_at: datetime


class TestimonyCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    content: str = Field(min_length=1, max_length=4000)
    member_id: int | None = None


# Les transferts doivent préciser deux comptes différents.
class FinanceCreate(BaseModel):
    journal: str = Field(min_length=2, max_length=40)
    direction: str = Field(pattern="^(recette|depense|transfert)$")
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    currency: str = Field(default="XOF", pattern="^(XOF|EUR|USD)$")
    description: str = Field(min_length=1, max_length=255)
    treasury_account: str = Field(default="caisse", pattern="^(caisse|banque)$")
    counterparty_account: str | None = Field(default=None, pattern="^(caisse|banque)$")
    occurred_on: date = Field(default_factory=date.today)
    member_id: int | None = None

    @model_validator(mode="after")
    def validate_transfer(self):
        if self.direction == "transfert":
            if self.journal != "tresorerie":
                raise ValueError("Un transfert doit être enregistré dans le journal de trésorerie.")
            if self.counterparty_account is None or self.counterparty_account == self.treasury_account:
                raise ValueError("Un transfert doit préciser deux comptes différents (caisse et banque).")
        elif self.counterparty_account is not None:
            raise ValueError("Le compte destinataire est réservé aux transferts.")
        return self


class FinanceOutput(FinanceCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


# Données de l'organisation géographique.
class ZoneCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ZoneOutput(ZoneCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class SectorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class SectorOutput(SectorCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    zone_id: int


class CellCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class CellOutput(CellCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sector_id: int


# Données des budgets et événements familiaux.
class BudgetCreate(BaseModel):
    fiscal_year: int = Field(ge=2000, le=2200)
    label: str = Field(min_length=1, max_length=160)
    budget_class: str = Field(pattern="^(charge|produit)$")
    planned_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)


class MarriageCreate(BaseModel):
    partner_one_id: int
    partner_two_id: int
    engagement_date: date | None = None
    engagement_status: str = "en cours"
    breakup_reason: str | None = None
    dowry_date: date | None = None
    civil_date: date | None = None
    blessing_date: date | None = None


class MarriageOutput(MarriageCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class BirthCreate(BaseModel):
    parent_one_id: int | None = None
    parent_two_id: int | None = None
    child_first_name: str = Field(min_length=1, max_length=100)
    child_last_name: str = Field(min_length=1, max_length=100)
    birth_date: date
    gender: str | None = None


class BirthOutput(BirthCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
