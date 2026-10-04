# Shodoukan — Documentation Index

Japanese-English dictionary platform built on JMDict and KANJIDIC2. See the [README](../README.md) for setup and deployment.

---

## Functional documentation

For understanding what the platform does and how to use it.

| Doc | Description |
|---|---|
| [functional/search.md](functional/search.md) | What users can search for, how queries work, how to interpret results |
| [functional/web.md](functional/web.md) | The web interface: search bar, results layout, badges, language switching |
| [functional/api.md](functional/api.md) | How to use the REST API as a consumer: common flows with examples |

## Technical documentation

For developers building, extending, or debugging the platform.

| Doc | Description |
|---|---|
| [technical/api.md](technical/api.md) | Full REST API reference: all endpoints, parameters, response schemas |
| [technical/search.md](technical/search.md) | Search architecture: query classification, entry/kanji pipelines, scoring formulas |
| [technical/frontend.md](technical/frontend.md) | Frontend architecture: components, responsive layout conventions, Tailwind patterns, debug mode |

## Practice app

The practice app (`shodoukan-practice`) has its own documentation tree.

| Doc | Description |
|---|---|
| [practice/README.md](practice/README.md) | Overview, status, and links to everything below |
| [practice/functional/README.md](practice/functional/README.md) | What the app does, per feature (written as use cases are defined) |
| [practice/technical/README.md](practice/technical/README.md) | Architecture, domain, persistence, dates, configuration, testing, design decisions |
| [practice/technical/exercises.md](practice/technical/exercises.md) | Exercises design: types, fields and directions, distractor rule, sessions and statistics, phases |
