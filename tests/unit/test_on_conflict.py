import pytest

from sqlo import Condition, Q, Raw, UnsupportedFeatureError, values_of
from sqlo.dialects.base import Dialect
from sqlo.dialects.postgresql import PostgreSQLDialect
from sqlo.expressions import Inserted
from sqlo.query.insert import InsertQuery
from sqlo.query.select import SelectQuery

PG = PostgreSQLDialect()


class PlainDialect(Dialect):
    @property
    def quote_char(self) -> str:
        return '"'

    def parameter_placeholder(self) -> str:
        return "?"


def _mysql(rows=None):
    return Q.insert_into("users").values(rows or {"id": 1, "name": "a"})


def _pg(rows=None):
    return InsertQuery("users", dialect=PG).values(rows or {"id": 1, "name": "a"})


# --- MySQL --------------------------------------------------------------------


def test_mysql_do_update_renders_on_duplicate_key_update():
    sql, params = _mysql().on_conflict("id").do_update({"name": values_of("name")}).build()
    assert sql == (
        "INSERT INTO `users` (`id`, `name`) VALUES (%s, %s) "
        "ON DUPLICATE KEY UPDATE `name` = VALUES(`name`)"
    )
    assert params == (1, "a")


def test_mysql_ignores_the_conflict_columns_and_does_not_need_them():
    with_cols = _mysql().on_conflict("id").do_update({"name": "x"}).build()
    without = _mysql().on_conflict().do_update({"name": "x"}).build()
    assert with_cols == without


def test_mysql_do_nothing_uses_the_noop_update_not_insert_ignore():
    sql, params = _mysql().on_conflict("id").do_nothing().build()
    assert sql == (
        "INSERT INTO `users` (`id`, `name`) VALUES (%s, %s) "
        "ON DUPLICATE KEY UPDATE `users`.`id` = `users`.`id`"
    )
    assert params == (1, "a")
    assert "IGNORE" not in sql
    assert _mysql().on_conflict().do_nothing().build() == (sql, params)


def test_mysql_do_nothing_with_insert_select_uses_the_first_selected_column():
    select = SelectQuery("a", "b").from_("src")
    sql, _ = (
        Q.insert_into("users").from_select(["a", "b"], select).on_conflict().do_nothing().build()
    )
    assert sql.endswith("ON DUPLICATE KEY UPDATE `users`.`a` = `users`.`a`")


def test_mysql_params_follow_sql_order_with_several_row_and_assignment_kinds():
    sql, params = (
        _mysql([{"id": 1, "name": "a"}, {"id": 2, "name": "b"}])
        .on_conflict("id")
        .do_update({"name": "plain", "n": Raw("`n` + %s", [5]), "x": values_of("x")})
        .build()
    )
    assert sql.endswith(
        "ON DUPLICATE KEY UPDATE `name` = %s, `n` = `n` + %s, `x` = VALUES(`x`)"
    )
    assert params == (1, "a", 2, "b", "plain", 5)


def test_the_legacy_method_still_accepts_values_of():
    sql, _ = _mysql().on_duplicate_key_update({"name": values_of("name")}).build()
    assert sql.endswith("ON DUPLICATE KEY UPDATE `name` = VALUES(`name`)")


# --- PostgreSQL ---------------------------------------------------------------


def test_postgresql_do_update_needs_and_renders_the_conflict_target():
    sql, params = _pg().on_conflict("id").do_update({"name": values_of("name")}).build()
    assert sql == (
        'INSERT INTO "users" ("id", "name") VALUES (%s, %s) '
        'ON CONFLICT ("id") DO UPDATE SET "name" = EXCLUDED."name"'
    )
    assert params == (1, "a")


def test_postgresql_composite_conflict_target():
    sql, _ = _pg().on_conflict("a", "b").do_update({"name": "x"}).build()
    assert 'ON CONFLICT ("a", "b") DO UPDATE SET "name" = %s' in sql


def test_postgresql_do_update_without_a_target_is_rejected_when_called():
    with pytest.raises(ValueError, match="conflict column"):
        _pg().on_conflict().do_update({"name": "x"})


def test_postgresql_do_nothing_with_and_without_a_target():
    assert _pg().on_conflict("id").do_nothing().build()[0].endswith('ON CONFLICT ("id") DO NOTHING')
    assert _pg().on_conflict().do_nothing().build()[0].endswith("ON CONFLICT DO NOTHING")


def test_postgresql_params_follow_sql_order():
    sql, params = (
        _pg([{"id": 1, "name": "a"}, {"id": 2, "name": "b"}])
        .on_conflict("id")
        .do_update({"name": "plain", "n": Raw('"n" + %s', [5])})
        .build()
    )
    assert params == (1, "a", 2, "b", "plain", 5)
    assert sql.endswith('DO UPDATE SET "name" = %s, "n" = "n" + %s')


def test_postgresql_insert_select_with_on_conflict():
    select = SelectQuery("id", "name", dialect=PG).from_("src")
    sql, _ = (
        InsertQuery("users", dialect=PG)
        .from_select(["id", "name"], select)
        .on_conflict("id")
        .do_nothing()
        .build()
    )
    assert sql == (
        'INSERT INTO "users" ("id", "name") SELECT "id", "name" FROM "src" '
        'ON CONFLICT ("id") DO NOTHING'
    )


def test_postgresql_rejects_the_mysql_forms_and_points_to_on_conflict():
    q = _pg()
    with pytest.raises(UnsupportedFeatureError, match="on_conflict"):
        q.ignore()
    with pytest.raises(UnsupportedFeatureError, match="on_conflict"):
        q.on_duplicate_key_update({"name": "x"})


# --- other dialects --------------------------------------------------------------


def test_a_portable_dialect_has_no_on_conflict():
    q = InsertQuery("t", dialect=PlainDialect()).values({"a": 1})
    with pytest.raises(UnsupportedFeatureError, match="ON CONFLICT"):
        q.on_conflict("a")


def test_inserted_value_needs_a_dialect_that_provides_it():
    class OnlyConflict(PlainDialect):
        supports_on_conflict = True

        def conflict_clause(self, target, assignments, first_column):
            return f" ON CONFLICT DO UPDATE SET {', '.join(assignments)}"

    q = (
        InsertQuery("t", dialect=OnlyConflict())
        .values({"a": 1})
        .on_conflict("a")
        .do_update({"a": values_of("a")})
    )
    with pytest.raises(UnsupportedFeatureError, match="inserted value"):
        q.build()


# --- validation ------------------------------------------------------------------


@pytest.mark.parametrize("bad", ["id; DROP TABLE x", "a b", "", "1a", "a..b"])
def test_conflict_columns_are_validated_when_called(bad):
    with pytest.raises(ValueError, match="Invalid identifier"):
        _mysql().on_conflict(bad)


def test_do_update_needs_a_non_empty_dict():
    with pytest.raises(ValueError, match="at least one"):
        _mysql().on_conflict("id").do_update({})
    with pytest.raises(TypeError):
        _mysql().on_conflict("id").do_update([("a", 1)])


def test_assignment_columns_are_validated_at_build():
    q = _mysql().on_conflict("id").do_update({"a; DROP TABLE x": 1})
    with pytest.raises(ValueError, match="Invalid identifier"):
        q.build()


def test_on_conflict_and_the_legacy_method_cannot_be_mixed():
    with pytest.raises(ValueError, match="on_duplicate_key_update"):
        _mysql().on_duplicate_key_update({"a": 1}).on_conflict("id")
    with pytest.raises(ValueError, match="on_conflict"):
        _mysql().on_conflict("id").do_nothing().on_duplicate_key_update({"a": 1})


def test_a_second_on_conflict_replaces_the_first():
    q = _mysql().on_conflict("id").do_nothing()
    q.on_conflict("id").do_update({"name": "z"})
    assert q.build()[0].endswith("ON DUPLICATE KEY UPDATE `name` = %s")


def test_a_pending_on_conflict_without_an_action_changes_nothing():
    q = _mysql()
    q.on_conflict("id")  # never completed
    assert q.build()[0] == "INSERT INTO `users` (`id`, `name`) VALUES (%s, %s)"


def test_on_conflict_actions_return_the_insert_query_so_chaining_continues():
    q = _mysql()
    assert q.on_conflict("id").do_nothing() is q
    assert q.on_conflict("id").do_update({"name": "x"}) is q


def test_clone_keeps_the_conflict_clause_independent():
    original = _mysql().on_conflict("id").do_update({"name": "x"})
    clone = original.clone()
    clone.on_conflict("id").do_nothing()
    assert original.build()[0].endswith("`name` = %s")
    assert clone.build()[0].endswith("`users`.`id` = `users`.`id`")


# --- values_of ------------------------------------------------------------------


def test_values_of_returns_a_lazy_node_not_sql_text():
    node = values_of("name")
    assert isinstance(node, Inserted)
    assert node.column == "name"


@pytest.mark.parametrize("bad", ["name); DROP TABLE x;--", "a b", "", "1a", "t.name"])
def test_values_of_accepts_only_a_plain_column_name(bad):
    with pytest.raises(ValueError):
        values_of(bad)


def test_values_of_is_rejected_where_it_would_be_bound_as_a_value():
    # INSERT ... VALUES is not checked cell by cell: that would double the cost of
    # a bulk insert, and a database driver cannot adapt the node anyway.
    with pytest.raises(TypeError, match="upsert"):
        Q.update("t").set({"a": values_of("b")})
    with pytest.raises(TypeError, match="upsert"):
        Condition("a", values_of("b"))
