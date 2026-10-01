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
| `application/` | Use cases: commands (write) and queries (read), transaction boundaries | `domain/` | Not built yet |
| `infrastructure/` | Persistence (ORM, mappers, repository implementations, migrations, DB connection) and the dictionary adapter | `domain/`, the `shodoukan` library | Built: [schema](infrastructure/database-schema.md), [ORM and mappers](infrastructure/orm-and-mappers.md), [repositories](infrastructure/repositories.md), [migrations](infrastructure/migrations.md), [dictionary gateway](infrastructure/dictionary-gateway.md) |
| `api/` | FastAPI routes, request/response schemas, dependency wiring (`deps.py`) | `application/`, and `infrastructure/` for wiring only | Not built yet |

`infrastructure/` implements the ports defined in `domain/`. `api/deps.py` will open
one `Session` per request, build the concrete repositories, hand them to use cases and
commit at the end (see [repositories](infrastructure/repositories.md#transactions)).

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
      services/                       *_service.py, pure business rules
    application/                      (scaffold)
    infrastructure/
      db/connection.py
      db/orm/                         *_orm.py + base_orm.py
      db/mappers/                     *_mapper.py
      db/migrations/                  env.py, script.py.mako, versions/
      repositories/                   sqlalchemy_*_repository.py
      dictionary/                     shodoukan gateway + anti-corruption mapper
    api/                              (scaffold) app.py, deps.py, routes/, schemas/
```

Module names follow `<subject>_<role>.py`; packages are plural and classes singular.
See the Naming section of the backend skill.

## Relationship with the dictionary

The practice app uses the `shodoukan` library **in-process**, behind the
`DictionaryGateway` port, just as `shodoukan-api` uses it. It reads the dictionary
only when importing. An imported entry or kanji is a snapshot stored in the practice
database, and the only link back is `source_entry_id` (shodoukan `Entry.id`) or
`literal` (shodoukan `Kanji.literal`). See the
[dictionary gateway](infrastructure/dictionary-gateway.md) and
[entities](domain/entities.md#snapshot-and-practice-state).
