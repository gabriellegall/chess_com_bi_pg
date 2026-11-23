"""The "Recent period" control shared by the pages: the last N days, or the last session."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import streamlit as st

import cube

LAST_SESSION = "session"
OPTIONS = [30, 60, 90, 180, LAST_SESSION]
DEFAULT = 90
MIN_SESSION_GAMES = 5


@dataclass(frozen=True)
class Recent:
    label: str  # "Last 90 days", "Last session"
    cutoff: date | None = None  # first day of the recent period (days)
    session: cube.Session | None = None  # None with "Last session" when no session qualifies

    @property
    def is_session(self) -> bool:
        return self.cutoff is None

    def scope(self, f: cube.Filters) -> dict | None:
        """The cube arguments selecting your recent games, or None when there is no recent period to compare."""
        if self.is_session:
            return {"session": self.session.sessions_sk} if self.session else None
        start = max(f.start, self.cutoff)
        return {"start": start} if start > f.start else None


def label(choice: int | str) -> str:
    return "Last session" if choice == LAST_SESSION else f"Last {choice} days"


def control(key: str, default: int | str = DEFAULT) -> int | str:
    """Draw the period control; read its value before it is drawn with st.session_state.get(key)."""
    return st.segmented_control("Recent period", OPTIONS, default=default, format_func=label, key=key) or default


def resolve(choice: int | str, f: cube.Filters, today: date) -> Recent:
    """The recent period of a control value. For the last session, writes a grey note with its date and games."""
    if choice != LAST_SESSION:
        return Recent(label(choice), cutoff=today - timedelta(days=choice))
    session = cube.last_session(f, MIN_SESSION_GAMES)
    if session is None:
        st.caption(f"No session with at least {MIN_SESSION_GAMES} games under these filters.")
    else:
        st.caption(f"Last session: {session.start:%a %d %b %Y}, from {session.start:%H:%M} · {session.games} games")
    return Recent(label(choice), session=session)
