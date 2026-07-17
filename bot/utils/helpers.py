from datetime import timedelta


def format_number(n: int) -> str:
    return f"{n:,}"


def escape_html(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def truncate(text: str, max_len: int = 20) -> str:
    s = str(text)
    return s if len(s) <= max_len else s[:max_len] + "…"


def format_timedelta(td: timedelta) -> str:
    total = int(td.total_seconds())
    if total <= 0:
        return "now"
    h, remainder = divmod(total, 3600)
    m, s = divmod(remainder, 60)
    parts = []
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    if s and not h:
        parts.append(f"{s}s")
    return " ".join(parts) or "now"
