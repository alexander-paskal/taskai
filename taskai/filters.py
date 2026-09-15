"""
Attribute filters for `task show`.

    task show status="IN PROGRESS" priority>=2 due_by<12-31-2026

Each argument is one filter, `attr<op>value`, with no spaces around the
operator (a quoted value with spaces still arrives as a single token). Every
filter must pass for an item to match - the list is AND-ed. Text matches (`=`
on a string attribute) use fnmatch, so `name=Write*` works; the ordering
operators compare numbers, dates, or strings as appropriate.

`match_items` returns the ids that match; `with_ancestors` pads that set out
with every matched item's parent chain, so the result renders as a coherent
tree rather than a scatter of disconnected nodes.
"""

import fnmatch
import re
from dataclasses import dataclass

from taskai.dates import parse_date_value
from taskai.json_dir_database import DatabaseError

# attr -> how both sides of the comparison should be read
_INT_ATTRS = {"id", "parent_id", "priority"}
_DATE_ATTRS = {"due_by", "created_on"}
_BOOL_ATTRS = {"completed"}
_STR_ATTRS = {"name", "description", "status"}

FILTERABLE_ATTRS = _INT_ATTRS | _DATE_ATTRS | _BOOL_ATTRS | _STR_ATTRS

# two-char operators first so `>=` isn't read as `>` then `=`
_FILTER_RE = re.compile(
    r"^(?P<attr>[A-Za-z_][A-Za-z0-9_]*)(?P<op>>=|<=|=|>|<)(?P<value>.*)$",
    re.DOTALL,
)


class FilterError(ValueError):
    """A filter argument that doesn't parse, or whose value is unusable."""


def _split_token(token: str):
    """(attr, op, raw_value) if `token` is structurally `attr<op>...` with a
    known attribute, else None. Purely structural - no value coercion."""
    match = _FILTER_RE.match(token)
    if match is None or match.group("attr") not in FILTERABLE_ATTRS:
        return None
    return match.group("attr"), match.group("op"), match.group("value")


def _coerce(attr: str, raw: str):
    if attr in _INT_ATTRS:
        return int(raw)
    if attr in _BOOL_ATTRS:
        return str(raw).strip().lower() in ("true", "1", "yes")
    if attr in _DATE_ATTRS:
        return parse_date_value(raw).date()
    return raw  # string: compared with fnmatch (=) or lexically (< >)


@dataclass
class FilterExpr:
    attr: str
    op: str
    value: object

    def matches(self, item) -> bool:
        return _compare(self.op, _item_value(item, self.attr), self.value)


def _item_value(item, attr):
    value = getattr(item, attr, None)
    if attr in _DATE_ATTRS and value is not None:
        return value.date()  # drop the time component for date comparisons
    return value


def _compare(op: str, actual, expected) -> bool:
    if op == "=":
        if isinstance(expected, str):
            return fnmatch.fnmatch("" if actual is None else str(actual), expected)
        return actual == expected
    if actual is None:
        return False  # None has no ordering
    try:
        if op == ">":
            return actual > expected
        if op == "<":
            return actual < expected
        if op == ">=":
            return actual >= expected
        if op == "<=":
            return actual <= expected
    except TypeError:
        return False
    return False


def looks_like_filters(tokens) -> bool:
    """True when `show`'s arguments should be treated as a filter query rather
    than a single id / name target."""
    return bool(tokens) and any(_split_token(t) is not None for t in tokens)


def parse_filters(tokens) -> list[FilterExpr]:
    """All tokens -> FilterExprs. Raises FilterError on the first token that
    isn't a valid `attr<op>value`."""
    exprs = []
    for token in tokens:
        parts = _split_token(token)
        if parts is None:
            raise FilterError(
                f"'{token}' is not a valid filter - expected attr=value, "
                f"attr>value, etc. (attributes: {', '.join(sorted(FILTERABLE_ATTRS))})"
            )
        attr, op, raw = parts
        try:
            value = _coerce(attr, raw)
        except (ValueError, TypeError):
            raise FilterError(f"'{raw}' is not a valid value for '{attr}'")
        exprs.append(FilterExpr(attr, op, value))
    return exprs


def match_items(db, exprs) -> set:
    """Ids of the items that satisfy every filter."""
    matched = set()
    for item_id in db.get_item_ids():
        item = db.get_item(item_id)
        if all(expr.matches(item) for expr in exprs):
            matched.add(item_id)
    return matched


def with_ancestors(db, ids) -> set:
    """`ids` plus every ancestor of every id, so the selection is a set of
    complete root-to-node paths."""
    keep = set()
    for id_ in ids:
        cursor = id_
        while cursor is not None and cursor not in keep:
            keep.add(cursor)
            try:
                cursor = db.get_item_attr(cursor, "parent_id")
            except DatabaseError:
                break
    return keep
