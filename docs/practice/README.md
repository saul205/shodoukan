# Practice App

`shodoukan-practice` lets each user build a personal study library from the shodoukan
dictionary, adapt it to how they study, group it into collections and practise with
exercises built from those collections.

## Status

| Part | State |
|---|---|
| Domain (entities, rules, repository ports) | Built |
| Persistence (PostgreSQL, Alembic, mappers, repositories) | Built |
| Dictionary integration (in-process `shodoukan` library) | Built |
| Application use cases | Import an entry or kanji; browse and customise the library; manage collections and their items; dictionary entry and kanji details |
| Sign-in (Keycloak, OAuth2 / OpenID Connect) | Built: local Keycloak with the `shodoukan` realm; practice users created on first request |
| HTTP API | `GET /dictionary/search` (public), `GET /users/me`, `GET`/`POST /library/entries`, `GET`/`POST /library/kanji`, `GET /library/imported`, `/collections/entries` and `/collections/kanji` |
| Frontend (`shodoukan-practice-web`) | Built: Keycloak sign-in, dictionary, library with customisation, collections; see [frontend](technical/frontend.md) |
| Exercises | Designed ([design](technical/exercises.md)); exercise definitions (`/exercises`) and sessions (`/exercise-sessions`) built; frontend and history to come |

## Documentation

- [Functional documentation](functional/README.md): what the app does, per feature.
  Written as use cases are defined.
- [Technical documentation](technical/README.md): architecture, layers, domain,
  persistence, conventions. Kept up to date with the code.

Package: [`packages/shodoukan-practice`](../../packages/shodoukan-practice/). Tests:
[`tests/shodoukan-practice`](../../tests/shodoukan-practice/). Back to the
[documentation index](../index.md).
