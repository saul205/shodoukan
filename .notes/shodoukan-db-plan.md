# shodoukan-db — Plan de optimizaciones de schema

> Plan de implementación para el pipeline Rust (XML → dominio → SQLite).
> Ver `optimization_db.md` para el contexto completo y el impacto en el lado Python.

---

## Contexto

El pipeline actual procesa JMDict y KANJIDIC2 y produce un SQLite que se publica
como asset de release mensual. El objetivo de estas tareas es pre-calcular en tiempo
de ingesta valores que actualmente se computan en cada búsqueda, eliminando subqueries
correlacionadas y operaciones sobre JSON en el lado Python.

La carga es: **XML → structs de dominio → INSERT en SQLite**.
Los cambios viven todos en la fase dominio → SQLite.

---

## Tarea 1 — `senses.sense_index` *(prioridad alta)*

### Cambio de schema

Añadir columna `sense_index INTEGER NOT NULL` a la tabla `senses`.

```sql
CREATE TABLE senses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id    INTEGER NOT NULL REFERENCES entries(id),
    sense_index INTEGER NOT NULL,
    pos         TEXT    NOT NULL DEFAULT '[]',
    misc        TEXT    NOT NULL DEFAULT '[]',
    dialects    TEXT    NOT NULL DEFAULT '[]',
    info        TEXT    NOT NULL DEFAULT '[]'
);
```

### Cambio en el pipeline

Al insertar los senses de una entry, usar el índice del iterador como `sense_index`.
No requiere ningún cálculo extra — es la posición natural en el Vec.

```rust
for (index, sense) in entry.senses.iter().enumerate() {
    db.execute(
        "INSERT INTO senses (entry_id, sense_index, pos, misc, dialects, info)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
        params![
            entry.id,
            index as i32,
            serde_json::to_string(&sense.pos)?,
            serde_json::to_string(&sense.misc)?,
            serde_json::to_string(&sense.dialects)?,
            serde_json::to_string(&sense.info)?,
        ],
    )?;
}
```

### Impacto en Python

Elimina la subquery correlacionada `_sense_pos_sq` en `search_by_gloss`.
`func.min(SenseORM.sense_index)` es una columna directa en el JOIN existente.

---

## Tarea 2 — `entries.freq_score` y `entries.has_common` *(prioridad alta)*

### Cambio de schema

Añadir dos columnas a `entries`:

```sql
CREATE TABLE entries (
    id         INTEGER PRIMARY KEY,
    jlpt       INTEGER,
    freq_score INTEGER NOT NULL DEFAULT 0,
    has_common INTEGER NOT NULL DEFAULT 0
);
```

### Lógica de cálculo

Los pesos actuales de `shodoukan/scoring.py` que hay que replicar:

| Tag | Puntos |
|-----|--------|
| `ichi1`, `spec1`, `news1`, `gai1` | 10 pts cada uno (Tier 1) |
| `ichi2`, `spec2`, `news2`, `gai2` | 5 pts cada uno (Tier 2) |
| Al menos un tag Tier 1 en cualquier reading | +500 pts (bonus `has_common`) |

`freq_score` = bonus `has_common` + max(`per_tag_score` de kanji_readings) + max(`per_tag_score` de readings)

```rust
const TIER1: &[&str] = &["ichi1", "spec1", "news1", "gai1"];
const TIER2: &[&str] = &["ichi2", "spec2", "news2", "gai2"];

fn per_tag_score(tags: &[String]) -> i32 {
    let t1 = TIER1.iter().filter(|&&t| tags.iter().any(|p| p == t)).count() as i32;
    let t2 = TIER2.iter().filter(|&&t| tags.iter().any(|p| p == t)).count() as i32;
    t1 * 10 + t2 * 5
}

fn compute_freq_score(entry: &Entry) -> (i32, bool) {
    let has_common = entry.kanji_readings.iter()
        .any(|kr| TIER1.iter().any(|&t| kr.priority.iter().any(|p| p == t)))
        || entry.readings.iter()
        .any(|r| TIER1.iter().any(|&t| r.priority.iter().any(|p| p == t)));

    let bonus = if has_common { 500 } else { 0 };

    let max_kanji = entry.kanji_readings.iter()
        .map(|kr| per_tag_score(&kr.priority))
        .max()
        .unwrap_or(0);

    let max_reading = entry.readings.iter()
        .map(|r| per_tag_score(&r.priority))
        .max()
        .unwrap_or(0);

    (bonus + max_kanji + max_reading, has_common)
}
```

### Cambio en el pipeline

Calcular antes del INSERT de la entry y pasar como parámetro:

```rust
let (freq_score, has_common) = compute_freq_score(&entry);

db.execute(
    "INSERT INTO entries (id, jlpt, freq_score, has_common) VALUES (?1, ?2, ?3, ?4)",
    params![entry.id, entry.jlpt, freq_score, has_common as i32],
)?;
```

> **Nota de mantenimiento:** si los pesos de scoring cambian en `shodoukan/scoring.py`,
> actualizar `TIER1`, `TIER2` y los multiplicadores en este módulo también.
> Añadir un comentario en ambos lados con referencia cruzada.

### Impacto en Python

- `search_by_japanese`: elimina `per_tag_score` y `common_word_bonus` del SELECT
- `search_by_gloss`: elimina además los dos `outerjoin` con `kanji_readings` y `readings`
- `scoring.py` se puede deprecar cuando se complete la migración

---

## Tarea 3 — Tabla `entry_sense_counts` *(prioridad media)*

### Cambio de schema

Nueva tabla auxiliar:

```sql
CREATE TABLE entry_sense_counts (
    entry_id INTEGER NOT NULL REFERENCES entries(id),
    lang     TEXT    NOT NULL,
    count    INTEGER NOT NULL,
    PRIMARY KEY (entry_id, lang)
);
CREATE INDEX idx_entry_sense_counts_entry ON entry_sense_counts(entry_id);
```

### Lógica de cálculo

Para cada entry, contar los senses distintos que tienen al menos un gloss en cada idioma.
Un sense con 3 glosses en inglés cuenta como 1, no como 3.

```rust
use std::collections::{HashMap, HashSet};

fn count_senses_by_lang(entry: &Entry) -> HashMap<String, usize> {
    let mut lang_senses: HashMap<String, HashSet<u64>> = HashMap::new();
    for (sense_idx, sense) in entry.senses.iter().enumerate() {
        for gloss in &sense.glosses {
            lang_senses
                .entry(gloss.lang.clone())
                .or_default()
                .insert(sense_idx as u64);
        }
    }
    lang_senses.into_iter().map(|(lang, ids)| (lang, ids.len())).collect()
}
```

### Cambio en el pipeline

Insertar después de procesar todos los senses de la entry:

```rust
let sense_counts = count_senses_by_lang(&entry);
for (lang, count) in &sense_counts {
    db.execute(
        "INSERT INTO entry_sense_counts (entry_id, lang, count) VALUES (?1, ?2, ?3)",
        params![entry.id, lang, *count as i32],
    )?;
}
```

### Impacto en Python

Elimina la subquery correlacionada `_sense_total_sq` en `search_by_gloss`.
`EntrySenseLangCountORM.count` es una columna directa en un JOIN normal.

---

## Tarea 6 — Scores por reading individual *(opcional)*

```sql
ALTER TABLE kanji_readings ADD COLUMN score INTEGER NOT NULL DEFAULT 0;
ALTER TABLE readings        ADD COLUMN score INTEGER NOT NULL DEFAULT 0;
```

```rust
// Al insertar cada kanji_reading:
db.execute(
    "INSERT INTO kanji_readings (entry_id, kanji, priority, info, score)
     VALUES (?1, ?2, ?3, ?4, ?5)",
    params![
        entry.id,
        &kr.kanji,
        serde_json::to_string(&kr.priority)?,
        serde_json::to_string(&kr.info)?,
        per_tag_score(&kr.priority),
    ],
)?;
```

Permite debug granular de por qué una entry tiene el `freq_score` que tiene.

---

## Orden de implementación

```
Sprint 1 (misma PR):
  ├── Tarea 1: sense_index en senses                  [~1h]
  └── Tarea 2: freq_score + has_common en entries     [~2h]

Sprint 2:
  └── Tarea 3: tabla entry_sense_counts               [~2h]

Backlog:
  └── Tarea 6: score por reading
```

Las tareas 1 y 2 van juntas porque ambas se calculan en la misma pasada
por la entry (antes de los INSERTs). La tarea 4 es un índice puro — sin riesgo.

---

## Verificación post-release

Después de publicar la nueva BD, verificar desde el lado Python con `SHODOUKAN_DEBUG=1`:

```bash
curl "localhost:8000/entries/search?q=hashiru" | python -m json.tool | grep -A 8 '"score"'
```

Valores esperados para 走る:
- `total_senses`: 8 (no 33)
- `sense_pos`: 0
- `freq`: 520 (ichi1 en ambos fields)
- `composite`: valor positivo, orden coherente con popularidad
