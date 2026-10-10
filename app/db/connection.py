from sqlalchemy.engine import make_url
import ssl
from pathlib import Path


def database_options(raw_url: str):
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql://", 1)
    url = make_url(raw_url).set(drivername="postgresql+asyncpg")
    args = {"prepared_statement_cache_size": 0, "statement_cache_size": 0, "timeout": 10, "command_timeout": 15}
    rootcert = url.query.get("sslrootcert")
    if not rootcert and url.host and url.host.endswith(".pooler.supabase.com"):
        rootcert = "security/supabase-ca.crt"
        url = url.update_query_dict({"sslmode": "verify-full"})
    if rootcert:
        if url.query.get("sslmode") != "verify-full":
            raise ValueError("sslrootcert requires sslmode=verify-full")
        certificate = Path(rootcert)
        if not certificate.is_absolute():
            certificate = Path(__file__).resolve().parents[2] / certificate
        context = ssl.create_default_context(cafile=str(certificate))
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        if url.host and url.host.endswith(".pooler.supabase.com"):
            context.verify_flags &= ~ssl.VERIFY_X509_STRICT
        args["ssl"] = context
        url = url.difference_update_query(["sslmode", "sslrootcert"])
    elif "sslmode" in url.query:
        args["ssl"] = url.query["sslmode"]
        url = url.difference_update_query(["sslmode"])
    elif "ssl" not in url.query and url.host not in (None, "localhost", "127.0.0.1", "::1"):
        args["ssl"] = "require"
    return url, args
