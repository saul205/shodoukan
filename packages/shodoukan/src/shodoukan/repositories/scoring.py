from sqlalchemy import func

from shodoukan.models.kanji import Kanji

JLPT_WEIGHT = 100
FTS_KANJI_WEIGHT = 1000

# --- Entry search score -------------------------------------------------------
#
#   score = match_tier * TIER_WEIGHT + popularity
#
# Both searches share the popularity unit: freq_score (0-560) + jlpt * JLPT_WEIGHT
# (0-500); gloss matches damp it by sense position (composite). TIER_WEIGHT is
# above the highest popularity, so a better tier always wins and popularity only
# orders entries within a tier. That makes reading and gloss matches comparable,
# so one query can rank and paginate both.
TIER_WEIGHT = 2000

# Gloss matches: composite = popularity / log2(pos + 2), pos = 0-based position of
# the matched sense among the entry's senses in that language (sense 1: 1.00,
# 2: 0.63, 3: 0.50, 5: 0.39, 9: 0.30). Only the position counts, not how many
# senses the entry has, so a common word with many senses isn't penalised for a
# match in its first one.

# Reading search: the spelling or reading equals the query, or starts with it.
TIER_READING_EXACT = 3
TIER_READING_PREFIX = 2

# Gloss search: tier from the entry's best bm25 rank relative to the best rank
# of the query (rank / best, 1 = as good as the best match). Gloss matches are
# rarely exact ("eat" vs "to eat"), so relevance is relative to the query.
GLOSS_TIER_3_RELEVANCE = 0.9
GLOSS_TIER_2_RELEVANCE = 0.5

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
