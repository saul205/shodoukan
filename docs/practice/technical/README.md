# Practice App — Technical Documentation

[← Practice app](../README.md)

For developers and agents working on `shodoukan-practice`. It describes what is built
and why. Coding conventions (naming, typing, testing style) live in the backend skill,
[`.claude/skills/python-backend-clean-code/SKILL.md`](../../../.claude/skills/python-backend-clean-code/SKILL.md).

## Contents

- [Architecture](architecture.md): layers, dependency rule, package map, status.
- [Design decisions](decisions.md): why things are the way they are.
- Application
  - [Use cases](application/use-cases.md): what each command and query does.
- API
  - [Endpoints](api/endpoints.md): routes, schemas, status codes, transactions, wiring.
  - [Authentication](api/authentication.md): Keycloak bearer tokens, 401 vs 403.
- Domain
  - [Entities](domain/entities.md): aggregates, practice state, timestamps.
  - [Repository ports](domain/repository-ports.md): the persistence contracts.
  - [Services and errors](domain/services-and-errors.md): domain rules, exceptions, clock.
- Infrastructure
  - [Database schema](infrastructure/database-schema.md): tables, constraints, cascades.
  - [ORM and mappers](infrastructure/orm-and-mappers.md): SQLAlchemy models and domain ↔ row mapping.
  - [Repositories](infrastructure/repositories.md): the SQLAlchemy implementations.
  - [Migrations](infrastructure/migrations.md): Alembic setup and workflow.
  - [Dictionary gateway](infrastructure/dictionary-gateway.md): reading the shodoukan dictionary and mapping it to practice entities.
- Cross-cutting
  - [Dates and time zones](cross-cutting/dates-and-time-zones.md)
  - [Configuration and local setup](cross-cutting/configuration.md)
- [Testing](testing.md)

## Where to document what

Technical docs are updated **in the same change** as the code. Use this table to find
the page to update:

| When you change… | Update |
|---|---|
| A layer, a package folder, or what a layer may import | [architecture.md](architecture.md) |
| A non-obvious design choice, or a reversed one | [decisions.md](decisions.md) (add an entry) |
| `domain/entities/` | [domain/entities.md](domain/entities.md) |
| `domain/repositories/`, `domain/gateways/` | [domain/repository-ports.md](domain/repository-ports.md) |
| `domain/services/`, `domain/exceptions.py`, `domain/clock.py` | [domain/services-and-errors.md](domain/services-and-errors.md) |
| Tables, columns, constraints (`infrastructure/db/orm/`) | [infrastructure/database-schema.md](infrastructure/database-schema.md) and [infrastructure/orm-and-mappers.md](infrastructure/orm-and-mappers.md) |
| `infrastructure/db/mappers/` | [infrastructure/orm-and-mappers.md](infrastructure/orm-and-mappers.md) |
| `infrastructure/repositories/` | [infrastructure/repositories.md](infrastructure/repositories.md) |
| Alembic config or workflow | [infrastructure/migrations.md](infrastructure/migrations.md) |
| `infrastructure/dictionary/`, dictionary wiring in `api/deps.py` | [infrastructure/dictionary-gateway.md](infrastructure/dictionary-gateway.md) |
| Date handling | [cross-cutting/dates-and-time-zones.md](cross-cutting/dates-and-time-zones.md) |
| Environment variables, docker compose, `connection.py` | [cross-cutting/configuration.md](cross-cutting/configuration.md) |
| Test fixtures, factories, CI | [testing.md](testing.md) |
| `application/` (commands, queries) | [application/use-cases.md](application/use-cases.md) |
| `api/routes/`, `api/schemas/`, `api/app.py`, `api/deps.py` | [api/endpoints.md](api/endpoints.md) |
| `api/auth.py`, `get_current_user` | [api/authentication.md](api/authentication.md) |
| A new layer or area | Add a folder here, link it above and in this table |
