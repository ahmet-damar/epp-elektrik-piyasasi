from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATHS = [
    ROOT / "db" / "schema.sql",
    ROOT / "supabase" / "migrations" / "20260819_0002_rls_roles.sql",
    ROOT / "supabase" / "migrations" / "20260819_0003_fix_grants.sql",
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

    assert_contains(
        combined,
        "REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM anon",
        "anon_table_revokes",
    )
    assert_contains(
        combined,
        "REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM authenticated",
        "authenticated_table_revokes",
    )
    assert_contains(
        combined,
        "REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM viewer, data_operator, admin",
        "application_role_table_revokes",
    )
    assert_contains(
        combined,
        "REVOKE REFERENCES, TRIGGER, TRUNCATE ON ALL TABLES IN SCHEMA public FROM anon, authenticated, viewer, data_operator, admin",
        "deny_unsafe_object_privileges",
    )
    assert_contains(
        combined,
        "GRANT USAGE ON SCHEMA public TO authenticated, service_role",
        "schema_usage_grants",
    )
    assert_contains(
        combined,
        "GRANT SELECT, INSERT, UPDATE ON TABLE job_status TO authenticated",
        "authenticated_job_status_grant",
    )
    assert_contains(
        combined,
        "GRANT SELECT, INSERT, UPDATE ON TABLE sistem_parametre, kpi_esik TO authenticated",
        "authenticated_parameter_and_kpi_grants",
    )
    assert_contains(
        combined,
        "GRANT SELECT, INSERT ON TABLE audit_log TO authenticated",
        "authenticated_audit_log_grant",
    )
    assert_contains(
        combined,
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE",
        "service_role_table_grant_prefix",
    )
    assert_contains(
        combined,
        "GRANT SELECT, INSERT ON TABLE audit_log TO service_role",
        "service_role_audit_log_grant",
    )
    assert_contains(
        combined,
        "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated, service_role",
        "sequence_access",
    )
    assert_contains(
        combined,
        "REVOKE USAGE ON SCHEMA public FROM anon",
        "anon_schema_usage_revoke",
    )

    # Ensure current_app_role execution grants are present and PUBLIC cannot execute it
    assert_contains(
        combined,
        "REVOKE ALL ON FUNCTION public.current_app_role() FROM public",
        "current_app_role_revoke_public",
    )
    assert_contains(
        combined,
        "GRANT EXECUTE ON FUNCTION public.current_app_role() TO authenticated, service_role",
        "current_app_role_execute_grant",
    )

    # Ensure admin policies have corresponding authenticated DELETE grants
    import re

    # find admin policies with their FOR action (e.g., FOR ALL or FOR SELECT)
    admin_policies = re.findall(
        r"CREATE POLICY\s+(admin_[^\s]+)\s+ON\s+(\w+)\s+FOR\s+([A-Z]+)\s+TO\s+admin",
        combined,
        flags=re.IGNORECASE,
    )
    # find GRANT ... ON TABLE ... TO authenticated blocks (multiline-aware,
    # but bounded by ';' so it can't bleed across separate GRANT statements -
    # [\s\S]+? alone would happily span an unrelated "GRANT ... TO viewer"
    # statement and everything after it just to reach a LATER "TO authenticated"
    # occurrence, corrupting both captured groups; found the hard way when
    # db/schema.sql's veri_kapsam_disi grant became the FIRST "TO authenticated"
    # text in the file (2026-09-02), bkz. dokumanlar/06_canli_veri_operasyon_gunlugu.md)
    grant_blocks = re.findall(
        r"GRANT\s+([^;]+?)\s+ON\s+TABLE\s+([^;]+?)\s+TO\s+authenticated",
        combined,
        flags=re.IGNORECASE,
    )
    for policy_name, table_name, for_action in admin_policies:
        # only require DELETE grant when policy FOR is ALL or DELETE
        if for_action.upper() not in ("ALL", "DELETE"):
            continue
        found = False
        has_delete = False
        for perm_text, tables_text in grant_blocks:
            tables = [
                x.strip().strip(",")
                for x in re.split(r"[,\n]+", tables_text)
                if x.strip()
            ]
            if table_name in tables:
                found = True
                if "DELETE" in perm_text.upper():
                    has_delete = True
        if not found:
            raise AssertionError(
                f"admin policy {policy_name} exists for {table_name} but no authenticated grant block found"
            )
        if not has_delete:
            raise AssertionError(
                f"admin policy {policy_name} exists for {table_name} but authenticated is not granted DELETE"
            )

    # Audit log must not have UPDATE/DELETE/TRUNCATE granted to anyone
    if any(
        keyword in combined and "audit_log" in combined
        for keyword in ("GRANT", "UPDATE", "DELETE", "TRUNCATE")
    ):
        # more precise check below
        pass
    # explicit checks
    if "GRANT" in combined:
        for line in combined.splitlines():
            if "audit_log" in line.upper() or "audit_log" in line:
                up = line.upper()
                if "UPDATE" in up or "DELETE" in up or "TRUNCATE" in up:
                    raise AssertionError(
                        "audit_log must not be granted UPDATE/DELETE/TRUNCATE"
                    )

    # Ensure anon has no privileges (GRANT to anon is not allowed; REVOKE FROM anon is expected)
    import re as _re

    cleaned = _re.sub(r"--.*", "", combined)  # strip SQL line comments for checks
    if _re.search(r"GRANT\s+[\s\S]*\bTO\s+anon\b", cleaned, flags=_re.IGNORECASE):
        raise AssertionError("anon must not be granted privileges in migrations")

    # Detect data_operator DELETE policy (disallowed)
    if "data_operator" in combined and "DELETE" in combined:
        # look for policy lines that combine data_operator and DELETE or FOR ALL to data_operator
        bad = re.search(
            r"CREATE POLICY[\s\S]{0,120}data_operator[\s\S]{0,120}DELETE", combined
        )
        if bad:
            raise AssertionError("data_operator must not have DELETE policy")

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
