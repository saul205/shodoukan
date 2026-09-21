# Optimización y escalabilidad de shodoukan — Tareas de desarrollo

## Estado actual y cuellos de botella

El ciclo de vida de una búsqueda en producción hace lo siguiente por cada request:

1. FTS sobre `glosses_fts` o recorrido de índices en `kanji_readings`/`readings`
2. Para cada fila candidata: **8 operaciones `INSTR()` sobre JSON** para calcular `per_tag_score`, más **8 `INSTR()` más** para `common_word_bonus`
3. Para cada entrada resultado: **dos subqueries correlacionadas** (`_sense_pos_sq`, `_sense_total_sq`) que vuelven a hacer JOIN de senses + glosses filtrado por idioma
4. `GROUP BY`, ordenación y paginación sobre el resultado

Los pasos 2 y 3 se repiten por fila, no por query. Son el coste que escala linealmente con el número de candidatos FTS.

---

## Resumen de tareas priorizadas

| Prioridad | Tarea | Dónde | Elimina |
|-----------|-------|-------|---------|
| **1** | `senses.sense_index` | shodoukan-db + Python ORM | subquery `_sense_pos_sq` |
| **2** | `entries.freq_score` + `entries.has_common` | shodoukan-db + Python ORM | 16+ `INSTR()` por fila en ambos métodos de búsqueda |
| **3** | Tabla `entry_sense_counts(entry_id, lang, count)` | shodoukan-db + Python ORM | subquery `_sense_total_sq` |
| **4** | Índice compuesto `glosses(lang, sense_id)` | shodoukan-db | acelera el JOIN de filtrado por idioma |
| **5** | Índice `entries(jlpt)` | shodoukan-db | filtrado futuro por JLPT |
| **6** | Scores por reading (`kanji_readings.score`, `readings.score`) | shodoukan-db + Python ORM | granularidad de debug, simplifica `freq_score` |

---

## Tarea 1 — `senses.sense_index`

### Qué es

Columna entera que almacena la posición 0-based del sense dentro de su entry. El primer sense de una entry tiene `sense_index = 0`, el segundo `= 1`, etc.

### Por qué importa

Actualmente `_sense_pos_sq` es una subquery correlacionada que cuenta cuántos senses con gloss en el idioma objetivo tienen `id < matched_sense.id`. Con `sense_index` precalculado, esa información ya está en la fila — no hay que volver a contar.

**Antes:**
```python
# Subquery correlacionada: se ejecuta por cada fila del outer query
_s_pos = aliased(SenseORM)
_g_pos = aliased(GlossORM)
_sense_pos_sq = (
    select(func.count(distinct(_s_pos.id)))
    .select_from(_s_pos)
    .join(_g_pos, and_(_g_pos.sense_id == _s_pos.id, _g_pos.lang == gloss_lang(lang)))
    .where(_s_pos.entry_id == EntryORM.id, _s_pos.id < GlossORM.sense_id)
    .correlate(EntryORM, GlossORM)
    .scalar_subquery()
)
composite = (...) * (_total - func.min(_sense_pos_sq)) / (...)
```

**Después:**
```python
# SenseORM.sense_index ya está en el JOIN del outer query
composite = (...) * (_total - func.min(SenseORM.sense_index)) / (...)
```

La subquery correlacionada desaparece. `func.min(SenseORM.sense_index)` recoge la posición del primer sense que matcheó el FTS, disponible como columna en el JOIN existente.

> **Nota sobre idiomas:** `sense_index` refleja la posición entre todos los senses, no solo los del idioma objetivo. Para inglés (idioma primario de JMDict) es exacto porque todas las entries tienen gloss en inglés. Para otros idiomas es una aproximación suficientemente precisa para ranking.

### Cambio en el esquema SQLite

```sql
CREATE TABLE senses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id    INTEGER NOT NULL REFERENCES entries(id),
    sense_index INTEGER NOT NULL DEFAULT 0,
    pos         TEXT    NOT NULL DEFAULT '[]',
    misc        TEXT    NOT NULL DEFAULT '[]',
    dialects    TEXT    NOT NULL DEFAULT '[]',
    info        TEXT    NOT NULL DEFAULT '[]'
);
```

### Cambio en el ORM de Python (`db/orm.py`)

```python
class SenseORM(Base):
    __tablename__ = "senses"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("entries.id"))
    sense_index: Mapped[int]
    pos: Mapped[str]
    # resto sin cambios
```

### Simplificación en `repositories/entry.py`

Eliminar `_sense_pos_sq` y sus aliases (`_s_pos`, `_g_pos`). Sustituir en `composite`:

```python
_pos = func.min(SenseORM.sense_index)
composite = (
    (_freq + _jlpt_pts)
    * (_total - _pos)
    / (_total * (0.9 + 0.1 * _total))
).label("composite")
```

---

## Tarea 2 — `entries.freq_score` y `entries.has_common`

### Qué son

- **`freq_score`**: puntuación de frecuencia pre-calculada por entry. Combina `common_word_bonus` + el `per_tag_score` máximo entre todos sus readings.
- **`has_common`**: flag 0/1 — si algún reading tiene etiqueta `ichi1`, `spec1`, `news1` o `gai1`.

### Por qué importa

En cada búsqueda (tanto `search_by_japanese` como `search_by_gloss`), el motor evalúa esto por cada fila candidata:

```python
# Actualmente: hasta 24 INSTR() sobre strings JSON por fila
func.max(
    common_word_bonus(KanjiReadingORM.priority, ReadingORM.priority)  # 8 INSTR()
    + per_tag_score(KanjiReadingORM.priority)                         # 8 INSTR()
    + per_tag_score(ReadingORM.priority)                              # 8 INSTR()
)
```

Con columnas pre-computadas:

```python
_freq = EntryORM.freq_score  # entero directo, sin INSTR()
```

### Valores concretos con los pesos actuales

| Escenario | freq_score | has_common |
|-----------|------------|------------|
| ichi1 en kanji + ichi1 en reading | 520 (500+10+10) | 1 |
| ichi1 solo en reading | 510 (500+10) | 1 |
| ichi2 en reading | 5 | 0 |
| Sin etiquetas | 0 | 0 |

> Si cambian los pesos en `scoring.py`, hay que regenerar la BD. Dado que se regenera mensualmente, es asumible. Documentarlo en el changelog de shodoukan-db.

### Cambio en el esquema SQLite

```sql
CREATE TABLE entries (
    id         INTEGER PRIMARY KEY,
    jlpt       INTEGER,
    freq_score INTEGER NOT NULL DEFAULT 0,
    has_common INTEGER NOT NULL DEFAULT 0
);
```

### Cambio en el ORM de Python (`db/orm.py`)

```python
class EntryORM(Base):
    __tablename__ = "entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    jlpt: Mapped[int | None]
    freq_score: Mapped[int]
    has_common: Mapped[int]
    # relaciones sin cambios
```

### Simplificación en `repositories/entry.py`

En `search_by_japanese`:

```python
# Antes
_freq_j = func.max(
    common_word_bonus(KanjiReadingORM.priority, ReadingORM.priority)
    + per_tag_score(KanjiReadingORM.priority)
    + per_tag_score(ReadingORM.priority)
)

# Después
_freq_j = EntryORM.freq_score
```

En `search_by_gloss`, los JOINs con `kanji_readings` y `readings` se usaban solo para calcular `_freq`. Con `freq_score` en `entries`, esos dos `outerjoin` desaparecen:

```python
def base(s):
    return (
        s.select_from(EntryORM)
        .join(EntryORM.senses)
        .join(SenseORM.glosses)
        .join(fts.glosses_fts, fts.glosses_fts.c.rowid == GlossORM.id)
        # outerjoin(kanji_readings) y outerjoin(readings) eliminados
        .where(fts_where)
    )

_freq = EntryORM.freq_score
```

---

## Tarea 3 — Tabla `entry_sense_counts`

### Qué es

Tabla auxiliar que almacena el número de senses con al menos un gloss en cada idioma, por entry.

```sql
CREATE TABLE entry_sense_counts (
    entry_id INTEGER NOT NULL REFERENCES entries(id),
    lang     TEXT    NOT NULL,
    count    INTEGER NOT NULL,
    PRIMARY KEY (entry_id, lang)
);
CREATE INDEX idx_entry_sense_counts_entry ON entry_sense_counts(entry_id);
```

### Por qué importa

`_sense_total_sq` es la segunda subquery correlacionada: cuenta senses con gloss en el idioma buscado para cada entry candidata. Con esta tabla, es un JOIN simple.

**Antes:**
```python
_s_total = aliased(SenseORM)
_g_total = aliased(GlossORM)
_sense_total_sq = (
    select(func.count(distinct(_s_total.id)))
    .select_from(_s_total)
    .join(_g_total, and_(_g_total.sense_id == _s_total.id, _g_total.lang == gloss_lang(lang)))
    .where(_s_total.entry_id == EntryORM.id)
    .correlate(EntryORM)
    .scalar_subquery()
)
_total = func.min(_sense_total_sq)
```

**Después:**
```python
_total = EntrySenseLangCountORM.count

# En base():
.join(EntrySenseLangCountORM, and_(
    EntrySenseLangCountORM.entry_id == EntryORM.id,
    EntrySenseLangCountORM.lang == gloss_lang(lang),
))
```

### Nuevo ORM de Python (`db/orm.py`)

```python
class EntrySenseLangCountORM(Base):
    __tablename__ = "entry_sense_counts"

    entry_id: Mapped[int] = mapped_column(ForeignKey("entries.id"), primary_key=True)
    lang: Mapped[str] = mapped_column(primary_key=True)
    count: Mapped[int]
```

---

## Tarea 4 — Índice compuesto `glosses(lang, sense_id)`

El filtro `GlossORM.lang == gloss_lang(lang)` en los JOINs de scoring no tiene índice. El FTS cubre la búsqueda de texto pero el filtro de idioma en el JOIN posterior hace un scan.

```sql
CREATE INDEX idx_glosses_lang_sense ON glosses(lang, sense_id);
```

Beneficia las queries actuales sin cambio en código Python.

---

## Tarea 5 — Índice `entries(jlpt)`

Para cuando se añada filtrado por JLPT en `/entries/search`. Permite al planificador reducir candidatos antes del FTS.

```sql
CREATE INDEX idx_entries_jlpt ON entries(jlpt);
```

---

## Tarea 6 — Scores individuales por reading

Opcional, útil para debug granular. Almacenar el score ya calculado en cada reading:

```sql
ALTER TABLE kanji_readings ADD COLUMN score INTEGER NOT NULL DEFAULT 0;
ALTER TABLE readings        ADD COLUMN score INTEGER NOT NULL DEFAULT 0;
```

Permite queries de debug que identifican qué reading específico contribuyó a `freq_score` y cuánto.

---

## Estado resultante de `search_by_gloss` tras las tres primeras tareas

```python
def search_by_gloss(self, query, lang="en", limit=20, offset=0):
    _freq  = EntryORM.freq_score
    _jlpt  = func.coalesce(EntryORM.jlpt, 0) * JLPT_WEIGHT
    _total = EntrySenseLangCountORM.count
    _pos   = func.min(SenseORM.sense_index)
    composite = (
        (_freq + _jlpt)
        * (_total - _pos)
        / (_total * (0.9 + 0.1 * _total))
    ).label("composite")

    def base(s):
        return (
            s.select_from(EntryORM)
            .join(EntryORM.senses)
            .join(SenseORM.glosses)
            .join(fts.glosses_fts, fts.glosses_fts.c.rowid == GlossORM.id)
            .join(EntrySenseLangCountORM, and_(
                EntrySenseLangCountORM.entry_id == EntryORM.id,
                EntrySenseLangCountORM.lang == gloss_lang(lang),
            ))
            .where(
                text("glosses_fts MATCH :fts_q").bindparams(fts_q=fts_q),
                GlossORM.lang == gloss_lang(lang),
            )
        )
```

Cero subqueries correlacionadas. Todos los valores son columnas en el JOIN.

---

## Orden de implementación recomendado

1. **Tareas 1 + 2 juntas** — una sola pasada por el dominio al procesar cada entry: `sense_index` al insertar senses, `freq_score`/`has_common` al final de la entry.
2. **Tarea 4** — solo SQL, sin cambio de código, en cualquier momento.
3. **Tarea 3** — requiere acumular datos de glosses durante el procesamiento de cada entry.
4. **Tareas 5 y 6** — según necesidad futura.
