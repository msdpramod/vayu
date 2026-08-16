# Ollama Planner

Vayu can use a local Ollama model as its planning component without granting that model execution authority.

## Enable it

```bash
export VAYU_PLANNER_PROVIDER=ollama
export VAYU_OLLAMA_URL=http://127.0.0.1:11434
export VAYU_OLLAMA_MODEL=llama3.2
export VAYU_OLLAMA_TIMEOUT_SECONDS=8
uvicorn app.main:app --reload
```

The default planner remains `local`, so Vayu still runs without Ollama.

## Safety boundary

The Ollama provider can only return a structured planner decision. It never receives an executor, approval token, shell, filesystem, browser, email, calendar, or notification capability.

Planner-created actions must:

- use one of `calendar.create`, `email.send`, or `notification.send`;
- include a non-empty description;
- use an object payload;
- retain risk `confirm`;
- enter the durable `pending_approval` state before any later execution step.

Unexpected action fields are rejected. Unknown tools such as `shell.exec` are rejected by the planner service even if a model emits them. Transport failures and malformed model output create no action. `/plan` returns HTTP 503 when the configured provider is unavailable.

## Request example

```bash
curl -X POST http://localhost:8000/plan \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Prepare a notification telling me the Vayu build finished"}'
```

A successful model response may create a proposal, but that proposal is not approved or executed automatically. A human must use the separate action approval flow, and execution still requires an explicitly registered allow-listed adapter.

This keeps the useful local-intelligence pattern aligned with KUPPA AI while preserving Vayu as an independently deployable system.
