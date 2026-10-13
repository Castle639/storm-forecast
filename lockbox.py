"""Room 27's lockboxes, in code (STATE, 02:10 UTC 13 Oct 2026; room 26's spans, unchanged).
Lockbox 1: every G target and the L1 solar wind/IMF from 2025-01-01 00:00 UTC on.
Lockbox 2: 1986-01-01 ... 1995-05-31 23:59:59 UTC.
Development: 1995-06-01 ... 2024-12-31 23:59:59 UTC."""
import pandas as pd

LOCK1_START = pd.Timestamp("2025-01-01T00:00:00Z")
LOCK2_START = pd.Timestamp("1986-01-01T00:00:00Z")
LOCK2_END = pd.Timestamp("1995-05-31T23:59:59Z")
DEV_START = pd.Timestamp("1995-06-01T00:00:00Z")
DEV_END = pd.Timestamp("2024-12-31T23:59:59Z")


def _ts(t):
    t = pd.Timestamp(t)
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


def assert_dev(times):
    """Refuse anything outside development (both lockboxes)."""
    s = pd.to_datetime(pd.Series(times), utc=True)
    s = s.dropna()
    if len(s) == 0:
        return
    assert s.min() >= DEV_START, f"lockbox 2 / pre-dev time {s.min()}"
    assert s.max() <= DEV_END, f"lockbox 1 time {s.max()}"


def cut_dev(df, col):
    """Keep development rows only (used at parse, before anything is stored)."""
    t = pd.to_datetime(df[col], utc=True)
    return df[(t >= DEV_START) & (t <= DEV_END)].copy()

# aliases for code copied from room 25 (its names)
LOCKBOX_START = LOCK1_START
