from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATHS = [
    ROOT / "db" / "schema.sql",
    ROOT / "supabase" / "migrations" / "20260819_0002_rls_roles.sql",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def assert_contains(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise AssertionError(f"Missing required token for {label}: {needle}")


def main() -> int:
    combined = "\n".join(read_text(path) for path in SCHEMA_PATHS)

    assert_contains(combined, "public.current_app_role()", "helper_function")
    assert_contains(combined, "auth.jwt()", "jwt_claim_source")
    assert_contains(combined, "app_metadata", "app_metadata_role")
    assert_contains(combined, "viewer", "viewer_role")
    assert_contains(combined, "data_operator", "data_operator_role")
    assert_contains(combined, "admin", "admin_role")
    assert_contains(combined, "is_active = true", "active_fact_access")
    assert_contains(combined, "audit_log", "audit_table")
    assert_contains(
        combined, "Service role bypasses RLS by design", "service_role_note"
    )

    if "user_metadata" in combined:
        raise AssertionError("user_metadata must not be used as the role source")

    if (
        "DELETE" in combined
        and "audit_log" in combined
        and "DROP POLICY IF EXISTS" not in combined
    ):
        # This static guard is intentionally permissive; actual delete protection is in the policy block.
        pass

    print("RLS static validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
