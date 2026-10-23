# Architecture

[← Technical documentation](README.md)

Layers, what each may depend on, and where the code lives.

## Layers

Clean architecture with dependency inversion. Dependencies point inwards:

```
api/ ──► application/ ──► domain/ ◄── infrastructure/
(FastAPI)  (use cases)     (entities,     (ORM, mappers,
                            ports, rules)  SQLAlchemy repos, Alembic)
```

| Layer | Responsibility | May import | Status |
|---|---|---|---|
| `domain/` | Entities, business rules, repository ports (Protocols) | Only itself (and Pydantic) | Built: [entities](domain/entities.md), [ports](domain/repository-ports.md), [services](domain/services-and-errors.md) |
| `application/` | Use cases: commands (write) and queries (read) | `domain/` | Built: [use cases](application/use-cases.md) |
| `infrastructure/` | Persistence (ORM, mappers, repository implementations, migrations, DB connection) and the dictionary adapter | `domain/`, the `shodoukan` library | Built: [schema](infrastructure/database-schema.md), [ORM and mappers](infrastructure/orm-and-mappers.md), [repositories](infrastructure/repositories.md), [migrations](infrastructure/migrations.md), [dictionary gateway](infrastructure/dictionary-gateway.md) |
| `api/` | FastAPI routes, request/response schemas, authentication, dependency wiring (`deps.py`), commit per request | `application/`, and `infrastructure/` for wiring only | Built: [endpoints](api/endpoints.md), [authentication](api/authentication.md) |

`infrastructure/` implements the ports defined in `domain/`. `api/deps.py` opens one
`Session` per request, builds the concrete repositories and the dictionary gateway,
and hands them to use cases. The route commits after the use case succeeds (see
[endpoints](api/endpoints.md#transactions)).

## Package map

```
packages/shodoukan-practice/
  alembic.ini
  src/shodoukan_practice/
    domain/
      clock.py                        utc_now()
      exceptions.py
      entities/                       *_entity.py, one module per aggregate
      repositories/                   *_repository.py, Protocol ports
      gateways/                       *_gateway.py, ports to external sources
      searches/                       library_search.py: search criteria, scopes, tiers
      services/                       *_service.py, pure business rules
    application/
      commands/                       *_commands.py, write use cases
      queries/                        *_queries.py, read use cases
    infrastructure/
      db/connection.py
      db/orm/                         *_orm.py + base_orm.py
      db/mappers/                     *_mapper.py
      db/migrations/                  env.py, script.py.mako, versions/
      repositories/                   sqlalchemy_*_repository.py (+ sqlalchemy_library_search.py)
      dictionary/                     shodoukan gateway + anti-corruption mapper
    api/
      app.py                          FastAPI app, domain error → HTTP mapping
      auth.py                         TokenVerifier (Keycloak, RS256 via JWKS)
      deps.py                         wiring: session, verifier, current user, use cases
      routes/                         *_routes.py
      schemas/                        *_schemas.py, request/response models
```

Module names follow `<subject>_<role>.py`; packages are plural and classes singular.
See the Naming section of the backend skill.

## Relationship with the dictionary

The practice app uses the `shodoukan` library **in-process**, behind the
`DictionaryGateway` port, just as `shodoukan-api` uses it. It reads the dictionary to
search (`GET /dictionary/search`), to import, and to build handwriting questions
(which kanji have a stroke order, and their strokes; see
[decisions](decisions.md#handwriting-questions-read-the-dictionary-when-theyre-asked)). The two apps are standalone and
don't call each other. An imported entry or kanji is a snapshot stored in the practice
database, and the only link back is `source_entry_id` (shodoukan `Entry.id`) or
`literal` (shodoukan `Kanji.literal`). See the
[dictionary gateway](infrastructure/dictionary-gateway.md) and
[entities](domain/entities.md#snapshot-and-practice-state).
