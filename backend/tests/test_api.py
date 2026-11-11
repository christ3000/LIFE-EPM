import os
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.schemas import FinanceCreate


# Crée une base SQLite isolée et démarre la vraie API pour ce module de tests.
@pytest.fixture(scope="module")
def client(tmp_path_factory: pytest.TempPathFactory):
    database_path = tmp_path_factory.mktemp("life-epm") / "test.sqlite"
    os.environ["DATABASE_URL"] = f"sqlite:///{database_path.as_posix()}"
    os.environ["JWT_SECRET"] = "test-jwt-secret-that-is-at-least-thirty-two-characters"
    os.environ["BOOTSTRAP_ADMIN_USERNAME"] = "pasteur.bobou"
    os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = "initial-test-password-2026"
    os.environ["BOOTSTRAP_ADMIN_FULL_NAME"] = "Pasteur BOBOU Josué E."
    os.environ["DEMO_DATA_ENABLED"] = "false"

    from app.config import get_settings

    get_settings.cache_clear()
    from app.db import Base, engine
    from app.main import app

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)


# Vérifie la connexion, le changement de mot de passe initial et les droits financiers.
def test_admin_bootstrap_password_change_and_finance_rbac(client: TestClient) -> None:
    response = client.post("/api/auth/login", json={"username": "pasteur.bobou", "password": "initial-test-password-2026"})
    assert response.status_code == 200
    assert response.json()["full_name"] == "Pasteur BOBOU Josué E."
    assert response.json()["must_change_password"] is True
    assert client.get("/api/members").status_code == 403

    os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = "replacement-test-password-2026"
    from app.config import get_settings
    from app.main import bootstrap

    get_settings.cache_clear()
    bootstrap()
    client.post("/api/auth/logout")
    assert client.post(
        "/api/auth/login",
        json={"username": "pasteur.bobou", "password": "initial-test-password-2026"},
    ).status_code == 401
    replacement_login = client.post(
        "/api/auth/login",
        json={"username": "pasteur.bobou", "password": "replacement-test-password-2026"},
    )
    assert replacement_login.status_code == 200
    assert replacement_login.json()["must_change_password"] is True

    changed = client.post(
        "/api/auth/change-password",
        json={"current_password": "replacement-test-password-2026", "new_password": "permanent-test-password-2026"},
    )
    assert changed.status_code == 200
    assert changed.json()["must_change_password"] is False
    assert client.get("/api/finances").status_code == 200

    os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = "another-test-password-2026"
    get_settings.cache_clear()
    bootstrap()
    client.post("/api/auth/logout")
    assert client.post(
        "/api/auth/login",
        json={"username": "pasteur.bobou", "password": "permanent-test-password-2026"},
    ).status_code == 200

    secretary = client.post(
        "/api/users",
        json={
            "username": "secretary",
            "full_name": "Secrétaire de test",
            "password": "secretary-test-password",
            "role": "secretary",
        },
    )
    assert secretary.status_code == 201
    client.post("/api/auth/logout")
    assert client.post("/api/auth/login", json={"username": "secretary", "password": "secretary-test-password"}).status_code == 200
    assert client.get("/api/finances").status_code == 403
    assert client.get("/api/members").status_code == 403
    assert client.post(
        "/api/auth/change-password",
        json={"current_password": "secretary-test-password", "new_password": "secretary-new-password-2026"},
    ).status_code == 200
    assert client.get("/api/members").status_code == 200
    assert client.get("/api/finances").status_code == 403


def test_internal_messaging_private_conversations_and_unread_counts(client: TestClient) -> None:
    client.post("/api/auth/logout")
    assert client.post(
        "/api/auth/login",
        json={"username": "pasteur.bobou", "password": "permanent-test-password-2026"},
    ).status_code == 200
    recipient_id = client.get("/api/messaging/recipients").json()[0]["id"]
    created = client.post(
        "/api/conversations",
        json={"recipient_user_ids": [recipient_id], "message": "Bonjour, réunion dimanche."},
    )
    assert created.status_code == 201
    conversation_id = created.json()["id"]
    assert created.json()["is_group"] is False
    assert created.json()["unread_count"] == 0
    reopened = client.post(
        "/api/conversations",
        json={"recipient_user_ids": [recipient_id], "message": "À dimanche."},
    )
    assert reopened.status_code == 201
    assert reopened.json()["id"] == conversation_id

    client.post("/api/auth/logout")
    assert client.post(
        "/api/auth/login",
        json={"username": "secretary", "password": "secretary-new-password-2026"},
    ).status_code == 200
    conversation = client.get("/api/conversations").json()[0]
    assert conversation["id"] == conversation_id
    assert conversation["unread_count"] == 2
    messages = client.get(f"/api/conversations/{conversation_id}/messages")
    assert messages.status_code == 200
    assert [message["body"] for message in messages.json()] == ["Bonjour, réunion dimanche.", "À dimanche."]
    assert client.get("/api/conversations").json()[0]["unread_count"] == 0
    assert client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={"body": "Bien reçu, merci."},
    ).status_code == 201

    client.post("/api/auth/logout")
    assert client.post(
        "/api/auth/login",
        json={"username": "pasteur.bobou", "password": "permanent-test-password-2026"},
    ).status_code == 200
    assert client.get("/api/conversations").json()[0]["unread_count"] == 1
    nonparticipant = client.post(
        "/api/users",
        json={
            "username": "nonparticipant",
            "full_name": "Compte non participant",
            "password": "nonparticipant-test-password",
            "role": "secretary",
        },
    )
    assert nonparticipant.status_code == 201
    client.post("/api/auth/logout")
    assert client.post(
        "/api/auth/login",
        json={"username": "nonparticipant", "password": "nonparticipant-test-password"},
    ).status_code == 200
    assert client.post(
        "/api/auth/change-password",
        json={"current_password": "nonparticipant-test-password", "new_password": "nonparticipant-new-password-2026"},
    ).status_code == 200
    assert client.get(f"/api/conversations/{conversation_id}/messages").status_code == 404

    client.post("/api/auth/logout")
    assert client.post(
        "/api/auth/login",
        json={"username": "pasteur.bobou", "password": "permanent-test-password-2026"},
    ).status_code == 200
    group = client.post(
        "/api/conversations",
        json={
            "recipient_user_ids": [recipient_id, nonparticipant.json()["id"]],
            "title": "Équipe de service",
            "message": "Bienvenue dans le groupe.",
        },
    )
    assert group.status_code == 201
    assert group.json()["is_group"] is True
    assert group.json()["title"] == "Équipe de service"

    client.post("/api/auth/logout")
    assert client.post(
        "/api/auth/login",
        json={"username": "nonparticipant", "password": "nonparticipant-new-password-2026"},
    ).status_code == 200
    assert client.get("/api/conversations").json()[0]["id"] == group.json()["id"]
    assert client.get("/api/conversations").json()[0]["unread_count"] == 1


def test_member_numbers_are_generated_and_unique(client: TestClient) -> None:
    first = client.post(
        "/api/members",
        json={"first_name": "Grâce", "last_name": "Kouassi", "arrival_date": "2026-11-02"},
    )
    second = client.post(
        "/api/members",
        json={"first_name": "Jean", "last_name": "Yao", "arrival_date": "2026-11-02"},
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["church_number"] == "EPM-2026-11-001"
    assert second.json()["church_number"] == "EPM-2026-11-002"


def test_sms_broadcast_requires_consent_and_queues_with_provider(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    client.post("/api/auth/logout")
    assert client.post(
        "/api/auth/login",
        json={"username": "pasteur.bobou", "password": "permanent-test-password-2026"},
    ).status_code == 200
    opted_in = client.post(
        "/api/members",
        json={
            "first_name": "Aminata",
            "last_name": "Consentement",
            "phone": "+2250700000000",
            "sms_opt_in": True,
            "arrival_date": "2026-11-03",
        },
    )
    opted_out = client.post(
        "/api/members",
        json={
            "first_name": "Jean",
            "last_name": "Refus",
            "phone": "+2250700000001",
            "sms_opt_in": False,
            "arrival_date": "2026-11-03",
        },
    )
    assert opted_in.status_code == opted_out.status_code == 201
    assert client.get("/api/communications/sms/recipients").json() == [
        {"id": opted_in.json()["id"], "name": "Aminata Consentement", "phone": "+2250700000000"}
    ]
    assert client.post(
        "/api/communications/sms",
        json={"member_ids": [opted_in.json()["id"]], "message": "Réunion dimanche."},
    ).status_code == 503

    from app.config import get_settings
    queued: list[tuple[list[str], str]] = []

    class QueuedTask:
        id = "test-task-id"

    def enqueue(phone_numbers: list[str], message: str) -> QueuedTask:
        queued.append((phone_numbers, message))
        return QueuedTask()

    with monkeypatch.context() as sms_env:
        sms_env.setenv("SMS_PROVIDER", "africas_talking")
        sms_env.setenv("SMS_USERNAME", "sandbox")
        sms_env.setenv("SMS_API_KEY", "test-api-key")
        get_settings.cache_clear()
        sms_env.setattr("app.routes.send_bulk_sms.delay", enqueue)
        queued_response = client.post(
            "/api/communications/sms",
            json={"member_ids": [opted_in.json()["id"]], "message": "Réunion dimanche."},
        )
        assert queued_response.status_code == 202
        assert queued_response.json() == {"task_id": "test-task-id", "recipient_count": 1, "status": "queued"}
        assert queued == [(["+2250700000000"], "Réunion dimanche.")]
        rejected = client.post(
            "/api/communications/sms",
            json={"member_ids": [opted_out.json()["id"]], "message": "Message non sollicité."},
        )
        assert rejected.status_code == 400
    updated = client.patch(f"/api/members/{opted_out.json()['id']}", json={"sms_opt_in": True})
    assert updated.status_code == 200
    assert updated.json()["sms_opt_in"] is True
    assert any(
        recipient["id"] == opted_out.json()["id"]
        for recipient in client.get("/api/communications/sms/recipients").json()
    )
    revoked = client.patch(f"/api/members/{opted_out.json()['id']}", json={"sms_opt_in": False})
    assert revoked.status_code == 200
    assert revoked.json()["sms_opt_in"] is False
    get_settings.cache_clear()


def test_church_identity_can_only_be_updated_by_super_admin(client: TestClient) -> None:
    client.post("/api/auth/logout")
    admin_login = client.post(
        "/api/auth/login",
        json={"username": "pasteur.bobou", "password": "permanent-test-password-2026"},
    )
    assert admin_login.status_code == 200
    identity = {
        "name": "Église Pentecôte Missionnaire",
        "denomination": "Église Pentecôte Missionnaire",
        "initials": "EPM",
        "city": "Abidjan",
    }
    updated = client.patch("/api/church", json=identity)
    assert updated.status_code == 200
    assert {key: updated.json()[key] for key in identity} == identity
    assert updated.json()["logo_url"] is None

    png = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    )
    uploaded = client.post("/api/church/logo", files={"file": ("logo.png", png, "image/png")})
    assert uploaded.status_code == 200
    assert uploaded.json()["logo_url"] == "/api/church/logo"
    logo = client.get("/api/church/logo")
    assert logo.status_code == 200
    assert logo.headers["content-type"] == "image/png"
    assert logo.content == png

    invalid_upload = client.post("/api/church/logo", files={"file": ("logo.png", b"not an image", "image/png")})
    assert invalid_upload.status_code == 422
    assert client.delete("/api/church/logo").status_code == 204
    assert client.get("/api/church/logo").status_code == 404

    assert client.get("/api/followups").status_code == 404
    assert client.post(
        "/api/followups",
        json={
            "member_id": 1,
            "followup_type": "visite",
            "notes": "Entrée non créée",
            "followed_up_on": "2026-11-03",
        },
    ).status_code == 404
    assert client.get("/api/assets").status_code == 404
    assert client.post(
        "/api/assets",
        json={"name": "Bien non créé", "category": "matériel"},
    ).status_code == 404

    client.post("/api/auth/logout")
    assert client.post(
        "/api/auth/login",
        json={"username": "secretary", "password": "secretary-new-password-2026"},
    ).status_code == 200
    assert client.patch("/api/church", json=identity).status_code == 403
    assert client.post("/api/church/logo", files={"file": ("logo.png", png, "image/png")}).status_code == 403


def test_shepherd_cell_scope_limits_member_list_and_attendance(client: TestClient) -> None:
    client.post("/api/auth/logout")
    assert client.post(
        "/api/auth/login",
        json={"username": "pasteur.bobou", "password": "permanent-test-password-2026"},
    ).status_code == 200
    zone = client.post("/api/zones", json={"name": "Zone test"})
    assert zone.status_code == 201
    sector_one = client.post(f"/api/zones/{zone.json()['id']}/sectors", json={"name": "Secteur un"})
    sector_two = client.post(f"/api/zones/{zone.json()['id']}/sectors", json={"name": "Secteur deux"})
    assert sector_one.status_code == sector_two.status_code == 201
    cell_one = client.post(f"/api/sectors/{sector_one.json()['id']}/cells", json={"name": "Cellule un"})
    cell_two = client.post(f"/api/sectors/{sector_two.json()['id']}/cells", json={"name": "Cellule deux"})
    assert cell_one.status_code == cell_two.status_code == 201
    member_one = client.post(
        "/api/members",
        json={"first_name": "Aline", "last_name": "Test", "cell_id": cell_one.json()["id"]},
    )
    member_two = client.post(
        "/api/members",
        json={"first_name": "Benoît", "last_name": "Test", "cell_id": cell_two.json()["id"]},
    )
    assert member_one.status_code == member_two.status_code == 201
    service = client.post(
        "/api/services",
        json={"title": "Culte test", "starts_at": datetime.now(timezone.utc).isoformat()},
    )
    assert service.status_code == 201
    shepherd = client.post(
        "/api/users",
        json={
            "username": "shepherd-cell",
            "full_name": "Berger de cellule",
            "password": "shepherd-test-password-2026",
            "role": "shepherd",
            "cell_id": cell_one.json()["id"],
        },
    )
    assert shepherd.status_code == 201
    client.post("/api/auth/logout")
    shepherd_login = client.post(
        "/api/auth/login",
        json={"username": "shepherd-cell", "password": "shepherd-test-password-2026"},
    )
    assert shepherd_login.status_code == 200
    assert shepherd_login.json()["must_change_password"] is True
    assert client.post(
        "/api/auth/change-password",
        json={
            "current_password": "shepherd-test-password-2026",
            "new_password": "shepherd-new-password-2026",
        },
    ).status_code == 200
    visible_members = client.get("/api/members").json()
    assert [member["id"] for member in visible_members] == [member_one.json()["id"]]
    assert client.post(f"/api/services/{service.json()['id']}/attendance/{member_two.json()['id']}").status_code == 403
    assert client.post(f"/api/services/{service.json()['id']}/attendance/{member_one.json()['id']}").status_code == 201
    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["total_members"] == 1
    assert dashboard.json()["total_presence"] == 1
    assert dashboard.json()["total_absences"] == 0
    assert "finance_month" not in dashboard.json()
    assert "finance_year" not in dashboard.json()


def test_prayers_and_testimonies_share_the_same_ministry_workflow(client: TestClient) -> None:
    client.post("/api/auth/logout")
    assert client.post(
        "/api/auth/login",
        json={"username": "pasteur.bobou", "password": "permanent-test-password-2026"},
    ).status_code == 200
    member = client.post(
        "/api/members",
        json={"first_name": "Témoignage", "last_name": "Essai", "arrival_date": "2026-12-01"},
    )
    assert member.status_code == 201
    prayer = client.post(
        "/api/prayers",
        json={
            "member_id": member.json()["id"],
            "author_name": "Témoignage Essai",
            "category": "emploi",
            "content": "Priez pour une recherche d'emploi.",
            "is_confidential": False,
        },
    )
    assert prayer.status_code == 201
    testimony = client.post(
        "/api/testimonies",
        json={
            "member_id": member.json()["id"],
            "title": "Un emploi trouvé",
            "content": "Le sujet de prière a reçu une réponse.",
        },
    )
    assert testimony.status_code == 201
    assert testimony.json()["record_kind"] == "testimony"
    assert len(client.get("/api/prayers").json()) >= 1
    listed_testimonies = client.get("/api/testimonies").json()
    assert any(item["id"] == testimony.json()["id"] for item in listed_testimonies)
    assert client.post(f"/api/prayers/{prayer.json()['id']}/answer").status_code == 200
    first_testimony_count = len(client.get("/api/testimonies").json())
    assert client.post(f"/api/prayers/{prayer.json()['id']}/answer").status_code == 200
    assert len(client.get("/api/testimonies").json()) == first_testimony_count


def test_demo_seed_is_opt_in_and_only_runs_for_an_empty_church(tmp_path) -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.db import Base
    from app.main import seed_demo_data
    from app.models import Church, Member, PrayerRequest, Testimony

    engine = create_engine(f"sqlite:///{tmp_path / 'demo-seed.sqlite'}")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        church = Church(
            name="Église Pentecôte Missionnaire",
            denomination="Église Pentecôte Missionnaire",
            initials="EPM",
            city="Abidjan",
        )
        db.add(church)
        db.flush()
        assert seed_demo_data(db, church, enabled=False) == 0
        assert seed_demo_data(db, church, enabled=True) == 5
        db.commit()
        assert seed_demo_data(db, church, enabled=True) == 0
        members = db.query(Member).filter(Member.church_id == church.id).all()
        assert len(members) == 5
        assert all(member.is_demo for member in members)
        assert db.query(PrayerRequest).filter(PrayerRequest.church_id == church.id).count() == 2
        assert db.query(Testimony).filter(Testimony.church_id == church.id).count() == 1
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_treasury_transfer_requires_two_distinct_accounts() -> None:
    payload = {
        "journal": "tresorerie",
        "direction": "transfert",
        "amount": "1000",
        "description": "Versement en banque",
        "treasury_account": "caisse",
        "counterparty_account": "banque",
        "occurred_on": "2026-11-02",
    }
    assert FinanceCreate.model_validate(payload).direction == "transfert"
    payload["counterparty_account"] = "caisse"
    with pytest.raises(ValidationError):
        FinanceCreate.model_validate(payload)


def test_activity_and_financial_summaries_include_explicit_attendance_statuses(client: TestClient) -> None:
    client.post("/api/auth/logout")
    login = client.post(
        "/api/auth/login",
        json={"username": "pasteur.bobou", "password": "permanent-test-password-2026"},
    )
    if login.status_code == 401:
        login = client.post(
            "/api/auth/login",
            json={"username": "pasteur.bobou", "password": "initial-test-password-2026"},
        )
        if login.status_code == 200 and login.json()["must_change_password"]:
            changed = client.post(
                "/api/auth/change-password",
                json={
                    "current_password": "initial-test-password-2026",
                    "new_password": "permanent-test-password-2026",
                },
            )
            assert changed.status_code == 200
            login = changed
    assert login.status_code == 200
    member_activity_before = client.get("/api/members/summary").json()
    service_activity_before = client.get("/api/services/summary").json()
    member = client.post(
        "/api/members",
        json={
            "first_name": "Résumé",
            "last_name": "Activité",
            "water_baptism_date": "2024-06-01",
            "spirit_baptism_date": "2025-08-15",
        },
    )
    assert member.status_code == 201
    service = client.post(
        "/api/services",
        json={"title": "Culte pour résumé", "starts_at": datetime.now(timezone.utc).isoformat()},
    )
    assert service.status_code == 201
    program = client.post(
        "/api/services",
        json={
            "title": "Rencontre de jeunesse",
            "service_group": "programme",
            "service_type": "Rencontre de jeunesse",
            "starts_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert program.status_code == 201
    assert program.json()["service_group"] == "programme"
    worship_services = client.get("/api/services?group=culte").json()
    program_services = client.get("/api/services?group=programme").json()
    assert service.json()["id"] in [row["id"] for row in worship_services]
    assert all(row["service_group"] == "culte" for row in worship_services)
    assert [row["id"] for row in program_services] == [program.json()["id"]]
    assert client.get("/api/services/summary?group=programme").json()["total_services"] == 1
    assert client.get("/api/services/summary?group=culte").json()["total_services"] == service_activity_before["total_services"] + 1
    attendance_path = f"/api/services/{service.json()['id']}/attendance/{member.json()['id']}"
    assert client.post(attendance_path, json={"present": False}).status_code == 201
    assert client.get("/api/members/summary").json()["total_absences"] == member_activity_before["total_absences"] + 1
    assert client.get("/api/services/summary").json()["total_absences"] == service_activity_before["total_absences"] + 1
    assert client.post(attendance_path, json={"present": True}).status_code == 201
    assert client.get("/api/members/summary").json()["total_presence"] == member_activity_before["total_presence"] + 1
    service_rows = client.get("/api/services").json()
    assert next(row for row in service_rows if row["id"] == service.json()["id"])["attendance_count"] == 1
    assert client.post(attendance_path, json={"present": False}).status_code == 201
    service_rows = client.get("/api/services").json()
    assert next(row for row in service_rows if row["id"] == service.json()["id"])["attendance_count"] == 0
    member_summary = client.get("/api/members/summary").json()
    assert member_summary["water_baptisms"] == 1
    assert member_summary["spirit_baptisms"] == 1
    assert member_summary["total_absences"] == member_activity_before["total_absences"] + 1

    current_year = datetime.now(timezone.utc).year
    for budget_class, amount in (("charge", 100000), ("produit", 200000)):
        assert client.post(
            "/api/budgets",
            json={"fiscal_year": current_year, "label": f"Prévision {budget_class}", "budget_class": budget_class, "planned_amount": amount},
        ).status_code == 201
    for direction, amount in (("recette", 55000), ("depense", 30000)):
        assert client.post(
            "/api/finances",
            json={"journal": "divers", "direction": direction, "amount": amount, "description": f"Opération {direction}", "occurred_on": f"{current_year}-01-01"},
        ).status_code == 201
    financial = client.get(f"/api/financial-summary?year={current_year}").json()
    assert financial == {
        "year": current_year,
        "planned_charge": "100000.00",
        "planned_product": "200000.00",
        "actual_income": "55000.00",
        "actual_expenses": "30000.00",
    }
