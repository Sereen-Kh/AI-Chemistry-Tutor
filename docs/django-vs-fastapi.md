# Django vs FastAPI — Team Decision Reference

## Core Philosophy

| | Django | FastAPI |
|---|---|---|
| Type | Full-stack web framework | API-focused micro-framework |
| Approach | "Batteries included" — gives you everything built-in | "Bring your own" — minimal core, you add what you need |
| Age | 2005 — very mature | 2018 — modern, built on current Python standards |
| Best for | Content-heavy apps, admin panels, monoliths | APIs, AI/ML services, async workloads |

---

## Authentication — Both support it, differently

> **Common misconception:** people think only Django does auth. Both frameworks fully support authentication — the difference is how much is built-in vs. how much you write yourself.

### Django Auth
- Built-in user model, sessions, password hashing, login/logout, permissions, groups — all zero setup
- Add `djangorestframework-simplejwt` → JWT tokens in minutes
- Free admin panel at `/admin` to manage users with no code

### FastAPI Auth
- No built-in user system, but has built-in OAuth2/JWT helpers (`OAuth2PasswordBearer`, `HTTPBearer`)
- You write the user model, hashing, and token logic yourself
- More control, slightly more upfront code — but fully capable

---

## Feature-by-Feature Comparison

| Feature | Django | FastAPI |
|---|---|---|
| **Authentication** | Built-in (full system) | Built-in helpers (you assemble it) |
| **Admin panel** | ✅ Free at `/admin` | ❌ Not included |
| **ORM** | ✅ Built-in Django ORM | ❌ Bring your own (SQLAlchemy) |
| **Migrations** | ✅ `makemigrations` built-in | ❌ Use Alembic separately |
| **API docs** | Via DRF extensions only | ✅ Auto Swagger at `/docs` + ReDoc at `/redoc` |
| **Async support** | Partial (added later, incomplete) | ✅ Native `async/await` from day one |
| **Performance** | Good | Faster (one of the fastest Python frameworks) |
| **Type safety** | Limited | ✅ Pydantic models — full validation + auto docs |
| **WebSockets** | Limited | ✅ Native support |
| **Learning curve** | Higher upfront (more conventions) | Lower upfront (more freedom) |
| **Ecosystem maturity** | 20 years — massive | 7 years — growing fast |

---

## Why people prefer Django

1. **Admin panel** — Full UI to manage database records for free. For content-heavy apps this alone saves weeks of work.
2. **Everything in one place** — Auth, ORM, migrations, templating, forms — one install, one config.
3. **Strong conventions** — Large teams write code the same way. Less decision fatigue.
4. **Battle-tested at scale** — Instagram, Pinterest, Disqus run on Django.
5. **Easier onboarding** — New team members follow the framework's conventions immediately.

## Why people prefer FastAPI

1. **Async-native** — LLM/AI API calls don't block other requests. Django's async is incomplete.
2. **Auto API documentation** — Swagger UI and ReDoc generated automatically from your code at zero cost.
3. **Type safety** — Pydantic validates every request and response automatically.
4. **Performance** — Comparable to Node.js and Go for I/O-bound workloads.
5. **Lightweight** — Only what you need. No unused admin panel or template engine overhead.
6. **Modern Python** — Designed around Python 3.6+ type hints.

---

## Why We Chose FastAPI for This Project

| Our Requirement | Why FastAPI wins |
|---|---|
| AI / LLM API calls | Async — calls don't block other users |
| Flutter as the only client | No templates needed — pure JSON API |
| JWT authentication | Built-in `HTTPBearer` helpers — already implemented |
| Team wants API docs | Auto Swagger at `/docs` — free, always up to date |
| Chatbot feature (future) | Native WebSocket support |
| Simple user model | We only need register / login / me — Django's full auth system is overkill |

---

## One-Line Summary

> **Django** is a full city — roads, buildings, and utilities all provided.
> **FastAPI** is an empty plot of land with high-quality tools — you build exactly what you need, nothing more.
>
> For a Flutter app with AI features: **FastAPI is the right choice.**

---

## Current Stack Decision Log

| Layer | Decision | Status |
|---|---|---|
| Backend framework | **FastAPI** | ✅ Decided |
| Database (dev) | SQLite (auto-created) | ✅ In use |
| Database (prod) | PostgreSQL (swap `DATABASE_URL`) | ⏳ TBD |
| Flutter state management | Provider (chatbot MVP) | ⏳ Team to finalize |
| AI provider | OpenAI / Gemini / local | ⏳ TBD |
