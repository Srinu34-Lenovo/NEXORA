# NEXORA

Personal AI Intelligence OS.

## Features

- Persistent memory and keyword search
- SQLite-backed tasks and conversations
- FastAPI backend with registration and login
- Email and SMS registration verification
- Local LLM and agent integration
- Automated tests

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Before starting the API, replace both secret placeholders in `.env` with
different random values of at least 32 characters. For example, run this twice
and place each result in the corresponding variable:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Set up **both** code-delivery providers for registration verification:

- SMTP: `NEXORA_SMTP_HOST`, `NEXORA_SMTP_PORT`, `NEXORA_SMTP_FROM`, and provider
	credentials when required. Port 587 uses STARTTLS; set
	`NEXORA_SMTP_USE_SSL=true` for implicit TLS.
- Twilio: `NEXORA_TWILIO_ACCOUNT_SID`, `NEXORA_TWILIO_AUTH_TOKEN`, and
	`NEXORA_TWILIO_FROM`.

Registration sends the same six-digit code to both the supplied email and
E.164-format phone number. Codes expire after 10 minutes, allow five attempts,
and can be resent after a 60-second cooldown. An account is not created until
the code is verified. If either delivery provider or either required secret is
missing, registration fails closed; codes are never returned by the API.

Keep `.env` private and do not commit real provider credentials.

## Run

```powershell
python -m uvicorn app.api:app --reload
```

The API documentation is available at `http://127.0.0.1:8000/docs`.

## Tests

```powershell
python -m pytest -q
```