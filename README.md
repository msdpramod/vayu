# Vayu

Vayu is a Jarvis-style personal assistant backend MVP focused on safe, allow-listed command execution.

## What works now

- FastAPI backend
- `GET /` service status
- `GET /health` health check
- `POST /command` command API
- Safe allow-listed commands: `hello`, `hi`, `status`, `health`, `time`, `what time is it`
- Explicit blocking for destructive, financial, credential, and security-sensitive commands
- Automated tests
- Docker image + Docker Compose
- GitHub Actions CI

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:

- http://localhost:8000/
- http://localhost:8000/docs
- http://localhost:8000/health

Try:

```bash
curl -X POST http://localhost:8000/command \
  -H 'Content-Type: application/json' \
  -d '{"command":"hello"}'
```

## Docker

```bash
docker compose up --build
```

## Architecture direction

Next milestones:

1. LLM reasoning/provider abstraction
2. Voice input/output (STT/TTS)
3. Skill registry
4. Desktop agent
5. Browser control
6. Calendar/email integrations
7. Smart-home integrations
8. Permission and confirmation engine
9. Long-term memory
10. Mobile/web UI

The assistant should never execute arbitrary shell commands directly. Every capability should be an explicit skill with scoped permissions and confirmation rules.
