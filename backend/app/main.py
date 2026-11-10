from contextlib import asynccontextmanager
from datetime import date
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.models import Church, Member, PrayerRequest, Testimony, User
from app.routes import router
from app.security import hash_password

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("life_epm")


# Ajoute des exemples identifiés comme fictifs seulement si le mode démo est actif et qu'il n'y a aucun fidèle.
def seed_demo_data(db: Session, church: Church, enabled: bool) -> int:
    if not enabled or db.query(Member.id).filter(Member.church_id == church.id).first() is not None:
        return 0

    today = date.today()
    members = [
        Member(
            church_id=church.id,
            church_number=f"{church.initials}-{today.year}-{today.month:02d}-{index:03d}",
            first_name=first_name,
            last_name="Exemple",
            arrival_date=today,
            spiritual_status=spiritual_status,
            is_demo=True,
        )
        for index, (first_name, spiritual_status) in enumerate(
            [
                ("Aïssata", "membre simple"),
                ("Jean", "ouvrier"),
                ("Grâce", "néophyte"),
                ("Samuel", "membre simple"),
                ("Élodie", "ouvrier"),
            ],
            start=1,
        )
    ]
    db.add_all(members)
    db.flush()
    db.add_all(
        [
            PrayerRequest(
                church_id=church.id,
                member_id=members[0].id,
                author_name="Aïssata Exemple",
                category="emploi",
                content="Sujet de démonstration : accompagnement dans une recherche d'emploi.",
                is_confidential=False,
            ),
            PrayerRequest(
                church_id=church.id,
                member_id=members[2].id,
                author_name="Grâce Exemple",
                category="famille",
                content="Sujet de démonstration : prière pour la famille.",
                is_confidential=False,
            ),
            Testimony(
                church_id=church.id,
                member_id=members[1].id,
                title="Témoignage de démonstration",
                content="Exemple fictif pour présenter la page des témoignages.",
            ),
        ]
    )
    logger.info("Seeded %s demo members for church %s.", len(members), church.id)
    return len(members)


# Vérifie les secrets puis crée l'église et l'administrateur initiaux sans écraser un compte existant.
def bootstrap() -> None:
    settings = get_settings()
    if len(settings.jwt_secret) < 32:
        raise RuntimeError("JWT_SECRET doit contenir au moins 32 caractères.")
    if len(settings.bootstrap_admin_password) < 12:
        raise RuntimeError("BOOTSTRAP_ADMIN_PASSWORD doit contenir au moins 12 caractères.")
    with SessionLocal() as db:
        church = db.query(Church).first()
        if church is None:
            church = Church(
                name=settings.church_name,
                denomination=settings.church_name,
                initials=settings.church_initials,
                city=settings.church_city,
            )
            db.add(church)
            db.flush()
        existing_admin = db.query(User).filter(User.username == settings.bootstrap_admin_username).first()
        if existing_admin is None:
            db.add(
                User(
                    church_id=church.id,
                    username=settings.bootstrap_admin_username,
                    full_name=settings.bootstrap_admin_full_name,
                    role="super_admin",
                    password_hash=hash_password(settings.bootstrap_admin_password),
                    must_change_password=True,
                )
            )
            logger.info("Bootstrap administrator created for church %s.", church.id)
        seed_demo_data(db, church, settings.demo_data_enabled)
        db.commit()


# Configure le démarrage, le CORS et l'enregistrement des routes de l'API.
@asynccontextmanager
async def lifespan(_: FastAPI):
    bootstrap()
    yield


settings = get_settings()
app = FastAPI(title="Life EPM API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type"],
)
app.include_router(router)
