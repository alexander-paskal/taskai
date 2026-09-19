"""Shared due-date parsing: a couple of relative keywords plus a handful of
common formats, tried in turn. Used by both the CLI's --due/create/
update path (cli.py's _parse_item_kwargs) and date-attribute filter values
(filters.py's due/created_on) so the two don't drift apart.
"""

from datetime import datetime, timedelta

_FORMATS = [
    "%m-%d-%Y",   # the CLI's original, still-documented primary format
    "%Y-%m-%d",   # ISO
    "%m/%d/%Y",
    "%m/%d/%y",
    "%B %d, %Y",  # "December 31, 2026"
    "%b %d, %Y",  # "Dec 31, 2026"
    "%B %d %Y",   # "December 31 2026"
    "%b %d %Y",   # "Dec 31 2026"
]


def _midnight(dt: datetime) -> datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


_KEYWORDS = {
    "today": lambda: _midnight(datetime.now()),
    "tomorrow": lambda: _midnight(datetime.now() + timedelta(days=1)),
}


def parse_date_value(raw: str) -> datetime:
    """A relative keyword ("today", "tomorrow") or one of a few common date
    formats, tried in turn. Raises ValueError if nothing matches."""
    key = raw.strip().lower()
    if key in _KEYWORDS:
        return _KEYWORDS[key]()

    for fmt in _FORMATS:
        try:
            return datetime.strptime(raw.strip(), fmt)
        except ValueError:
            continue

    raise ValueError(
        f"'{raw}' isn't a recognized date - try MM-DD-YYYY, YYYY-MM-DD, "
        f"or the keywords 'today'/'tomorrow'"
    )
