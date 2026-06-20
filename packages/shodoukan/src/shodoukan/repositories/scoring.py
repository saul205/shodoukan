from sqlalchemy import func

from shodoukan.models.kanji import Kanji

JLPT_WEIGHT = 100

# Weight applied to entry position when ranking related kanji.
# gap(pos 0 → pos 3) = 75 000 > max k_score spread (~50 000),
# so a kanji from entry 0 always beats any kanji from entries 1-3.
KANJI_POSITION_WEIGHT = 100_000


def kanji_score_value(k: Kanji) -> int:
    score = (k.jlpt or 0) * 10_000 - (k.freq if k.freq is not None else 99_999)
    if k.grade is not None:
        score += (11 - k.grade) * 1_000
    return score


def kanji_score(jlpt_field, freq_field, grade_field=None):
    # JLPT dominates; grade breaks ties within the same level; freq breaks remaining ties.
    # jlpt: 1–5 (5=N5=most common). grade: 1–10 (lower=more basic), NULL=ungraded.
    # freq: lower=more common, NULL=unranked.
    score = (
        func.coalesce(jlpt_field, 0) * 10_000
        - func.coalesce(freq_field, 99_999)
    )
    if grade_field is not None:
        score = score + func.coalesce(11 - grade_field, 0) * 1_000
    return score
