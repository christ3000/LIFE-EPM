from datetime import date, datetime, timezone
from decimal import Decimal
import logging

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import (
    Attendance,
    AuditLog,
    BudgetLine,
    BirthRecord,
    Cell,
    Church,
    ChurchService,
    Conversation,
    ConversationParticipant,
    FinanceTransaction,
    Message,
    Member,
    MarriageRecord,
    PrayerRequest,
    Sector,
    Testimony,
    User,
    Zone,
)
from app.schemas import (
    AttendanceUpdate,
    BirthCreate,
    BirthOutput,
    BudgetCreate,
    CellCreate,
    CellOutput,
    ChurchUpdate,
    ConversationCreate,
    FinanceCreate,
    FinanceOutput,
    LoginInput,
    MemberCreate,
    MemberOutput,
    MemberUpdate,
    MarriageCreate,
    MarriageOutput,
    MessageCreate,
    SmsBroadcastCreate,
    PasswordChange,
    PrayerCreate,
    PrayerOutput,
    ServiceCreate,
    ServiceOutput,
    SectorCreate,
    SectorOutput,
    TestimonyCreate,
    UserCreate,
    UserOutput,
    ZoneCreate,
    ZoneOutput,
)
from app.security import COOKIE_NAME, create_session_token, current_user, hash_password, require_roles, verify_password
from app.worker import send_bulk_sms

logger = logging.getLogger("life_epm.routes")

router = APIRouter(prefix="/api")
MEMBER_ROLES = ("super_admin", "secretary", "treasurer", "shepherd")
MAX_CHURCH_LOGO_SIZE = 2 * 1024 * 1024
CHURCH_LOGO_SIGNATURES = {
    "image/png": lambda data: data.startswith(b"\x89PNG\r\n\x1a\n"),
    "image/jpeg": lambda data: data.startswith(b"\xff\xd8\xff"),
    "image/webp": lambda data: data.startswith(b"RIFF") and data[8:12] == b"WEBP",
}


# Vérifie le périmètre d'un berger pour les membres et les présences.
def member_is_in_shepherd_scope(member: Member, user: User) -> bool:
    if user.role != "shepherd":
        return True
    if user.cell_id is not None:
        return member.cell_id == user.cell_id
    if user.zone_id is not None:
        return member.zone_id == user.zone_id
    return False


# Vérification de santé et gestion de la connexion/session.
@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/auth/login", response_model=UserOutput)
def login(payload: LoginInput, response: Response, db: Session = Depends(get_db)) -> User:
    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants incorrects ou compte bloqué.")
    settings = get_settings()
    response.set_cookie(
        COOKIE_NAME,
        create_session_token(user),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        max_age=settings.access_token_minutes * 60,
        path="/",
    )
    return user


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/", samesite="strict")


@router.get("/auth/me", response_model=UserOutput)
def get_me(user: User = Depends(current_user)) -> User:
    return user


@router.post("/auth/change-password", response_model=UserOutput)
def change_password(
    payload: PasswordChange,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> User:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Le mot de passe actuel est incorrect.")
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Choisissez un nouveau mot de passe.")
    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    db.commit()
    db.refresh(user)
    return user


# Identité de l'église et données agrégées du tableau de bord.
def church_identity(church: Church) -> dict[str, str | None]:
    return {
        "name": church.name,
        "denomination": church.denomination,
        "initials": church.initials,
        "city": church.city,
        "logo_url": "/api/church/logo" if church.logo_data else None,
    }


@router.get("/church")
def get_church(user: User = Depends(require_roles(*MEMBER_ROLES)), db: Session = Depends(get_db)) -> dict[str, str | None]:
    church = db.get(Church, user.church_id)
    if church is None:
        raise HTTPException(status_code=404, detail="Église introuvable.")
    return church_identity(church)


@router.get("/church/logo")
def get_church_logo(
    user: User = Depends(require_roles(*MEMBER_ROLES)),
    db: Session = Depends(get_db),
) -> Response:
    church = db.get(Church, user.church_id)
    if church is None:
        raise HTTPException(status_code=404, detail="Église introuvable.")
    if church.logo_data is None or church.logo_content_type is None:
        raise HTTPException(status_code=404, detail="Aucun logo n'est configuré.")
    return Response(
        content=church.logo_data,
        media_type=church.logo_content_type,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.post("/church/logo")
def upload_church_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("super_admin")),
) -> dict[str, str | None]:
    content_type = file.content_type or ""
    signature_check = CHURCH_LOGO_SIGNATURES.get(content_type)
    if signature_check is None:
        raise HTTPException(status_code=415, detail="Format non accepté. Choisissez une image PNG, JPEG ou WebP.")
    logo_data = file.file.read(MAX_CHURCH_LOGO_SIZE + 1)
    if len(logo_data) > MAX_CHURCH_LOGO_SIZE:
        raise HTTPException(status_code=413, detail="Le logo dépasse la taille maximale de 2 Mo.")
    if not logo_data or not signature_check(logo_data):
        raise HTTPException(status_code=422, detail="Le contenu du fichier ne correspond pas à son format d'image.")

    church = db.get(Church, user.church_id)
    if church is None:
        raise HTTPException(status_code=404, detail="Église introuvable.")
    church.logo_data = logo_data
    church.logo_content_type = content_type
    db.add(AuditLog(church_id=user.church_id, user_id=user.id, action="church.logo.update", entity="church", entity_id=church.id))
    db.commit()
    db.refresh(church)
    return church_identity(church)


@router.delete("/church/logo", status_code=status.HTTP_204_NO_CONTENT)
def delete_church_logo(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("super_admin")),
) -> None:
    church = db.get(Church, user.church_id)
    if church is None:
        raise HTTPException(status_code=404, detail="Église introuvable.")
    church.logo_data = None
    church.logo_content_type = None
    db.add(AuditLog(church_id=user.church_id, user_id=user.id, action="church.logo.delete", entity="church", entity_id=church.id))
    db.commit()


@router.patch("/church")
def update_church(
    payload: ChurchUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("super_admin")),
) -> dict[str, str | None]:
    church = db.get(Church, user.church_id)
    if church is None:
        raise HTTPException(status_code=404, detail="Église introuvable.")
    for field, value in payload.model_dump().items():
        setattr(church, field, value)
    db.add(AuditLog(church_id=user.church_id, user_id=user.id, action="church.update", entity="church", entity_id=church.id))
    db.commit()
    db.refresh(church)
    return church_identity(church)


@router.get("/dashboard")
def dashboard(user: User = Depends(require_roles(*MEMBER_ROLES)), db: Session = Depends(get_db)) -> dict:
    church_id = user.church_id
    today = date.today()
    member_filters = [Member.church_id == church_id]
    if user.role == "shepherd":
        if user.cell_id:
            member_filters.append(Member.cell_id == user.cell_id)
        elif user.zone_id:
            member_filters.append(Member.zone_id == user.zone_id)
        else:
            member_filters.append(Member.id == -1)
    count = db.scalar(select(func.count(Member.id)).where(*member_filters)) or 0
    new_members = db.scalar(select(func.count(Member.id)).where(
        *member_filters, Member.arrival_date >= today.replace(day=1)
    )) or 0
    upcoming_filter = [ChurchService.church_id == church_id, ChurchService.starts_at >= datetime.now(timezone.utc)]
    upcoming_service = db.scalar(
        select(ChurchService).where(*upcoming_filter, ChurchService.service_group == "culte").order_by(ChurchService.starts_at).limit(1)
    )
    upcoming_program = db.scalar(
        select(ChurchService).where(*upcoming_filter, ChurchService.service_group == "programme").order_by(ChurchService.starts_at).limit(1)
    )
    total_services = db.scalar(select(func.count(ChurchService.id)).where(
        ChurchService.church_id == church_id, ChurchService.service_group == "culte"
    )) or 0
    total_programs = db.scalar(select(func.count(ChurchService.id)).where(
        ChurchService.church_id == church_id, ChurchService.service_group == "programme"
    )) or 0
    prayer_query = select(func.count(PrayerRequest.id)).where(
        PrayerRequest.church_id == church_id, PrayerRequest.is_answered.is_(False)
    )
    if user.role == "secretary":
        prayer_query = prayer_query.where(PrayerRequest.is_confidential.is_(False))
    if user.role == "shepherd":
        prayer_query = prayer_query.join(Member, PrayerRequest.member_id == Member.id, isouter=True)
        prayer_query = prayer_query.where(PrayerRequest.is_confidential.is_(False))
        if user.cell_id:
            prayer_query = prayer_query.where(Member.cell_id == user.cell_id)
        elif user.zone_id:
            prayer_query = prayer_query.where(Member.zone_id == user.zone_id)
        else:
            prayer_query = prayer_query.where(False)
    open_prayers = db.scalar(prayer_query) or 0
    birthday_query = select(Member).where(*member_filters, Member.birth_date.is_not(None))
    if user.role == "shepherd":
        attendance_query = select(Attendance.present, func.count(Attendance.id)).join(
            ChurchService, Attendance.service_id == ChurchService.id
        ).join(Member, Attendance.member_id == Member.id).where(
            ChurchService.church_id == church_id, *member_filters
        ).group_by(Attendance.present)
        attendance_counts = dict(db.execute(attendance_query).all())
    else:
        attendance_query = select(Attendance.present, func.count(Attendance.id)).join(
            ChurchService, Attendance.service_id == ChurchService.id
        ).where(ChurchService.church_id == church_id).group_by(Attendance.present)
        attendance_counts = dict(db.execute(attendance_query).all())
    birthdays = db.scalars(birthday_query)
    result = {
        "church": get_church(user, db),
        "total_members": count,
        "new_members_this_month": new_members,
        "upcoming_service": ServiceOutput.model_validate(upcoming_service).model_dump(mode="json") if upcoming_service else None,
        "upcoming_program": ServiceOutput.model_validate(upcoming_program).model_dump(mode="json") if upcoming_program else None,
        "total_services": total_services,
        "total_programs": total_programs,
        "open_prayer_requests": open_prayers,
        "total_presence": attendance_counts.get(True, 0),
        "total_absences": attendance_counts.get(False, 0),
        "birthdays_today": [
            {"id": member.id, "name": f"{member.first_name} {member.last_name}"}
            for member in birthdays
            if member.birth_date and (member.birth_date.month, member.birth_date.day) == (today.month, today.day)
        ],
    }
    if user.role in ("super_admin", "treasurer"):
        start = today.replace(day=1)
        total_income = db.scalar(select(func.coalesce(func.sum(FinanceTransaction.amount), 0)).where(FinanceTransaction.church_id == church_id, FinanceTransaction.occurred_on >= start, FinanceTransaction.direction == "recette", FinanceTransaction.currency == "XOF")) or Decimal(0)
        total_expenses = db.scalar(select(func.coalesce(func.sum(FinanceTransaction.amount), 0)).where(FinanceTransaction.church_id == church_id, FinanceTransaction.occurred_on >= start, FinanceTransaction.direction == "depense", FinanceTransaction.currency == "XOF")) or Decimal(0)
        fiscal_year = today.year
        planned_products = db.scalar(select(func.coalesce(func.sum(BudgetLine.planned_amount), 0)).where(BudgetLine.church_id == church_id, BudgetLine.fiscal_year == fiscal_year, BudgetLine.budget_class == "produit")) or Decimal(0)
        planned_charges = db.scalar(select(func.coalesce(func.sum(BudgetLine.planned_amount), 0)).where(BudgetLine.church_id == church_id, BudgetLine.fiscal_year == fiscal_year, BudgetLine.budget_class == "charge")) or Decimal(0)
        result["finance_month"] = {"income": str(total_income), "expenses": str(total_expenses), "currency": "XOF"}
        result["finance_year"] = {"planned_products": str(planned_products), "planned_charges": str(planned_charges), "year": fiscal_year}
    if user.role in ("super_admin", "secretary"):
        result["marriages_count"] = db.scalar(select(func.count(MarriageRecord.id)).where(MarriageRecord.church_id == church_id)) or 0
        result["births_count"] = db.scalar(select(func.count(BirthRecord.id)).where(BirthRecord.church_id == church_id)) or 0
    return result


# Annuaire des fidèles, planification et pointage des cultes/programmes.
@router.get("/members", response_model=list[MemberOutput])
def list_members(
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*MEMBER_ROLES)),
) -> list[Member]:
    query = select(Member).where(Member.church_id == user.church_id)
    if user.role == "shepherd":
        if user.cell_id:
            query = query.where(Member.cell_id == user.cell_id)
        elif user.zone_id:
            query = query.where(Member.zone_id == user.zone_id)
        else:
            return []
    if search:
        term = f"%{search.strip()}%"
        query = query.where(Member.first_name.ilike(term) | Member.last_name.ilike(term) | Member.church_number.ilike(term))
    return list(db.scalars(query.order_by(Member.last_name, Member.first_name).offset(offset).limit(min(limit, 200))))


@router.get("/members/summary")
def member_summary(db: Session = Depends(get_db), user: User = Depends(require_roles(*MEMBER_ROLES))) -> dict[str, int]:
    member_filters = [Member.church_id == user.church_id]
    if user.role == "shepherd":
        if user.cell_id:
            member_filters.append(Member.cell_id == user.cell_id)
        elif user.zone_id:
            member_filters.append(Member.zone_id == user.zone_id)
        else:
            member_filters.append(Member.id == -1)

    def member_count(*extra_filters) -> int:
        return db.scalar(select(func.count(Member.id)).where(*member_filters, *extra_filters)) or 0

    attendance_filters = [Attendance.service_id == ChurchService.id, ChurchService.church_id == user.church_id, *member_filters]
    attendance_count = select(func.count(Attendance.id)).join(ChurchService).join(Member, Attendance.member_id == Member.id).where(*attendance_filters)
    return {
        "total_members": member_count(),
        "water_baptisms": member_count(Member.water_baptism_date.is_not(None)),
        "spirit_baptisms": member_count(Member.spirit_baptism_date.is_not(None)),
        "total_presence": db.scalar(attendance_count.where(Attendance.present.is_(True))) or 0,
        "total_absences": db.scalar(attendance_count.where(Attendance.present.is_(False))) or 0,
    }


@router.post("/members", response_model=MemberOutput, status_code=status.HTTP_201_CREATED)
def create_member(
    payload: MemberCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("super_admin", "secretary")),
) -> Member:
    church = db.scalar(select(Church).where(Church.id == user.church_id).with_for_update())
    if church is None:
        raise HTTPException(status_code=404, detail="Église introuvable.")
    if payload.zone_id is not None and db.scalar(select(Zone.id).where(Zone.id == payload.zone_id, Zone.church_id == user.church_id)) is None:
        raise HTTPException(status_code=400, detail="Zone inconnue pour cette église.")
    member_values = payload.model_dump()
    if payload.cell_id is not None:
        cell_zone_id = db.scalar(
            select(Zone.id)
            .join(Sector)
            .join(Cell)
            .where(Cell.id == payload.cell_id, Zone.church_id == user.church_id)
        )
        if cell_zone_id is None:
            raise HTTPException(status_code=400, detail="Cellule inconnue pour cette église.")
        if payload.zone_id is not None and payload.zone_id != cell_zone_id:
            raise HTTPException(status_code=400, detail="La cellule ne correspond pas à la zone sélectionnée.")
        member_values["zone_id"] = cell_zone_id
    arrival = payload.arrival_date
    month_start = arrival.replace(day=1)
    if arrival.month == 12:
        month_end = date(arrival.year + 1, 1, 1)
    else:
        month_end = date(arrival.year, arrival.month + 1, 1)
    rank = (db.scalar(select(func.count(Member.id)).where(
        Member.church_id == church.id,
        Member.arrival_date >= month_start,
        Member.arrival_date < month_end,
    )) or 0) + 1
    member = Member(
        church_id=church.id,
        church_number=f"{church.initials}-{arrival.year}-{arrival.month:02d}-{rank:03d}",
        **member_values,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.patch("/members/{member_id}", response_model=MemberOutput)
def update_member(
    member_id: int,
    payload: MemberUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("super_admin", "secretary")),
) -> Member:
    member = db.scalar(select(Member).where(Member.id == member_id, Member.church_id == user.church_id))
    if member is None:
        raise HTTPException(status_code=404, detail="Fidèle introuvable.")
    values = payload.model_dump(exclude_unset=True)
    if "zone_id" in values and values["zone_id"] is not None:
        if db.scalar(select(Zone.id).where(Zone.id == values["zone_id"], Zone.church_id == user.church_id)) is None:
            raise HTTPException(status_code=400, detail="Zone inconnue pour cette église.")
    if "cell_id" in values and values["cell_id"] is not None:
        cell_zone_id = db.scalar(
            select(Zone.id)
            .join(Sector)
            .join(Cell)
            .where(Cell.id == values["cell_id"], Zone.church_id == user.church_id)
        )
        if cell_zone_id is None:
            raise HTTPException(status_code=400, detail="Cellule inconnue pour cette église.")
        if values.get("zone_id", member.zone_id) not in (None, cell_zone_id):
            raise HTTPException(status_code=400, detail="La cellule ne correspond pas à la zone sélectionnée.")
        values["zone_id"] = cell_zone_id
    for field, value in values.items():
        setattr(member, field, value)
    db.commit()
    db.refresh(member)
    return member


@router.get("/services", response_model=list[ServiceOutput])
def list_services(
    group: str = Query(default="culte", pattern="^(culte|programme)$"),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*MEMBER_ROLES)),
) -> list[ChurchService]:
    return list(db.scalars(
        select(ChurchService)
        .where(ChurchService.church_id == user.church_id, ChurchService.service_group == group)
        .order_by(ChurchService.starts_at.desc()).limit(100)
    ))


@router.get("/services/summary")
def service_summary(
    group: str = Query(default="culte", pattern="^(culte|programme)$"),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*MEMBER_ROLES)),
) -> dict[str, int | float]:
    service_count = db.scalar(select(func.count(ChurchService.id)).where(
        ChurchService.church_id == user.church_id, ChurchService.service_group == group
    )) or 0
    attendance_query = select(Attendance.present, func.count(Attendance.id)).join(
        ChurchService, Attendance.service_id == ChurchService.id
    ).join(Member, Attendance.member_id == Member.id).where(
        ChurchService.church_id == user.church_id, ChurchService.service_group == group
    )
    if user.role == "shepherd":
        if user.cell_id:
            attendance_query = attendance_query.where(Member.cell_id == user.cell_id)
        elif user.zone_id:
            attendance_query = attendance_query.where(Member.zone_id == user.zone_id)
        else:
            attendance_query = attendance_query.where(Member.id == -1)
    attendance_counts = dict(db.execute(attendance_query.group_by(Attendance.present)).all())
    presences = attendance_counts.get(True, 0)
    absences = attendance_counts.get(False, 0)
    recorded = presences + absences
    return {
        "total_services": service_count,
        "total_presence": presences,
        "total_absences": absences,
        "attendance_rate": round(presences * 100 / recorded, 1) if recorded else 0,
        "recorded_attendance": recorded,
    }


@router.post("/services", response_model=ServiceOutput, status_code=status.HTTP_201_CREATED)
def create_service(payload: ServiceCreate, db: Session = Depends(get_db), user: User = Depends(require_roles("super_admin", "secretary"))) -> ChurchService:
    service = ChurchService(church_id=user.church_id, **payload.model_dump())
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


@router.post("/services/{service_id}/attendance/{member_id}", status_code=status.HTTP_201_CREATED)
def record_attendance(service_id: int, member_id: int, payload: AttendanceUpdate | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles("super_admin", "shepherd"))) -> dict[str, bool]:
    service = db.scalar(select(ChurchService).where(ChurchService.id == service_id, ChurchService.church_id == user.church_id))
    member = db.scalar(select(Member).where(Member.id == member_id, Member.church_id == user.church_id))
    if service is None or member is None:
        raise HTTPException(status_code=404, detail="Culte ou fidèle introuvable.")
    if not member_is_in_shepherd_scope(member, user):
        raise HTTPException(status_code=403, detail="Ce fidèle n'est pas dans votre périmètre.")
    present = payload.present if payload else True
    attendance = db.scalar(select(Attendance).where(Attendance.service_id == service_id, Attendance.member_id == member_id))
    if attendance is None:
        db.add(Attendance(service_id=service_id, member_id=member_id, recorded_by_id=user.id, present=present))
        if present:
            service.attendance_count += 1
    elif attendance.present != present:
        attendance.present = present
        service.attendance_count += 1 if present else -1
    else:
        db.commit()
        return {"present": present}
    db.commit()
    return {"present": present}


# Les sujets de prière respectent la confidentialité et le périmètre du rôle connecté.
@router.get("/prayers", response_model=list[PrayerOutput])
def list_prayers(db: Session = Depends(get_db), user: User = Depends(require_roles(*MEMBER_ROLES))) -> list[PrayerRequest]:
    query = select(PrayerRequest).where(PrayerRequest.church_id == user.church_id)
    if user.role == "secretary":
        query = query.where(PrayerRequest.is_confidential.is_(False))
    if user.role == "shepherd":
        if user.cell_id:
            query = query.join(Member, PrayerRequest.member_id == Member.id, isouter=True).where((Member.cell_id == user.cell_id) | PrayerRequest.member_id.is_(None))
        elif user.zone_id:
            query = query.join(Member, PrayerRequest.member_id == Member.id, isouter=True).where((Member.zone_id == user.zone_id) | PrayerRequest.member_id.is_(None))
        else:
            return []
    return list(db.scalars(query.order_by(PrayerRequest.created_at.desc()).limit(100)))


@router.post("/prayers", response_model=PrayerOutput, status_code=status.HTTP_201_CREATED)
def create_prayer(payload: PrayerCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*MEMBER_ROLES))) -> PrayerRequest:
    if payload.member_id is not None:
        member = db.scalar(select(Member).where(Member.id == payload.member_id, Member.church_id == user.church_id))
        if member is None:
            raise HTTPException(status_code=404, detail="Fidèle introuvable.")
        if not member_is_in_shepherd_scope(member, user):
            raise HTTPException(status_code=403, detail="Ce fidèle n'est pas dans votre périmètre.")
    prayer = PrayerRequest(church_id=user.church_id, **payload.model_dump())
    db.add(prayer)
    db.commit()
    db.refresh(prayer)
    return prayer


@router.post("/prayers/{prayer_id}/answer", response_model=PrayerOutput)
def answer_prayer(prayer_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("super_admin", "shepherd"))) -> PrayerRequest:
    prayer = db.scalar(select(PrayerRequest).where(PrayerRequest.id == prayer_id, PrayerRequest.church_id == user.church_id))
    if prayer is None:
        raise HTTPException(status_code=404, detail="Sujet de prière introuvable.")
    if user.role == "shepherd" and prayer.member_id is not None:
        member = db.get(Member, prayer.member_id)
        if member is None or not member_is_in_shepherd_scope(member, user):
            raise HTTPException(status_code=403, detail="Ce sujet n'est pas dans votre périmètre.")
    if not prayer.is_answered:
        prayer.is_answered = True
        db.add(Testimony(church_id=user.church_id, member_id=prayer.member_id, title=f"Témoignage — {prayer.category}", content=prayer.content))
        db.commit()
        db.refresh(prayer)
    return prayer


# Les finances et budgets sont réservés aux administrateurs et trésoriers.
@router.get("/finances", response_model=list[FinanceOutput])
def list_finances(db: Session = Depends(get_db), user: User = Depends(require_roles("super_admin", "treasurer"))) -> list[FinanceTransaction]:
    return list(db.scalars(select(FinanceTransaction).where(FinanceTransaction.church_id == user.church_id).order_by(FinanceTransaction.occurred_on.desc()).limit(200)))


@router.get("/financial-summary")
def financial_summary(
    year: int = Query(default=date.today().year, ge=2000, le=2200),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("super_admin", "treasurer")),
) -> dict[str, str | int]:
    planned_charge = db.scalar(select(func.coalesce(func.sum(BudgetLine.planned_amount), 0)).where(
        BudgetLine.church_id == user.church_id, BudgetLine.fiscal_year == year, BudgetLine.budget_class == "charge"
    )) or Decimal(0)
    planned_product = db.scalar(select(func.coalesce(func.sum(BudgetLine.planned_amount), 0)).where(
        BudgetLine.church_id == user.church_id, BudgetLine.fiscal_year == year, BudgetLine.budget_class == "produit"
    )) or Decimal(0)
    actual_income = db.scalar(select(func.coalesce(func.sum(FinanceTransaction.amount), 0)).where(
        FinanceTransaction.church_id == user.church_id, FinanceTransaction.occurred_on >= date(year, 1, 1),
        FinanceTransaction.occurred_on < date(year + 1, 1, 1), FinanceTransaction.direction == "recette",
        FinanceTransaction.currency == "XOF",
    )) or Decimal(0)
    actual_expenses = db.scalar(select(func.coalesce(func.sum(FinanceTransaction.amount), 0)).where(
        FinanceTransaction.church_id == user.church_id, FinanceTransaction.occurred_on >= date(year, 1, 1),
        FinanceTransaction.occurred_on < date(year + 1, 1, 1), FinanceTransaction.direction == "depense",
        FinanceTransaction.currency == "XOF",
    )) or Decimal(0)
    return {
        "year": year,
        "planned_charge": str(planned_charge),
        "planned_product": str(planned_product),
        "actual_income": str(actual_income),
        "actual_expenses": str(actual_expenses),
    }


@router.post("/finances", response_model=FinanceOutput, status_code=status.HTTP_201_CREATED)
def create_finance(payload: FinanceCreate, db: Session = Depends(get_db), user: User = Depends(require_roles("super_admin", "treasurer"))) -> FinanceTransaction:
    if payload.member_id is not None and db.scalar(select(Member.id).where(Member.id == payload.member_id, Member.church_id == user.church_id)) is None:
        raise HTTPException(status_code=404, detail="Fidèle introuvable.")
    transaction = FinanceTransaction(church_id=user.church_id, created_by_id=user.id, **payload.model_dump())
    db.add(transaction)
    db.flush()
    db.add(AuditLog(church_id=user.church_id, user_id=user.id, action="finance.create", entity="finance_transaction", entity_id=transaction.id))
    db.commit()
    db.refresh(transaction)
    return transaction


@router.get("/budgets")
def list_budgets(db: Session = Depends(get_db), user: User = Depends(require_roles("super_admin", "treasurer"))) -> list[dict]:
    lines = db.scalars(select(BudgetLine).where(BudgetLine.church_id == user.church_id).order_by(BudgetLine.fiscal_year.desc(), BudgetLine.label))
    return [{"id": line.id, "year": line.fiscal_year, "label": line.label, "class": line.budget_class, "planned_amount": str(line.planned_amount)} for line in lines]


@router.post("/budgets", status_code=status.HTTP_201_CREATED)
def create_budget(payload: BudgetCreate, db: Session = Depends(get_db), user: User = Depends(require_roles("super_admin", "treasurer"))) -> dict:
    budget = BudgetLine(church_id=user.church_id, **payload.model_dump())
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return {"id": budget.id, "year": budget.fiscal_year, "label": budget.label, "class": budget.budget_class, "planned_amount": str(budget.planned_amount)}


# Organisation géographique (zones, secteurs et cellules).
@router.get("/zones", response_model=list[ZoneOutput])
def list_zones(db: Session = Depends(get_db), user: User = Depends(require_roles(*MEMBER_ROLES))) -> list[Zone]:
    return list(db.scalars(select(Zone).where(Zone.church_id == user.church_id).order_by(Zone.name)))


@router.post("/zones", response_model=ZoneOutput, status_code=status.HTTP_201_CREATED)
def create_zone(payload: ZoneCreate, db: Session = Depends(get_db), user: User = Depends(require_roles("super_admin"))) -> Zone:
    zone = Zone(church_id=user.church_id, name=payload.name.strip())
    db.add(zone)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Une zone portant ce nom existe déjà.") from None
    db.refresh(zone)
    return zone


@router.get("/zones/{zone_id}/sectors", response_model=list[SectorOutput])
def list_sectors(zone_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(*MEMBER_ROLES))) -> list[Sector]:
    if db.scalar(select(Zone.id).where(Zone.id == zone_id, Zone.church_id == user.church_id)) is None:
        raise HTTPException(status_code=404, detail="Zone introuvable.")
    return list(db.scalars(select(Sector).where(Sector.zone_id == zone_id).order_by(Sector.name)))


@router.post("/zones/{zone_id}/sectors", response_model=SectorOutput, status_code=status.HTTP_201_CREATED)
def create_sector(zone_id: int, payload: SectorCreate, db: Session = Depends(get_db), user: User = Depends(require_roles("super_admin"))) -> Sector:
    if db.scalar(select(Zone.id).where(Zone.id == zone_id, Zone.church_id == user.church_id)) is None:
        raise HTTPException(status_code=404, detail="Zone introuvable.")
    sector = Sector(zone_id=zone_id, name=payload.name.strip())
    db.add(sector)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Un secteur portant ce nom existe déjà dans cette zone.") from None
    db.refresh(sector)
    return sector


@router.post("/sectors/{sector_id}/cells", response_model=CellOutput, status_code=status.HTTP_201_CREATED)
def create_cell(sector_id: int, payload: CellCreate, db: Session = Depends(get_db), user: User = Depends(require_roles("super_admin"))) -> Cell:
    sector = db.scalar(select(Sector).join(Zone).where(Sector.id == sector_id, Zone.church_id == user.church_id))
    if sector is None:
        raise HTTPException(status_code=404, detail="Secteur introuvable.")
    cell = Cell(sector_id=sector_id, name=payload.name.strip())
    db.add(cell)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Une cellule portant ce nom existe déjà dans ce secteur.") from None
    db.refresh(cell)
    return cell


# Dossiers familiaux.
@router.get("/families/marriages", response_model=list[MarriageOutput])
def list_marriages(db: Session = Depends(get_db), user: User = Depends(require_roles("super_admin", "secretary"))) -> list[MarriageRecord]:
    return list(db.scalars(select(MarriageRecord).where(MarriageRecord.church_id == user.church_id).order_by(MarriageRecord.created_at.desc())))


@router.post("/families/marriages", response_model=MarriageOutput, status_code=status.HTTP_201_CREATED)
def create_marriage(payload: MarriageCreate, db: Session = Depends(get_db), user: User = Depends(require_roles("super_admin", "secretary"))) -> MarriageRecord:
    if payload.partner_one_id == payload.partner_two_id:
        raise HTTPException(status_code=400, detail="Les deux personnes doivent être différentes.")
    partner_ids = db.scalars(select(Member.id).where(Member.church_id == user.church_id, Member.id.in_([payload.partner_one_id, payload.partner_two_id])))
    if len(list(partner_ids)) != 2:
        raise HTTPException(status_code=404, detail="L'un des fidèles est introuvable.")
    marriage = MarriageRecord(church_id=user.church_id, **payload.model_dump())
    db.add(marriage)
    db.commit()
    db.refresh(marriage)
    return marriage


@router.get("/families/births", response_model=list[BirthOutput])
def list_births(db: Session = Depends(get_db), user: User = Depends(require_roles("super_admin", "secretary"))) -> list[BirthRecord]:
    return list(db.scalars(select(BirthRecord).where(BirthRecord.church_id == user.church_id).order_by(BirthRecord.birth_date.desc())))


@router.post("/families/births", response_model=BirthOutput, status_code=status.HTTP_201_CREATED)
def create_birth(payload: BirthCreate, db: Session = Depends(get_db), user: User = Depends(require_roles("super_admin", "secretary"))) -> BirthRecord:
    parent_ids = [member_id for member_id in (payload.parent_one_id, payload.parent_two_id) if member_id is not None]
    if parent_ids and len(list(db.scalars(select(Member.id).where(Member.church_id == user.church_id, Member.id.in_(parent_ids))))) != len(parent_ids):
        raise HTTPException(status_code=404, detail="L'un des parents est introuvable.")
    birth = BirthRecord(church_id=user.church_id, **payload.model_dump())
    db.add(birth)
    db.commit()
    db.refresh(birth)
    return birth


# Témoignages, administration des utilisateurs et communication.
@router.get("/messaging/recipients")
def messaging_recipients(db: Session = Depends(get_db), user: User = Depends(require_roles(*MEMBER_ROLES))) -> list[dict]:
    recipients = db.scalars(
        select(User)
        .where(
            User.church_id == user.church_id,
            User.id != user.id,
            User.is_active.is_(True),
            User.must_change_password.is_(False),
        )
        .order_by(User.full_name)
    )
    return [{"id": recipient.id, "full_name": recipient.full_name, "role": recipient.role} for recipient in recipients]


@router.get("/conversations")
def list_conversations(db: Session = Depends(get_db), user: User = Depends(require_roles(*MEMBER_ROLES))) -> list[dict]:
    conversations = list(
        db.scalars(
            select(Conversation)
            .join(ConversationParticipant, ConversationParticipant.conversation_id == Conversation.id)
            .where(
                Conversation.church_id == user.church_id,
                ConversationParticipant.user_id == user.id,
            )
            .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
            .limit(100)
        )
    )
    if not conversations:
        return []

    conversation_ids = [conversation.id for conversation in conversations]
    participant_rows = db.execute(
        select(ConversationParticipant.conversation_id, User.id, User.full_name)
        .join(User, User.id == ConversationParticipant.user_id)
        .where(ConversationParticipant.conversation_id.in_(conversation_ids))
        .order_by(User.full_name)
    ).all()
    participant_names: dict[int, list[str]] = {}
    for conversation_id, participant_id, full_name in participant_rows:
        if participant_id != user.id:
            participant_names.setdefault(conversation_id, []).append(full_name)

    latest_message_ids = (
        select(func.max(Message.id).label("message_id"))
        .where(Message.conversation_id.in_(conversation_ids))
        .group_by(Message.conversation_id)
        .subquery()
    )
    latest_messages = db.scalars(
        select(Message).join(latest_message_ids, Message.id == latest_message_ids.c.message_id)
    ).all()
    latest_by_conversation: dict[int, Message] = {}
    for message in latest_messages:
        latest_by_conversation.setdefault(message.conversation_id, message)

    unread_rows = db.execute(
        select(ConversationParticipant.conversation_id, func.count(Message.id))
        .outerjoin(
            Message,
            and_(
                Message.conversation_id == ConversationParticipant.conversation_id,
                Message.id > func.coalesce(ConversationParticipant.last_read_message_id, 0),
                Message.sender_id != user.id,
            ),
        )
        .where(
            ConversationParticipant.user_id == user.id,
            ConversationParticipant.conversation_id.in_(conversation_ids),
        )
        .group_by(ConversationParticipant.conversation_id)
    ).all()
    unread_by_conversation = dict(unread_rows)
    sender_ids = {message.sender_id for message in latest_by_conversation.values()}
    senders = {
        sender.id: sender.full_name
        for sender in db.scalars(select(User).where(User.id.in_(sender_ids)))
    } if sender_ids else {}

    return [
        {
            "id": conversation.id,
            "title": conversation.title or (", ".join(participant_names.get(conversation.id, [])) or "Conversation"),
            "is_group": conversation.is_group,
            "participants": participant_names.get(conversation.id, []),
            "last_message": latest_by_conversation[conversation.id].body if conversation.id in latest_by_conversation else "",
            "last_sender": senders.get(latest_by_conversation[conversation.id].sender_id) if conversation.id in latest_by_conversation else None,
            "updated_at": conversation.updated_at,
            "unread_count": unread_by_conversation.get(conversation.id, 0),
        }
        for conversation in conversations
    ]


@router.post("/conversations", status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ConversationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*MEMBER_ROLES)),
) -> dict:
    if user.id in payload.recipient_user_ids:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas vous ajouter comme destinataire.")
    is_group = len(payload.recipient_user_ids) > 1
    if is_group and not payload.title:
        raise HTTPException(status_code=422, detail="Un nom est requis pour une conversation de groupe.")
    recipients = list(
        db.scalars(
            select(User).where(
                User.id.in_(payload.recipient_user_ids),
                User.church_id == user.church_id,
                User.is_active.is_(True),
                User.must_change_password.is_(False),
            )
        )
    )
    if len(recipients) != len(payload.recipient_user_ids):
        raise HTTPException(status_code=404, detail="Un destinataire est introuvable ou ne peut pas accéder à la messagerie.")

    if not is_group:
        direct_conversation_ids = list(db.scalars(
            select(Conversation.id)
            .join(ConversationParticipant, ConversationParticipant.conversation_id == Conversation.id)
            .where(
                Conversation.church_id == user.church_id,
                Conversation.is_group.is_(False),
                ConversationParticipant.user_id == user.id,
            )
        ))
        participants_by_conversation: dict[int, set[int]] = {}
        if direct_conversation_ids:
            for existing_id, participant_id in db.execute(
                select(ConversationParticipant.conversation_id, ConversationParticipant.user_id).where(
                    ConversationParticipant.conversation_id.in_(direct_conversation_ids)
                )
            ):
                participants_by_conversation.setdefault(existing_id, set()).add(participant_id)
        expected_participants = {user.id, recipients[0].id}
        for existing_id in direct_conversation_ids:
            if participants_by_conversation.get(existing_id) == expected_participants:
                existing_conversation = db.get(Conversation, existing_id)
                existing_participant = db.scalar(
                    select(ConversationParticipant).where(
                        ConversationParticipant.conversation_id == existing_id,
                        ConversationParticipant.user_id == user.id,
                    )
                )
                if existing_conversation is None or existing_participant is None:
                    raise RuntimeError("Les données de la conversation existante sont incomplètes.")
                message = Message(conversation_id=existing_id, sender_id=user.id, body=payload.message)
                db.add(message)
                db.flush()
                existing_conversation.updated_at = datetime.now(timezone.utc)
                existing_participant.last_read_message_id = message.id
                db.commit()
                return {
                    "id": existing_id,
                    "title": recipients[0].full_name,
                    "is_group": False,
                    "participants": [recipients[0].full_name],
                    "last_message": message.body,
                    "last_sender": user.full_name,
                    "updated_at": existing_conversation.updated_at,
                    "unread_count": 0,
                }

    conversation = Conversation(
        church_id=user.church_id,
        created_by_id=user.id,
        title=payload.title if is_group else None,
        is_group=is_group,
        updated_at=datetime.now(timezone.utc),
    )
    db.add(conversation)
    db.flush()
    participant_ids = [user.id, *(recipient.id for recipient in recipients)]
    db.add_all(
        ConversationParticipant(conversation_id=conversation.id, user_id=participant_id)
        for participant_id in participant_ids
    )
    message = Message(conversation_id=conversation.id, sender_id=user.id, body=payload.message)
    db.add(message)
    db.flush()
    creator_participant = db.scalar(
        select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == conversation.id,
            ConversationParticipant.user_id == user.id,
        )
    )
    if creator_participant is None:
        raise RuntimeError("Le participant créateur de la conversation est introuvable.")
    creator_participant.last_read_message_id = message.id
    db.commit()
    return {
        "id": conversation.id,
        "title": conversation.title or ", ".join(recipient.full_name for recipient in recipients),
        "is_group": is_group,
        "participants": [recipient.full_name for recipient in recipients],
        "last_message": message.body,
        "last_sender": user.full_name,
        "updated_at": conversation.updated_at,
        "unread_count": 0,
    }


@router.get("/conversations/{conversation_id}/messages")
def list_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*MEMBER_ROLES)),
) -> list[dict]:
    participant = db.scalar(
        select(ConversationParticipant)
        .join(Conversation, Conversation.id == ConversationParticipant.conversation_id)
        .where(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.user_id == user.id,
            Conversation.church_id == user.church_id,
        )
    )
    if participant is None:
        raise HTTPException(status_code=404, detail="Conversation introuvable.")
    messages = list(
        db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.id.desc())
            .limit(200)
        )
    )
    messages.reverse()
    sender_ids = {message.sender_id for message in messages}
    senders = {
        sender.id: sender.full_name
        for sender in db.scalars(select(User).where(User.id.in_(sender_ids)))
    } if sender_ids else {}
    if messages:
        participant.last_read_message_id = messages[-1].id
        db.commit()
    return [
        {
            "id": message.id,
            "sender_id": message.sender_id,
            "sender_name": senders.get(message.sender_id, "Compte supprimé"),
            "body": message.body,
            "created_at": message.created_at,
        }
        for message in messages
    ]


@router.post("/conversations/{conversation_id}/messages", status_code=status.HTTP_201_CREATED)
def send_message(
    conversation_id: int,
    payload: MessageCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*MEMBER_ROLES)),
) -> dict:
    participant = db.scalar(
        select(ConversationParticipant)
        .join(Conversation, Conversation.id == ConversationParticipant.conversation_id)
        .where(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.user_id == user.id,
            Conversation.church_id == user.church_id,
        )
    )
    if participant is None:
        raise HTTPException(status_code=404, detail="Conversation introuvable.")
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation introuvable.")
    message = Message(conversation_id=conversation.id, sender_id=user.id, body=payload.body)
    db.add(message)
    db.flush()
    conversation.updated_at = datetime.now(timezone.utc)
    participant.last_read_message_id = message.id
    db.commit()
    db.refresh(message)
    return {
        "id": message.id,
        "sender_id": user.id,
        "sender_name": user.full_name,
        "body": message.body,
        "created_at": message.created_at,
    }


@router.get("/testimonies")
def list_testimonies(db: Session = Depends(get_db), user: User = Depends(require_roles(*MEMBER_ROLES))) -> list[dict]:
    query = select(Testimony, Member.first_name, Member.last_name).outerjoin(Member, Testimony.member_id == Member.id).where(Testimony.church_id == user.church_id)
    if user.role == "shepherd":
        if user.cell_id:
            query = query.where((Member.cell_id == user.cell_id) | Testimony.member_id.is_(None))
        elif user.zone_id:
            query = query.where((Member.zone_id == user.zone_id) | Testimony.member_id.is_(None))
        else:
            return []
    testimonies = db.execute(query.order_by(Testimony.created_at.desc()).limit(100)).all()
    return [
        {
            "id": testimony.id,
            "record_kind": "testimony",
            "category": "témoignage",
            "title": testimony.title,
            "content": testimony.content,
            "member_id": testimony.member_id,
            "member_name": " ".join(name for name in (first_name, last_name) if name) or None,
            "created_at": testimony.created_at,
        }
        for testimony, first_name, last_name in testimonies
    ]


@router.post("/testimonies", status_code=status.HTTP_201_CREATED)
def create_testimony(
    payload: TestimonyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*MEMBER_ROLES)),
) -> dict:
    member_name = None
    if payload.member_id is not None:
        member = db.scalar(select(Member).where(Member.id == payload.member_id, Member.church_id == user.church_id))
        if member is None:
            raise HTTPException(status_code=404, detail="Fidèle introuvable.")
        if not member_is_in_shepherd_scope(member, user):
            raise HTTPException(status_code=403, detail="Ce fidèle n'est pas dans votre périmètre.")
        member_name = f"{member.first_name} {member.last_name}"
    testimony = Testimony(church_id=user.church_id, **payload.model_dump())
    db.add(testimony)
    db.commit()
    db.refresh(testimony)
    return {
        "id": testimony.id,
        "record_kind": "testimony",
        "category": "témoignage",
        "title": testimony.title,
        "content": testimony.content,
        "member_id": testimony.member_id,
        "member_name": member_name,
        "created_at": testimony.created_at,
    }


@router.get("/users", response_model=list[UserOutput])
def list_users(db: Session = Depends(get_db), user: User = Depends(require_roles("super_admin"))) -> list[User]:
    return list(db.scalars(select(User).where(User.church_id == user.church_id).order_by(User.full_name)))


@router.post("/users", response_model=UserOutput, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db), user: User = Depends(require_roles("super_admin"))) -> User:
    username = payload.username.strip()
    if db.scalar(select(User.id).where(User.username == username)):
        raise HTTPException(status_code=409, detail="Cet identifiant existe déjà.")
    if payload.zone_id is not None and db.scalar(select(Zone.id).where(Zone.id == payload.zone_id, Zone.church_id == user.church_id)) is None:
        raise HTTPException(status_code=400, detail="Zone inconnue pour cette église.")
    if payload.cell_id is not None:
        cell_zone_id = db.scalar(
            select(Zone.id)
            .join(Sector)
            .join(Cell)
            .where(Cell.id == payload.cell_id, Zone.church_id == user.church_id)
        )
        if cell_zone_id is None:
            raise HTTPException(status_code=400, detail="Cellule inconnue pour cette église.")
        if payload.zone_id is not None and payload.zone_id != cell_zone_id:
            raise HTTPException(status_code=400, detail="La cellule ne correspond pas à la zone sélectionnée.")
        if payload.zone_id is None:
            payload.zone_id = cell_zone_id
    new_user = User(church_id=user.church_id, username=username, full_name=payload.full_name.strip(), role=payload.role, password_hash=hash_password(payload.password), must_change_password=True, zone_id=payload.zone_id, cell_id=payload.cell_id)
    db.add(new_user)
    db.flush()
    db.add(AuditLog(church_id=user.church_id, user_id=user.id, action="user.create", entity="user", entity_id=new_user.id))
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/users/{user_id}/block", response_model=UserOutput)
def block_user(user_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("super_admin"))) -> User:
    target = db.scalar(select(User).where(User.id == user_id, User.church_id == user.church_id))
    if target is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas bloquer votre propre compte.")
    target.is_active = False
    db.add(AuditLog(church_id=user.church_id, user_id=user.id, action="user.block", entity="user", entity_id=target.id))
    db.commit()
    db.refresh(target)
    return target


@router.get("/communications/sms/recipients")
def sms_recipients(db: Session = Depends(get_db), user: User = Depends(require_roles("super_admin", "secretary"))) -> list[dict]:
    members = db.scalars(
        select(Member)
        .where(
            Member.church_id == user.church_id,
            Member.sms_opt_in.is_(True),
            Member.phone.is_not(None),
        )
        .order_by(Member.last_name, Member.first_name)
        .limit(500)
    )
    return [
        {"id": member.id, "name": f"{member.first_name} {member.last_name}", "phone": member.phone}
        for member in members
    ]


@router.post("/communications/sms", status_code=status.HTTP_202_ACCEPTED)
def queue_sms(
    payload: SmsBroadcastCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("super_admin", "secretary")),
) -> dict[str, str | int]:
    settings = get_settings()
    if settings.sms_provider != "africas_talking" or not settings.sms_username or not settings.sms_api_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Africa's Talking n'est pas configuré; aucun SMS n'a été envoyé.")
    members = list(
        db.scalars(
            select(Member).where(
                Member.church_id == user.church_id,
                Member.id.in_(payload.member_ids),
                Member.sms_opt_in.is_(True),
                Member.phone.is_not(None),
            )
        )
    )
    if len(members) != len(payload.member_ids):
        raise HTTPException(status_code=400, detail="Un ou plusieurs fidèles n'ont pas donné leur accord SMS ou n'ont pas de numéro.")
    try:
        task = send_bulk_sms.delay([member.phone for member in members if member.phone], payload.message)
    except Exception as error:
        logger.exception("Could not enqueue SMS broadcast for church %s.", user.church_id)
        raise HTTPException(status_code=503, detail="La file d'envoi SMS est indisponible; aucun SMS n'a été envoyé.") from error
    return {"task_id": task.id, "recipient_count": len(members), "status": "queued"}


@router.get("/anniversaries")
def anniversaries(db: Session = Depends(get_db), user: User = Depends(require_roles(*MEMBER_ROLES))) -> list[dict]:
    today = date.today()
    members = db.scalars(select(Member).where(Member.church_id == user.church_id, Member.birth_date.is_not(None)))
    return [
        {"member_id": member.id, "name": f"{member.first_name} {member.last_name}", "kind": "naissance"}
        for member in members
        if member.birth_date and (member.birth_date.month, member.birth_date.day) == (today.month, today.day)
    ]
