from sqlalchemy.engine import make_url


def database_options(raw_url: str):
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql://", 1)
    url = make_url(raw_url).set(drivername="postgresql+asyncpg")
    args = {"prepared_statement_cache_size": 0, "statement_cache_size": 0}
    if "sslmode" in url.query:
        args["ssl"] = url.query["sslmode"]
        url = url.difference_update_query(["sslmode"])
    elif "ssl" not in url.query and url.host not in (None, "localhost", "127.0.0.1", "::1"):
        args["ssl"] = "require"
    return url, args
