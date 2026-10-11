from app.database import init_db
from app.memory import MemoryManager
from app.agent import NexoraAgent


def test_agent_role_detection_and_prompting():

    agent = NexoraAgent()
    prompt = agent.build_prompt(
        "Act as the Data Agent. Analyze datasets and generate insights."
    )

    assert "Data Agent" in prompt
    assert "Analyze datasets and generate insights" in prompt
    assert "NEXORA, a personal AI intelligence system." in prompt


def test_database():

    init_db()

    manager = MemoryManager()

    memory_id = manager.add(
        "NEXORA test memory",
        "test"
    )

    assert memory_id > 0


def test_search():

    manager = MemoryManager()

    manager.add(
        "Python is useful for AI",
        "learning"
    )

    results = manager.search_keyword(
        "Python"
    )

    assert len(results) >= 1


def test_memory_api_crud_and_search(tmp_path, monkeypatch):

    import app.database as database

    monkeypatch.setattr(
        database,
        "DB_PATH",
        tmp_path / "memory-api.db",
    )

    from fastapi.testclient import TestClient
    from app.api import app

    with TestClient(app) as client:
        created = client.post(
            "/memory",
            json={"content": "NEXORA persistent memory", "category": "test"},
        )

        assert created.status_code == 200
        memory_id = created.json()["id"]

        assert any(
            memory["id"] == memory_id
            for memory in client.get("/memory").json()
        )
        assert [
            memory["id"]
            for memory in client.get(
                "/memory/search",
                params={"q": "persistent"},
            ).json()
        ] == [memory_id]
        assert client.delete(f"/memory/{memory_id}").status_code == 200
        assert client.get("/memory").json() == []
        assert client.delete(f"/memory/{memory_id}").status_code == 404


def test_backend_tool_endpoints(tmp_path, monkeypatch):

    import app.database as database

    monkeypatch.setattr(
        database,
        "DB_PATH",
        tmp_path / "tools-api.db",
    )
    database.init_db()
    from fastapi.testclient import TestClient
    from app.api import app
    from app.llm import llm

    monkeypatch.setattr(llm, "available", lambda: False)
    monkeypatch.setenv(
        "NEXORA_OTP_SECRET",
        "test-only-otp-signing-secret-32-bytes-minimum",
    )
    monkeypatch.setenv(
        "NEXORA_SECRET_KEY",
        "test-only-jwt-signing-secret-32-bytes-minimum",
    )
    from app.auth import routes as auth_routes

    sent_codes = []
    monkeypatch.setattr(
        auth_routes,
        "_deliver_code",
        lambda email, phone, code: sent_codes.append((email, phone, code)),
    )

    with TestClient(app) as client:
        user = {
            "username": "tools-test-user",
            "email": "tools-test@example.test",
            "password": "temporary-test-password",
            "phone_number": "+14155550123",
        }
        registered = client.post("/auth/register", json=user)
        assert registered.status_code == 200
        assert sent_codes[0][0] == user["email"]
        assert sent_codes[0][1] == user["phone_number"]

        assert client.post(
            "/auth/login",
            json={"email": user["email"], "password": user["password"]},
        ).status_code == 401
        wrong_code = "000000" if sent_codes[0][2] != "000000" else "000001"
        assert client.post(
            "/auth/register/verify",
            json={"email": user["email"], "code": wrong_code},
        ).status_code == 400

        verified = client.post(
            "/auth/register/verify",
            json={"email": user["email"], "code": sent_codes[0][2]},
        )
        assert verified.status_code == 200
        assert verified.json()["access_token"]

        logged_in = client.post(
            "/auth/login",
            json={"email": user["email"], "password": user["password"]},
        )
        assert logged_in.status_code == 200

        task = client.post(
            "/tasks",
            json={"title": "Persistent backend task"},
        )
        assert task.status_code == 200
        task_id = task.json()["id"]

        results = client.get("/search", params={"q": "persistent"})
        assert [item["id"] for item in results.json()["tasks"]] == [task_id]

        completed = client.patch(
            f"/tasks/{task_id}",
            json={"status": "completed"},
        )
        assert completed.json()["status"] == "completed"

        pending = client.patch(
            f"/tasks/{task_id}",
            json={"status": "pending"},
        )
        assert pending.json()["status"] == "pending"

        assert client.delete(f"/tasks/{task_id}").status_code == 200
        assert client.delete(f"/tasks/{task_id}").status_code == 404

        chat = client.post("/chat", json={"message": "history check"})
        assert chat.status_code == 200
        history = client.get("/chat/history").json()
        assert [item["role"] for item in history[-2:]] == ["user", "assistant"]


def test_registration_otp_attempts_expiry_and_resend(tmp_path, monkeypatch):

    from datetime import datetime, timedelta, timezone

    import app.database as database

    monkeypatch.setattr(database, "DB_PATH", tmp_path / "otp-limits.db")
    database.init_db()
    monkeypatch.setenv(
        "NEXORA_OTP_SECRET",
        "test-only-otp-signing-secret-32-bytes-minimum",
    )
    monkeypatch.setenv(
        "NEXORA_SECRET_KEY",
        "test-only-jwt-signing-secret-32-bytes-minimum",
    )

    from fastapi.testclient import TestClient
    from app.api import app
    from app.auth import routes as auth_routes

    sent_codes = []
    monkeypatch.setattr(
        auth_routes,
        "_deliver_code",
        lambda email, phone, code: sent_codes.append((email, phone, code)),
    )

    with TestClient(app) as client:
        registration = {
            "username": "otp-limits-user",
            "email": "otp-limits@example.test",
            "password": "temporary-test-password",
            "phone_number": "+14155550123",
        }
        assert client.post("/auth/register", json=registration).status_code == 200

        sent_code = sent_codes[-1][2]
        wrong_code = "000000" if sent_code != "000000" else "000001"
        for _ in range(5):
            assert client.post(
                "/auth/register/verify",
                json={"email": registration["email"], "code": wrong_code},
            ).status_code == 400

        assert client.post(
            "/auth/register/verify",
            json={"email": registration["email"], "code": sent_code},
        ).status_code == 429
        assert client.post(
            "/auth/register/resend",
            json={"email": registration["email"]},
        ).status_code == 429

        with database.get_db() as db:
            db.execute(
                "UPDATE registration_challenges SET created_at = ? WHERE email = ?",
                (
                    (datetime.now(timezone.utc) - timedelta(seconds=61)).isoformat(),
                    registration["email"],
                ),
            )
            db.commit()

        assert client.post(
            "/auth/register/resend",
            json={"email": registration["email"]},
        ).status_code == 200
        assert client.post(
            "/auth/register/verify",
            json={"email": registration["email"], "code": sent_codes[-1][2]},
        ).status_code == 200

        expiring_registration = {
            **registration,
            "username": "otp-expiry-user",
            "email": "otp-expiry@example.test",
        }
        assert client.post(
            "/auth/register",
            json=expiring_registration,
        ).status_code == 200

        with database.get_db() as db:
            db.execute(
                "UPDATE registration_challenges SET expires_at = ? WHERE email = ?",
                (
                    (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
                    expiring_registration["email"],
                ),
            )
            db.commit()

        expired = client.post(
            "/auth/register/verify",
            json={
                "email": expiring_registration["email"],
                "code": sent_codes[-1][2],
            },
        )
        assert expired.status_code == 400
        assert client.post(
            "/auth/login",
            json={
                "email": expiring_registration["email"],
                "password": expiring_registration["password"],
            },
        ).status_code == 401


def test_registration_fails_closed_when_delivery_is_unavailable(
    tmp_path,
    monkeypatch,
):

    import app.database as database

    monkeypatch.setattr(database, "DB_PATH", tmp_path / "otp-delivery.db")
    database.init_db()
    monkeypatch.setenv(
        "NEXORA_OTP_SECRET",
        "test-only-otp-signing-secret-32-bytes-minimum",
    )
    monkeypatch.setenv(
        "NEXORA_SECRET_KEY",
        "test-only-jwt-signing-secret-32-bytes-minimum",
    )

    from fastapi.testclient import TestClient
    from app.api import app
    from app.auth import routes as auth_routes

    monkeypatch.setattr(
        auth_routes,
        "_deliver_code",
        lambda email, phone, code: (_ for _ in ()).throw(RuntimeError("offline")),
    )

    with TestClient(app) as client:
        response = client.post(
            "/auth/register",
            json={
                "username": "delivery-user",
                "email": "delivery@example.test",
                "password": "temporary-test-password",
                "phone_number": "+14155550123",
            },
        )
        assert response.status_code == 503

    with database.get_db() as db:
        assert db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
        assert db.execute(
            "SELECT COUNT(*) FROM registration_challenges"
        ).fetchone()[0] == 0


def test_otp_delivery_adapters_send_to_both_channels(monkeypatch):

    import requests

    from app.auth import routes as auth_routes

    monkeypatch.setenv("NEXORA_SMTP_HOST", "smtp.example.test")
    monkeypatch.setenv("NEXORA_SMTP_PORT", "587")
    monkeypatch.setenv("NEXORA_SMTP_USERNAME", "smtp-user")
    monkeypatch.setenv("NEXORA_SMTP_PASSWORD", "smtp-password")
    monkeypatch.setenv("NEXORA_SMTP_FROM", "noreply@example.test")
    monkeypatch.setenv("NEXORA_SMTP_USE_SSL", "false")
    monkeypatch.setenv("NEXORA_TWILIO_ACCOUNT_SID", "account-sid")
    monkeypatch.setenv("NEXORA_TWILIO_AUTH_TOKEN", "auth-token")
    monkeypatch.setenv("NEXORA_TWILIO_FROM", "+14155550000")

    emails = []
    sms_requests = []

    class FakeSMTP:

        def __init__(self, host, port, timeout):
            assert (host, port, timeout) == ("smtp.example.test", 587, 10)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self):
            pass

        def login(self, username, password):
            assert (username, password) == ("smtp-user", "smtp-password")

        def send_message(self, message):
            emails.append(message)

    class FakeResponse:

        def raise_for_status(self):
            pass

    def fake_post(url, **kwargs):
        sms_requests.append((url, kwargs))
        return FakeResponse()

    monkeypatch.setattr(auth_routes.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(requests, "post", fake_post)

    auth_routes._deliver_code(
        "user@example.test",
        "+14155550123",
        "123456",
    )

    assert emails[0]["To"] == "user@example.test"
    assert "123456" in emails[0].get_content()
    sms_url, sms_request = sms_requests[0]
    assert sms_url.endswith("/Accounts/account-sid/Messages.json")
    assert sms_request["data"]["To"] == "+14155550123"
    assert "123456" in sms_request["data"]["Body"]
    assert sms_request["auth"] == ("account-sid", "auth-token")


def test_registration_fails_before_delivery_without_signing_key(
    tmp_path,
    monkeypatch,
):

    import app.database as database

    monkeypatch.setattr(database, "DB_PATH", tmp_path / "otp-signing.db")
    database.init_db()
    monkeypatch.setenv(
        "NEXORA_OTP_SECRET",
        "test-only-otp-signing-secret-32-bytes-minimum",
    )
    monkeypatch.delenv("NEXORA_SECRET_KEY", raising=False)

    from fastapi.testclient import TestClient
    from app.api import app
    from app.auth import routes as auth_routes

    delivery_calls = []
    monkeypatch.setattr(
        auth_routes,
        "_deliver_code",
        lambda *args: delivery_calls.append(args),
    )

    with TestClient(app) as client:
        response = client.post(
            "/auth/register",
            json={
                "username": "unconfigured-user",
                "email": "unconfigured@example.test",
                "password": "temporary-test-password",
                "phone_number": "+14155550123",
            },
        )
        assert response.status_code == 503

    assert delivery_calls == []
    with database.get_db() as db:
        assert db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
        assert db.execute(
            "SELECT COUNT(*) FROM registration_challenges"
        ).fetchone()[0] == 0