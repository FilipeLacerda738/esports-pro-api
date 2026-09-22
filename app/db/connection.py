import ssl

from sqlalchemy.engine import make_url

from app.core.config import Settings


def database_connection_options(config: Settings):
    url = make_url(config.DATABASE_URL)
    if url.drivername not in {"postgres", "postgresql", "postgresql+asyncpg"}:
        raise ValueError("Only PostgreSQL with asyncpg is supported")
    url = url.set(drivername="postgresql+asyncpg")
    # URL parameters must never override the application's TLS policy.
    url = url.difference_update_query([
        "ssl", "sslmode", "sslrootcert", "sslcert", "sslkey",
        "sslcrl", "sslpassword", "ssl_min_protocol_version", "ssl_max_protocol_version",
    ])
    ssl_context = False
    if config.DATABASE_SSL:
        ssl_context = ssl.create_default_context(cafile=config.DATABASE_CA_FILE)
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
    return url, {
        "ssl": ssl_context,
        "prepared_statement_cache_size": 0,
        "statement_cache_size": 0,
        "timeout": 10,
        "command_timeout": 30,
    }
