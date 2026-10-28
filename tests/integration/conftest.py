"""Run the SQL sqlo builds on real MySQL and PostgreSQL servers.

Point the tests at servers with these environment variables; without them the
tests are skipped, so a plain ``pytest`` needs no database::

    SQLO_TEST_MYSQL_URL=mysql://user:password@127.0.0.1:3306/dbname
    SQLO_TEST_POSTGRES_URL=postgresql://user:password@127.0.0.1:5432/dbname

``make db-up`` starts both with the right settings, and ``make test-integration``
runs the tests against them. The tests create the tables ``u``, ``v``, ``o`` and
``w`` in the given database and run every test in a transaction that is rolled
back.
"""

import os
from urllib.parse import unquote, urlparse

import pytest

from sqlo import MySQLDialect, PostgreSQLDialect, Q

MYSQL_URL = os.environ.get("SQLO_TEST_MYSQL_URL")
POSTGRES_URL = os.environ.get("SQLO_TEST_POSTGRES_URL")

# The same logical data in both databases
_ROWS_U = [
    (1, 1, 1, "x", '{"a": {"b": 5, "c": [1, {"b": 9}]}, "list": [10, 20]}', "2024-01-01"),
    (2, 2, 2, "y", '{"a": {"b": 6}}', "2024-01-02"),
    (3, 3, 3, "z", None, "2024-01-03"),
]
_SCHEMA = {
    "mysql": [
        "CREATE TABLE u (id INT PRIMARY KEY, a INT, b INT, name VARCHAR(50), d JSON, ts DATE)",
        "CREATE TABLE v (id INT PRIMARY KEY, k INT)",
        "CREATE TABLE o (id INT PRIMARY KEY, user_id INT, total INT)",
        "CREATE TABLE w (id INT PRIMARY KEY, s VARCHAR(2))",
    ],
    "postgresql": [
        "CREATE TABLE u (id INT PRIMARY KEY, a INT, b INT, name TEXT, d JSONB, ts DATE)",
        "CREATE TABLE v (id INT PRIMARY KEY, k INT)",
        "CREATE TABLE o (id INT PRIMARY KEY, user_id INT, total INT)",
        "CREATE TABLE w (id INT PRIMARY KEY, s VARCHAR(2))",
    ],
}


def _connect_mysql():
    pymysql = pytest.importorskip("pymysql")
    url = urlparse(MYSQL_URL)
    return pymysql.connect(
        host=url.hostname,
        port=url.port or 3306,
        user=unquote(url.username or ""),
        password=unquote(url.password or ""),
        database=url.path.lstrip("/"),
        autocommit=False,
    )


def _connect_postgresql():
    psycopg = pytest.importorskip("psycopg")
    return psycopg.connect(POSTGRES_URL, autocommit=False)


_CONNECT = {"mysql": _connect_mysql, "postgresql": _connect_postgresql}
_URL = {"mysql": lambda: MYSQL_URL, "postgresql": lambda: POSTGRES_URL}
_ENV = {"mysql": "SQLO_TEST_MYSQL_URL", "postgresql": "SQLO_TEST_POSTGRES_URL"}


def _seed(engine):
    conn = _CONNECT[engine]()
    cur = conn.cursor()
    for table in ("o", "u", "v", "w"):
        cur.execute(f"DROP TABLE IF EXISTS {table}")
    for statement in _SCHEMA[engine]:
        cur.execute(statement)
    cur.executemany(
        "INSERT INTO u VALUES (%s, %s, %s, %s, %s, %s)", _ROWS_U
    )
    cur.executemany("INSERT INTO v VALUES (%s, %s)", [(1, 10), (2, 20)])
    cur.executemany("INSERT INTO o VALUES (%s, %s, %s)", [(1, 1, 100), (2, 1, 200), (3, 2, 50)])
    conn.commit()
    conn.close()


class Database:
    """A connection in an open transaction, plus a query factory for its dialect."""

    def __init__(self, name, conn, dialect):
        self.name = name
        self.conn = conn
        self.dialect = dialect
        self.q = Q.using(dialect)

    def run(self, query):
        """Build and execute a sqlo query. Rows (as tuples), or the affected row count."""
        sql, params = query.build()
        return self.execute(sql, params)

    def execute(self, sql, params=()):
        cur = self.conn.cursor()
        cur.execute(sql, params)
        if cur.description is None:
            return cur.rowcount
        return [tuple(row) for row in cur.fetchall()]

    def rows(self, sql):
        """Read rows with a plain SQL string, quoting identifiers for this engine."""
        quote = self.dialect.quote_char
        return self.execute(sql.replace("`", quote))


def _database(engine):
    if not _URL[engine]():
        pytest.skip(f"{_ENV[engine]} is not set")
    conn = _CONNECT[engine]()
    dialect = MySQLDialect() if engine == "mysql" else PostgreSQLDialect()
    db = Database(engine, conn, dialect)
    try:
        yield db
    finally:
        conn.rollback()
        conn.close()


@pytest.fixture(scope="session", autouse=True)
def _schema():
    """Create the tables once per session, for every engine that is configured."""
    for engine in ("mysql", "postgresql"):
        if _URL[engine]():
            _seed(engine)


@pytest.fixture(params=["mysql", "postgresql"])
def db(request):
    """Every test that uses it runs once per database."""
    yield from _database(request.param)


@pytest.fixture
def mysql():
    yield from _database("mysql")


@pytest.fixture
def pg():
    yield from _database("postgresql")


def numbers(rows):
    """Normalize numeric results: MySQL returns Decimal where PostgreSQL returns int."""
    return [tuple(int(v) if hasattr(v, "as_integer_ratio") and not isinstance(v, bool) else v for v in row) for row in rows]
