from pathlib import Path

import asyncpg
import pytest
from sqlalchemy import text

from app.db.session import engine


async def admin_connection():
    return await asyncpg.connect(
        host="127.0.0.1", port=55439, user="postgres",
        password="local-security-test-only", database="esports_security_test", ssl=False,
    )


@pytest.mark.asyncio
async def test_backend_has_only_required_permissions():
    try:
        async with engine.connect() as conn:
            role = (await conn.execute(text(
                "SELECT rolname, rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls "
                "FROM pg_roles WHERE rolname=current_user"
            ))).one()
            assert tuple(role) == ("esports_backend", False, False, False, False, False)
            assert not (await conn.execute(text("SELECT has_schema_privilege(current_user,'public','CREATE')"))).scalar_one()
            assert not (await conn.execute(text("SELECT has_table_privilege(current_user,'public.alembic_version','SELECT')"))).scalar_one()
            for table in ("teams", "leagues", "matches", "players", "game_maps"):
                for privilege in ("SELECT", "INSERT", "UPDATE"):
                    assert (await conn.execute(text(f"SELECT has_table_privilege(current_user,'public.{table}','{privilege}')"))).scalar_one()
                for privilege in ("TRUNCATE", "TRIGGER", "REFERENCES"):
                    assert not (await conn.execute(text(f"SELECT has_table_privilege(current_user,'public.{table}','{privilege}')"))).scalar_one()
                delete = (await conn.execute(text(f"SELECT has_table_privilege(current_user,'public.{table}','DELETE')"))).scalar_one()
                assert delete == (table == "matches")
            for sequence in ("teams_id_seq", "leagues_id_seq", "matches_id_seq"):
                assert (await conn.execute(text(f"SELECT has_sequence_privilege(current_user,'public.{sequence}','USAGE')"))).scalar_one()
                assert not (await conn.execute(text(f"SELECT has_sequence_privilege(current_user,'public.{sequence}','UPDATE')"))).scalar_one()
            for query in ("CREATE TABLE public.forbidden_test(id int)", "SELECT * FROM public.alembic_version", "DELETE FROM public.teams WHERE false"):
                async with conn.begin_nested() as transaction:
                    with pytest.raises(Exception, match="permission denied"):
                        await conn.execute(text(query))
                    await transaction.rollback()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["anon", "authenticated"])
async def test_public_roles_cannot_access_application_tables(role):
    conn = await admin_connection()
    try:
        async with conn.transaction():
            table_ids = {row["relname"]: row["oid"] for row in await conn.fetch("SELECT oid,relname FROM pg_class WHERE relnamespace='public'::regnamespace AND relkind='r'")}
            await conn.execute("SET LOCAL ROLE " + role)
            assert not await conn.fetchval("SELECT has_schema_privilege(current_user,'public','USAGE')")
            for table in ("teams", "leagues", "matches", "players", "game_maps", "alembic_version"):
                for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE"):
                    assert not await conn.fetchval("SELECT has_table_privilege(current_user,$1::oid,$2)", table_ids[table], privilege)
                with pytest.raises(asyncpg.InsufficientPrivilegeError):
                    async with conn.transaction():
                        await conn.fetch("SELECT 1 FROM public." + table + " LIMIT 1")
    finally:
        await conn.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["anon", "authenticated"])
async def test_rls_denies_rows_even_if_read_grants_are_restored(role):
    conn = await admin_connection()
    transaction = conn.transaction()
    await transaction.start()
    try:
        await conn.execute("INSERT INTO public.teams(name,game) VALUES ('RLS local probe','CSGO')")
        await conn.execute("GRANT USAGE ON SCHEMA public TO " + role)
        await conn.execute("GRANT SELECT ON public.teams TO " + role)
        await conn.execute("SET LOCAL ROLE " + role)
        assert not await conn.fetchval("SELECT EXISTS(SELECT 1 FROM public.teams)")
    finally:
        await transaction.rollback()
        await conn.close()


@pytest.mark.asyncio
async def test_future_objects_do_not_grant_public_access():
    conn = await admin_connection()
    transaction = conn.transaction()
    await transaction.start()
    try:
        await conn.execute("CREATE TABLE public.future_permission_probe(id serial PRIMARY KEY)")
        await conn.execute("CREATE FUNCTION public.future_function_probe() RETURNS integer LANGUAGE sql AS 'SELECT 1'")
        for role in ("anon", "authenticated", "esports_backend"):
            assert not await conn.fetchval("SELECT has_table_privilege($1,'public.future_permission_probe','SELECT')", role)
            assert not await conn.fetchval("SELECT has_sequence_privilege($1,'public.future_permission_probe_id_seq','USAGE')", role)
            assert not await conn.fetchval("SELECT has_function_privilege($1,'public.future_function_probe()','EXECUTE')", role)
        await conn.execute("GRANT USAGE, CREATE ON SCHEMA public TO supabase_admin")
        await conn.execute("SET LOCAL ROLE supabase_admin")
        await conn.execute("CREATE TABLE public.managed_future_probe(id integer)")
        await conn.execute("GRANT ALL ON public.managed_future_probe TO anon, authenticated")
        await conn.execute("RESET ROLE")
        for role in ("anon", "authenticated"):
            await conn.execute("SET LOCAL ROLE " + role)
            with pytest.raises(asyncpg.InsufficientPrivilegeError):
                async with conn.transaction():
                    await conn.fetch("SELECT 1 FROM public.managed_future_probe")
            await conn.execute("RESET ROLE")
    finally:
        await transaction.rollback()
        await conn.close()


@pytest.mark.asyncio
async def test_security_changes_are_idempotent():
    conn = await admin_connection()
    transaction = conn.transaction()
    await transaction.start()
    try:
        await conn.execute(Path("security/harden_database.sql").read_text(encoding="utf-8"))
        rows = await conn.fetch("SELECT relname,relrowsecurity FROM pg_class WHERE relnamespace='public'::regnamespace AND relname=ANY($1::text[])", ["teams", "leagues", "matches", "players", "game_maps", "alembic_version"])
        assert len(rows) == 6
        assert all(row["relrowsecurity"] for row in rows)
    finally:
        await transaction.rollback()
        await conn.close()


@pytest.mark.asyncio
async def test_backend_cleanup_keeps_working_with_rls():
    from app.jobs.tasks import cleanup_old_matches_task
    conn = await admin_connection()
    try:
        match_id = await conn.fetchval("INSERT INTO matches(pandascore_id,game,status,begin_at,team_a_score,team_b_score) VALUES(765432109,'CSGO','finished',now()-interval '15 days',2,1) RETURNING id")
        await conn.execute("INSERT INTO game_maps(id,match_id,position,status) VALUES(765432108,$1,1,'finished')", match_id)
        await cleanup_old_matches_task()
        assert not await conn.fetchval("SELECT EXISTS(SELECT 1 FROM matches WHERE id=$1)", match_id)
        assert not await conn.fetchval("SELECT EXISTS(SELECT 1 FROM game_maps WHERE id=765432108)")
    finally:
        await conn.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_scram_credential_is_accepted_by_postgres():
    from security.provision_backend import scram_verifier
    conn = await admin_connection()
    try:
        async with conn.transaction():
            await conn.fetchval("SELECT set_config('esports_backend.password',$1,true)", scram_verifier("local-backend-test-only"))
            await conn.execute("""DO $block$ BEGIN
                EXECUTE format('ALTER ROLE esports_backend PASSWORD %L', current_setting('esports_backend.password'));
            END $block$""")
    finally:
        await conn.close()
    backend = await asyncpg.connect(host="127.0.0.1", port=55439, user="esports_backend", password="local-backend-test-only", database="esports_security_test", ssl=False)
    try:
        assert await backend.fetchval("SELECT current_user") == "esports_backend"
    finally:
        await backend.close()


@pytest.mark.asyncio
async def test_non_superuser_can_create_restricted_role():
    conn = await admin_connection()
    transaction = conn.transaction()
    await transaction.start()
    try:
        await conn.execute("CREATE ROLE local_role_creator_probe NOLOGIN CREATEROLE")
        await conn.execute("SET LOCAL ROLE local_role_creator_probe")
        assert not await conn.fetchval("SELECT rolsuper FROM pg_roles WHERE rolname=current_user")
        await conn.execute("CREATE ROLE local_runtime_probe NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS")
    finally:
        await transaction.rollback()
        await conn.close()
