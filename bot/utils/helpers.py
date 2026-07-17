from datetime import timedelta
from typing import Tuple


# ── HTML escaping ──────────────────────────────────────────────────────────────

def escape_html(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def format_number(n) -> str:
    return f"{int(n):,}"


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


# ── Rank system ────────────────────────────────────────────────────────────────

RANKS = [
    (0,      "🌱", "Newcomer",   50_000),
    (500,    "🥉", "Bronze",     2_000),
    (2_000,  "🥈", "Silver",     5_000),
    (5_000,  "🥇", "Gold",       10_000),
    (10_000, "💎", "Platinum",   25_000),
    (25_000, "👑", "Diamond",    50_000),
    (50_000, "🌟", "Legend",     None),
]


def get_rank(total_earned: int) -> Tuple[str, str, int | None]:
    """Returns (emoji, title, next_threshold)."""
    current = RANKS[0]
    for r in RANKS:
        if total_earned >= r[0]:
            current = r
        else:
            break
    idx = RANKS.index(current)
    nxt = RANKS[idx + 1][0] if idx + 1 < len(RANKS) else None
    return current[1], current[2], nxt


def rank_progress_bar(total_earned: int, length: int = 10) -> str:
    _, _, nxt = get_rank(total_earned)
    if nxt is None:
        return "█" * length + "  MAX"
    # find previous threshold
    prev = 0
    for r in RANKS:
        if total_earned >= r[0]:
            prev = r[0]
    span = nxt - prev
    done = total_earned - prev
    pct = min(100, int(done / span * 100)) if span else 100
    filled = int(length * pct / 100)
    bar = "█" * filled + "░" * (length - filled)
    return f"{bar}  {pct}%"


# ── Progress bar ───────────────────────────────────────────────────────────────

def progress_bar(current: int, target: int, length: int = 10) -> str:
    if target <= 0:
        return "█" * length + "  100%"
    pct = min(100, int(current / target * 100))
    filled = int(length * pct / 100)
    bar = "█" * filled + "░" * (length - filled)
    return f"{bar}  {pct}%"


# ── Streak bonus ───────────────────────────────────────────────────────────────

def streak_bonus(streak: int, base: int) -> int:
    """Return bonus points for this streak day."""
    if streak >= 30:
        return base * 5
    if streak >= 14:
        return base * 3
    if streak >= 7:
        return base * 2
    if streak >= 5:
        return base + int(base * 0.5)
    if streak >= 3:
        return base + int(base * 0.2)
    return base


def streak_fire(streak: int) -> str:
    """Visual streak fire indicator."""
    if streak >= 30:
        return "🔥🔥🔥"
    if streak >= 14:
        return "🔥🔥"
    if streak >= 7:
        return "🔥"
    if streak >= 3:
        return "✨"
    return "⚡"


def streak_milestone_text(streak: int) -> str:
    """Return a milestone message if streak hit a special number."""
    milestones = {7: "🎉 7-Day Streak!", 14: "🌟 2-Week Streak!", 30: "👑 30-Day Legend!"}
    return milestones.get(streak, "")
