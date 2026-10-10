DO $block$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'esports_backend') THEN
        CREATE ROLE esports_backend NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_roles
        WHERE rolname = 'esports_backend'
          AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls)
    ) OR EXISTS (
        SELECT 1 FROM pg_auth_members
        WHERE member = (SELECT oid FROM pg_roles WHERE rolname = 'esports_backend')
    ) THEN
        RAISE EXCEPTION 'esports_backend must not have administrative privileges or role memberships';
    END IF;
END
$block$;

REVOKE ALL ON SCHEMA public FROM PUBLIC, anon, authenticated;
GRANT USAGE ON SCHEMA public TO postgres, service_role, esports_backend;

REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC, anon, authenticated, esports_backend;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC, anon, authenticated, esports_backend;
REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA public FROM PUBLIC, anon, authenticated, esports_backend;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON TABLES FROM PUBLIC, anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON SEQUENCES FROM PUBLIC, anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC, anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC, anon, authenticated;

GRANT SELECT, INSERT, UPDATE ON public.teams, public.leagues, public.matches, public.players, public.game_maps TO esports_backend;
GRANT DELETE ON public.matches TO esports_backend;
GRANT USAGE ON SEQUENCE public.teams_id_seq, public.leagues_id_seq, public.matches_id_seq TO esports_backend;

ALTER TABLE public.teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.leagues ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.players ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.game_maps ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alembic_version ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS esports_backend_access ON public.teams;
CREATE POLICY esports_backend_access ON public.teams TO esports_backend USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS esports_backend_access ON public.leagues;
CREATE POLICY esports_backend_access ON public.leagues TO esports_backend USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS esports_backend_access ON public.matches;
CREATE POLICY esports_backend_access ON public.matches TO esports_backend USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS esports_backend_access ON public.players;
CREATE POLICY esports_backend_access ON public.players TO esports_backend USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS esports_backend_access ON public.game_maps;
CREATE POLICY esports_backend_access ON public.game_maps TO esports_backend USING (true) WITH CHECK (true);

NOTIFY pgrst, 'reload schema';
