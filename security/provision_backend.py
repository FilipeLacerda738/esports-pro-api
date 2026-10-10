import argparse
import asyncio
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import ssl

import asyncpg
from dotenv import dotenv_values
from sqlalchemy.engine import make_url


ROOT = Path(__file__).resolve().parents[1]


def scram_verifier(password):
    salt = secrets.token_bytes(16)
    salted = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 4096)
    stored = hashlib.sha256(hmac.digest(salted, b"Client Key", "sha256")).digest()
    server = hmac.digest(salted, b"Server Key", "sha256")
    encode = lambda value: base64.b64encode(value).decode()
    return f"SCRAM-SHA-256$4096:{encode(salt)}${encode(stored)}:{encode(server)}"


async def apply(project_ref):
    values = dotenv_values(ROOT / ".env")
    raw_url = values.get("MIGRATION_DATABASE_URL") or values["DATABASE_URL"]
    url = make_url(raw_url.replace("postgres://", "postgresql://", 1))
    if (not project_ref or url.username != "postgres." + project_ref
            or not url.host or not url.host.endswith(".pooler.supabase.com")):
        raise RuntimeError("The administrative connection must match the explicitly selected Supabase project")
    secret_path = ROOT / ".env.backend"
    if secret_path.exists():
        existing = dotenv_values(secret_path)
        backend_url = make_url(existing["DATABASE_URL"])
        if (backend_url.host, backend_url.port, backend_url.database, backend_url.username) != (
            url.host, url.port, url.database, "esports_backend." + project_ref,
        ):
            raise RuntimeError("Stored backend credentials belong to a different target")
    else:
        backend_url = url.set(username="esports_backend." + project_ref, password=secrets.token_urlsafe(48))
        backend_url = backend_url.update_query_dict({"sslmode": "verify-full", "sslrootcert": "security/supabase-ca.crt"})
        descriptor = os.open(secret_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            file.write("DATABASE_URL=" + json.dumps(backend_url.render_as_string(hide_password=False)) + "\n")
    database_tls = ssl.create_default_context(cafile=str(ROOT / "security" / "supabase-ca.crt"))
    database_tls.minimum_version = ssl.TLSVersion.TLSv1_2
    database_tls.verify_flags &= ~ssl.VERIFY_X509_STRICT
    conn = await asyncpg.connect(
        host=url.host, port=url.port or 5432, user=url.username, password=url.password,
        database=url.database, ssl=database_tls, timeout=15, command_timeout=8, statement_cache_size=0,
    )
    try:
        snapshot = {}
        async with conn.transaction(readonly=True):
            for name, query in {
                "tables": "SELECT c.relname,c.relrowsecurity,c.relforcerowsecurity,c.relacl::text FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind IN ('r','p','S') ORDER BY c.relname",
                "schema": "SELECT nspname,nspacl::text FROM pg_namespace WHERE nspname='public'",
                "defaults": "SELECT pg_get_userbyid(d.defaclrole) AS owner,n.nspname,d.defaclobjtype::text,d.defaclacl::text FROM pg_default_acl d LEFT JOIN pg_namespace n ON n.oid=d.defaclnamespace WHERE n.nspname='public' OR d.defaclnamespace=0",
                "policies": "SELECT * FROM pg_policies WHERE schemaname='public'",
            }.items():
                snapshot[name] = [dict(row) for row in await conn.fetch(query)]
            names = {row["relname"] for row in snapshot["tables"] if not row["relname"].endswith("_seq")}
            expected = {"teams", "leagues", "matches", "players", "game_maps", "alembic_version"}
            if names != expected or snapshot["policies"]:
                raise RuntimeError("The live schema or policies differ from the reviewed configuration")
        snapshot_path = ROOT / "logs" / "database-security-before.json"
        snapshot_path.parent.mkdir(exist_ok=True)
        if snapshot_path.exists():
            if json.loads(snapshot_path.read_text(encoding="utf-8")) != snapshot:
                raise RuntimeError("A different previous production snapshot exists; review it before applying again")
        else:
            snapshot_path.write_text(json.dumps(snapshot, indent=2, default=str), encoding="utf-8")
        async with conn.transaction():
            await conn.execute("SET LOCAL lock_timeout = '250ms'")
            await conn.execute("SET LOCAL statement_timeout = '5s'")
            await conn.execute((ROOT / "security" / "harden_database.sql").read_text(encoding="utf-8"))
            await conn.fetchval("SELECT set_config('esports_backend.password', $1, true)", scram_verifier(backend_url.password))
            await conn.execute("""DO $block$ BEGIN
                EXECUTE format('ALTER ROLE esports_backend LOGIN PASSWORD %L', current_setting('esports_backend.password'));
            END $block$""")
        print("Production permissions, RLS, defaults and backend role applied atomically", flush=True)
    finally:
        await conn.close()
    runtime = await asyncpg.connect(
        host=backend_url.host, port=backend_url.port or 5432, user=backend_url.username,
        password=backend_url.password, database=backend_url.database, ssl=database_tls,
        timeout=15, command_timeout=8, statement_cache_size=0,
    )
    try:
        async with runtime.transaction(readonly=True):
            assert await runtime.fetchval("SELECT current_user") == "esports_backend"
            assert not await runtime.fetchval("SELECT rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls FROM pg_roles WHERE rolname=current_user")
            for table in ("teams", "leagues", "matches", "players", "game_maps"):
                await runtime.fetchval("SELECT EXISTS(SELECT 1 FROM public." + table + " LIMIT 1)")
            assert not await runtime.fetchval("SELECT has_schema_privilege(current_user,'public','CREATE')")
        print("Restricted backend connection accepted; production checks used read-only transactions", flush=True)
    finally:
        await runtime.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-ref", required=True)
    args = parser.parse_args()
    try:
        asyncio.run(apply(args.project_ref))
    except Exception as error:
        print("Provisioning stopped: " + type(error).__name__)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
