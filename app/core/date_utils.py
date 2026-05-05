"""
date_utils.py
─────────────
Resolves any date/time expression the user or LLM might pass into a UTC ISO 8601 string.

Supported input formats:
  Natural language (FA): امروز, دیروز, هفته گذشته, ماه گذشته, دو روز پیش, ...
  Natural language (EN): today, yesterday, last week, last month, 2 days ago, ...
  Jalali date:           1405/02/10  or  1405-02-10  (optionally with time)
  Gregorian date:        2026-04-18  or  2026/04/18  (optionally with time)
  ISO 8601:              2026-04-18T15:00:00Z  (passed through as-is)

All outputs are UTC ISO 8601: "2026-04-18T00:00:00Z"

Usage:
  from app.core.date_utils import resolve_date

  resolve_date("دیروز", position="start")   → "2026-04-27T00:00:00Z"
  resolve_date("دیروز", position="end")     → "2026-04-27T23:59:59Z"
  resolve_date("1405/02/10", position="start") → "2026-04-30T00:00:00Z"
  resolve_date("last week", position="start")  → "2026-04-21T00:00:00Z"

  position="start"  → midnight (00:00:00) of the resolved date
  position="end"    → end of day (23:59:59) of the resolved date
  position="as_is"  → use time component if present, otherwise midnight
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import jdatetime
from dateutil import parser as dateutil_parser


# ── Timezone ──────────────────────────────────────────────────────────────────
UTC = timezone.utc
IRAN_TZ = timezone(timedelta(hours=3, minutes=30))

# ── Natural language maps ─────────────────────────────────────────────────────

# Each entry maps to a (delta_days_start, delta_days_end) tuple relative to today.
# delta_days = 0  → today, -1 → yesterday, etc.
# For week/month we return the first and last day of that range.
_RELATIVE_FA = {
    # ─ single day ─
    "امروز":          ("today", "today"),
    "الان":            ("today", "today"),
    "اکنون":          ("today", "today"),
    "دیروز":          ("yesterday", "yesterday"),
    "پریروز":         ("2_days_ago", "2_days_ago"),
    "فردا":           ("tomorrow", "tomorrow"),
    # ─ N days ago ─
    "یک روز پیش":    ("1_days_ago", "1_days_ago"),
    "دو روز پیش":    ("2_days_ago", "2_days_ago"),
    "سه روز پیش":    ("3_days_ago", "3_days_ago"),
    "یک روز قبل":    ("1_days_ago", "1_days_ago"),
    "دو روز قبل":    ("2_days_ago", "2_days_ago"),
    "سه روز قبل":    ("3_days_ago", "3_days_ago"),
    # ─ week ─
    "هفته گذشته":    ("last_week_start", "last_week_end"),
    "هفته پیش":      ("last_week_start", "last_week_end"),
    "این هفته":      ("this_week_start", "today"),
    # ─ month ─
    "ماه گذشته":     ("last_month_start", "last_month_end"),
    "ماه پیش":       ("last_month_start", "last_month_end"),
    "این ماه":       ("this_month_start", "today"),
    # ─ 24h shortcuts ─
    "۲۴ ساعت گذشته": ("1_days_ago", "today"),
    "24 ساعت گذشته": ("1_days_ago", "today"),
    "۴۸ ساعت گذشته": ("2_days_ago", "today"),
    "48 ساعت گذشته": ("2_days_ago", "today"),
}

_RELATIVE_EN = {
    "today":             ("today", "today"),
    "now":               ("today", "today"),
    "yesterday":         ("yesterday", "yesterday"),
    "day before yesterday": ("2_days_ago", "2_days_ago"),
    "tomorrow":          ("tomorrow", "tomorrow"),
    "1 day ago":         ("1_days_ago", "1_days_ago"),
    "2 days ago":        ("2_days_ago", "2_days_ago"),
    "3 days ago":        ("3_days_ago", "3_days_ago"),
    "last week":         ("last_week_start", "last_week_end"),
    "this week":         ("this_week_start", "today"),
    "last month":        ("last_month_start", "last_month_end"),
    "this month":        ("this_month_start", "today"),
    "past 24 hours":     ("1_days_ago", "today"),
    "past 48 hours":     ("2_days_ago", "today"),
    "past week":         ("last_week_start", "today"),
    "past month":        ("last_month_start", "today"),
}

_ALL_RELATIVE = {**_RELATIVE_FA, **_RELATIVE_EN}

# Persian digit map
_FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")

# ── Pre-compiled patterns ──────────────────────────────
_ISO_UTC_RE = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')


def _normalize(text: str) -> str:
    """Lowercase, strip, and convert Persian digits to ASCII."""
    return text.strip().lower().translate(_FA_DIGITS)


def _resolve_anchor(anchor: str, today: datetime) -> datetime:
    """Convert an anchor string like 'yesterday', 'last_week_start' to a date."""
    if anchor == "today":
        return today
    if anchor == "yesterday":
        return today - timedelta(days=1)
    if anchor == "tomorrow":
        return today + timedelta(days=1)

    # N days ago
    m = re.match(r"(\d+)_days_ago", anchor)
    if m:
        return today - timedelta(days=int(m.group(1)))

    # Week helpers
    if anchor == "this_week_start":
        return today - timedelta(days=today.weekday())   # Monday
    if anchor == "last_week_start":
        start = today - timedelta(days=today.weekday() + 7)
        return start
    if anchor == "last_week_end":
        end = today - timedelta(days=today.weekday() + 1)
        return end

    # Month helpers
    if anchor == "this_month_start":
        return today.replace(day=1)
    if anchor == "last_month_start":
        first_this = today.replace(day=1)
        last_month = first_this - timedelta(days=1)
        return last_month.replace(day=1)
    if anchor == "last_month_end":
        first_this = today.replace(day=1)
        return first_this - timedelta(days=1)

    return today  # fallback


def _apply_position(dt: datetime, position: str) -> datetime:
    if position == "end":
        return dt.replace(hour=23, minute=59, second=59, microsecond=0)
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def _to_utc_iso(dt: datetime) -> str:
    """Convert a datetime (assumed UTC if no tzinfo) to ISO 8601 UTC string."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    dt_utc = dt.astimezone(UTC)
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def _try_jalali(text: str) -> Optional[datetime]:
    """
    Try to parse a Jalali date string like:
      1405/02/10
      1405-02-10
      1405/02/10 15:30
      1405/02/10T15:30:00
    Returns a UTC-aware datetime (converts from IRAN_TZ) or None.
    """
    # Normalise separators
    t = re.sub(r"[-/]", "/", text.strip().translate(_FA_DIGITS))
    t = t.replace("T", " ").replace("t", " ")

    # Pattern: YYYY/MM/DD [HH:MM[:SS]]
    m = re.match(
        r"(\d{4})/(\d{1,2})/(\d{1,2})"
        r"(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?$",
        t,
    )
    if not m:
        return None

    year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))

    # Sanity check: Jalali years are typically 1300–1500
    if not (1300 <= year <= 1500):
        return None

    hour = int(m.group(4)) if m.group(4) else 0
    minute = int(m.group(5)) if m.group(5) else 0
    second = int(m.group(6)) if m.group(6) else 0

    try:
        jdt = jdatetime.datetime(year, month, day, hour, minute, second,
                                 tzinfo=IRAN_TZ)
        return jdt.togregorian().astimezone(UTC)
    except Exception:
        return None


def _try_gregorian(text: str) -> Optional[datetime]:
    """
    Try to parse a Gregorian date string using dateutil.
    Returns a UTC-aware datetime or None.
    """
    try:
        dt = dateutil_parser.parse(text, dayfirst=False)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except Exception:
        return None


# ── Public API ────────────────────────────────────────────────────────────────

def resolve_date(text: str, position: str = "start") -> Tuple[Optional[str], Optional[str]]:
    """
    Resolve any date expression to a UTC ISO 8601 string.

    Args:
        text:     The raw date string from user or LLM
        position: "start" → 00:00:00, "end" → 23:59:59, "as_is" → keep parsed time

    Returns:
        (utc_iso_string, error_message)
        On success: ("2026-04-18T00:00:00Z", None)
        On failure: (None, "human-readable error in Farsi")
    """
    if not text or not text.strip():
        return None, "تاریخ وارد نشده است."

    if _ISO_UTC_RE.match(text.strip()):
        return text.strip(), None

    normalized = _normalize(text)
    today = datetime.now(IRAN_TZ).replace(hour=0, minute=0, second=0, microsecond=0)

    # ── 1. Natural language ───────────────────────────────────────────────────
    if normalized in _ALL_RELATIVE:
        start_anchor, end_anchor = _ALL_RELATIVE[normalized]
        anchor = end_anchor if position == "end" else start_anchor
        dt = _resolve_anchor(anchor, today)
        dt = _apply_position(dt, position)
        return _to_utc_iso(dt), None

    # ── 2. "N روز پیش / N days ago" with numeric prefix ─────────────────────
    m = re.match(r"(\d+)\s*(روز پیش|روز قبل|days? ago)", normalized)
    if m:
        n = int(m.group(1))
        dt = _apply_position(today - timedelta(days=n), position)
        return _to_utc_iso(dt), None

    # ── 3. Jalali date (1300–1500 range) ─────────────────────────────────────
    jalali_result = _try_jalali(text)
    if jalali_result is not None:
        if position != "as_is":
            jalali_result = _apply_position(jalali_result, position)
        return _to_utc_iso(jalali_result), None

    # ── 4. Gregorian / ISO 8601 ───────────────────────────────────────────────
    gregorian_result = _try_gregorian(text)
    if gregorian_result is not None:
        if position != "as_is":
            gregorian_result = _apply_position(gregorian_result, position)
        return _to_utc_iso(gregorian_result), None

    # ── 5. Nothing matched ────────────────────────────────────────────────────
    return None, (
        f"تاریخ '{text}' قابل تشخیص نیست. "
        "لطفاً از فرمت‌هایی مثل 'دیروز'، '1405/02/10'، یا '2026-04-18' استفاده کنید."
    )


def resolve_date_range(
    from_text: str,
    to_text: str,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Resolve both FromDate and ToDate at once.

    Returns:
        (from_utc, to_utc, error_message)
        On success: ("2026-04-18T00:00:00Z", "2026-04-18T23:59:59Z", None)
        On failure: (None, None, "error in Farsi")
    """
    from_utc, err = resolve_date(from_text, position="start")
    if err:
        return None, None, f"خطا در تاریخ شروع: {err}"

    to_utc, err = resolve_date(to_text, position="end")
    if err:
        return None, None, f"خطا در تاریخ پایان: {err}"

    # Sanity check: from must be before to
    from_dt = datetime.fromisoformat(from_utc.replace("Z", "+00:00"))
    to_dt = datetime.fromisoformat(to_utc.replace("Z", "+00:00"))

    if from_dt > to_dt:
        return None, None, (
            f"تاریخ شروع ({from_text}) بعد از تاریخ پایان ({to_text}) است. "
            "لطفاً ترتیب تاریخ‌ها را بررسی کنید."
        )

    return from_utc, to_utc, None
