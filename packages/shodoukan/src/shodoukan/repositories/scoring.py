from sqlalchemy import case, func, or_

JLPT_WEIGHT = 100

_TIER1 = ("ichi1", "spec1", "news1", "gai1")


def per_tag_score(field):
    safe = func.coalesce(field, "[]")
    return sum(
        case((func.instr(safe, code) > 0, pts), else_=0)
        for code, pts in [
            ("ichi1", 10), ("spec1", 10), ("news1", 10), ("gai1", 10),
            ("ichi2",  5), ("spec2",  5), ("news2",  5), ("gai2",  5),
        ]
    )


def common_word_bonus(k_field, r_field):
    k = func.coalesce(k_field, "[]")
    r = func.coalesce(r_field, "[]")
    return case(
        (
            or_(
                *(func.instr(k, c) > 0 for c in _TIER1),
                *(func.instr(r, c) > 0 for c in _TIER1),
            ),
            500,
        ),
        else_=0,
    )
