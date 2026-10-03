def fts_query(query: str) -> str:
    escaped = query.replace('"', '""')
    return f'"{escaped}"'


def fts_prefix_query(query: str) -> str:
    return " ".join(f"{word}*" for word in query.split())
