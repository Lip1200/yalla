"""Reusable fakes for tests.

`FakeSupabaseClient` mimics the subset of postgrest builder API used by
the codebase (`.table().select().eq().in_().neq().or_().order().limit()
.insert().update().delete().execute()`). It backs each table by an
in-memory list of dicts so service code reading and writing through the
same client sees consistent state across the test.

Filters are accumulated until `.execute()` runs. Inserts/updates/deletes
apply the accumulated filters before mutating the store and return the
affected rows via the standard `data` attribute on the response.

This is enough fidelity for the service-layer logic we care about — we
don't try to mimic Supabase RLS, query planning, joins, or actual
SQL semantics.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FakeResponse:
    data: list[dict[str, Any]] = field(default_factory=list)
    count: int | None = None


class FakeQuery:
    def __init__(self, store: "FakeStore", table_name: str) -> None:
        self._store = store
        self._table = table_name
        self._filters: list[tuple[str, str, Any]] = []
        self._or_filters: list[str] = []
        self._mode: str | None = None  # "select" | "insert" | "update" | "delete"
        self._payload: Any = None
        self._select_cols: list[str] | None = None
        self._limit: int | None = None
        self._order_key: str | None = None
        self._order_desc: bool = False
        self._count_mode: str | None = None

    # ----- terminal modes -----
    def select(self, *cols: str, count: str | None = None) -> "FakeQuery":
        self._mode = "select"
        self._count_mode = count
        if cols:
            joined = ",".join(cols)
            self._select_cols = [c.strip() for c in joined.split(",")]
        return self

    def insert(self, payload: dict | list[dict]) -> "FakeQuery":
        self._mode = "insert"
        self._payload = payload
        return self

    def update(self, payload: dict) -> "FakeQuery":
        self._mode = "update"
        self._payload = payload
        return self

    def delete(self) -> "FakeQuery":
        self._mode = "delete"
        return self

    # ----- filters -----
    def eq(self, col: str, value: Any) -> "FakeQuery":
        self._filters.append(("eq", col, value))
        return self

    def neq(self, col: str, value: Any) -> "FakeQuery":
        self._filters.append(("neq", col, value))
        return self

    def in_(self, col: str, values: list) -> "FakeQuery":
        self._filters.append(("in", col, list(values)))
        return self

    def or_(self, expr: str) -> "FakeQuery":
        self._or_filters.append(expr)
        return self

    def is_(self, col: str, value: Any) -> "FakeQuery":
        self._filters.append(("is", col, value))
        return self

    def not_(self) -> "FakeQuery":
        # Used in the codebase as `.not_.is_(col, "null")`. We model
        # `not_` as a sentinel that flips the next filter.
        self._filters.append(("not", "_pending_", True))
        return self

    def order(self, col: str, desc: bool = False) -> "FakeQuery":
        self._order_key = col
        self._order_desc = desc
        return self

    def limit(self, n: int) -> "FakeQuery":
        self._limit = n
        return self

    def range(self, start: int, end: int) -> "FakeQuery":
        self._limit = end - start + 1
        return self

    # ----- execute -----
    def execute(self) -> FakeResponse:
        rows = self._store.rows(self._table)

        def matches(row: dict[str, Any]) -> bool:
            for op, col, val in self._filters:
                if op == "eq":
                    if row.get(col) != val:
                        return False
                elif op == "neq":
                    if row.get(col) == val:
                        return False
                elif op == "in":
                    if row.get(col) not in val:
                        return False
                elif op == "is":
                    target = None if val == "null" else val
                    if row.get(col) != target:
                        return False
            return True

        filtered = [r for r in rows if matches(r)]

        if self._mode == "select":
            if self._order_key is not None:
                filtered.sort(
                    key=lambda r: (r.get(self._order_key) is None, r.get(self._order_key)),
                    reverse=self._order_desc,
                )
            count = len(filtered) if self._count_mode == "exact" else None
            if self._limit is not None:
                filtered = filtered[: self._limit]
            return FakeResponse(data=deepcopy(filtered), count=count)

        if self._mode == "insert":
            payloads = self._payload if isinstance(self._payload, list) else [self._payload]
            inserted: list[dict[str, Any]] = []
            for p in payloads:
                new_row = deepcopy(p)
                if "id" not in new_row:
                    new_row["id"] = self._store.next_id(self._table)
                self._store.rows(self._table).append(new_row)
                inserted.append(deepcopy(new_row))
            return FakeResponse(data=inserted)

        if self._mode == "update":
            updated: list[dict[str, Any]] = []
            for row in filtered:
                row.update(self._payload)
                updated.append(deepcopy(row))
            return FakeResponse(data=updated)

        if self._mode == "delete":
            store_rows = self._store.rows(self._table)
            keep = [r for r in store_rows if not matches(r)]
            removed = [r for r in store_rows if matches(r)]
            self._store.set_rows(self._table, keep)
            return FakeResponse(data=deepcopy(removed))

        raise RuntimeError(f"FakeQuery.execute() with no mode (table={self._table})")


class FakeStore:
    def __init__(self) -> None:
        self._tables: dict[str, list[dict[str, Any]]] = {}
        self._next_id: dict[str, int] = {}

    def rows(self, table: str) -> list[dict[str, Any]]:
        return self._tables.setdefault(table, [])

    def set_rows(self, table: str, rows: list[dict[str, Any]]) -> None:
        self._tables[table] = rows

    def seed(self, table: str, rows: list[dict[str, Any]]) -> None:
        self._tables[table] = [deepcopy(r) for r in rows]
        max_id = max((r.get("id") for r in rows if isinstance(r.get("id"), int)), default=0)
        self._next_id[table] = max(self._next_id.get(table, 0), max_id)

    def next_id(self, table: str) -> int:
        self._next_id[table] = self._next_id.get(table, 0) + 1
        return self._next_id[table]


class FakeAuth:
    """Stand-in for `supabase_client.auth`. By default `get_user` raises
    so any non-service-token request falls through to a 401 (matching the
    behaviour we want in integration tests that only use the service
    token). Override on the instance to return a fake response."""

    def __init__(self) -> None:
        self._get_user_side_effect: BaseException | None = None
        self._get_user_response: Any = None
        self._sign_up_side_effect: BaseException | None = None
        self._sign_up_response: Any = None
        self.sign_up_calls: list[dict[str, Any]] = []

    def set_get_user_response(self, response: Any) -> None:
        self._get_user_response = response
        self._get_user_side_effect = None

    def set_get_user_error(self, exc: BaseException) -> None:
        self._get_user_side_effect = exc
        self._get_user_response = None

    def get_user(self, _token: str) -> Any:
        if self._get_user_side_effect is not None:
            raise self._get_user_side_effect
        if self._get_user_response is not None:
            return self._get_user_response
        raise RuntimeError("FakeAuth.get_user: no response configured")

    def set_sign_up_response(self, response: Any) -> None:
        self._sign_up_response = response
        self._sign_up_side_effect = None

    def set_sign_up_error(self, exc: BaseException) -> None:
        self._sign_up_side_effect = exc
        self._sign_up_response = None

    def sign_up(self, payload: dict) -> Any:
        self.sign_up_calls.append(payload)
        if self._sign_up_side_effect is not None:
            raise self._sign_up_side_effect
        if self._sign_up_response is not None:
            return self._sign_up_response
        raise RuntimeError("FakeAuth.sign_up: no response configured")


class _FakeSession:
    """Stand-in for the httpx Session that supabase-py's postgrest client
    holds. Only `headers` is touched by restore_service_bearer (it writes
    the Authorization header directly), so a plain dict is enough."""

    def __init__(self) -> None:
        self.headers: dict[str, Any] = {}


class FakePostgrest:
    """Capture postgrest.auth(key) calls AND expose a writable session
    so restore_service_bearer can set the Authorization header on the
    fake client during tests (same mechanism as production)."""

    def __init__(self) -> None:
        self.auth_calls: list[Any] = []
        self.session = _FakeSession()

    def auth(self, key: Any) -> None:
        # Legacy hook — kept so old assertions still pass. In real
        # supabase-py 2.x this returns a new client; the singleton's
        # session.headers is NOT mutated here.
        self.auth_calls.append(key)


class FakeSupabaseClient:
    def __init__(self, store: FakeStore | None = None) -> None:
        self.store = store or FakeStore()
        self.auth = FakeAuth()
        self.postgrest = FakePostgrest()

    def table(self, name: str) -> FakeQuery:
        return FakeQuery(self.store, name)
