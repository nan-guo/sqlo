from sqlo import Q
from sqlo.dialects.mysql import MySQLDialect
from sqlo.query.mixins import WhereClauseMixin


class MockQuery(WhereClauseMixin):
    def __init__(self):
        self._dialect = MySQLDialect()
        self._ph = self._dialect.parameter_placeholder()
        self._wheres = []

    def where(self, column, value=None, operator="="):
        # Simple mock implementation
        connector, sql, params = self._build_where_clause(column, value, operator)
        self._wheres.append((connector, sql, params))
        return self


def test_or_where():
    q = MockQuery()
    q.or_where("id", 1)
    assert q._wheres == [("OR", "`id` = %s", [1])]


def test_where_in_subquery_mixin():
    q = MockQuery()
    sub = Q.select("id").from_("users")
    q.where_in("user_id", sub)
    assert q._wheres[0][0] == "AND"
    assert "IN (SELECT `id` FROM `users`)" in q._wheres[0][1]


def test_mixin_methods():
    """Test all mixin methods directly to ensure coverage"""
    q = MockQuery()

    # where_in / or_where_in / where_not_in / or_where_not_in
    q.where_in("id", [1])
    q.or_where_in("id", [2])
    q.where_not_in("id", [3])
    q.or_where_not_in("id", [4])

    # where_null / or_where_null / where_not_null / or_where_not_null
    q.where_null("a")
    q.or_where_null("b")
    q.where_not_null("c")
    q.or_where_not_null("d")

    # where_between / or_where_between / where_not_between / or_where_not_between
    q.where_between("x", 1, 2)
    q.or_where_between("x", 3, 4)
    q.where_not_between("x", 5, 6)
    q.or_where_not_between("x", 7, 8)

    # where_like / or_where_like / where_not_like / or_where_not_like
    q.where_like("name", "A%")
    q.or_where_like("name", "B%")
    q.where_not_like("name", "C%")
    q.or_where_not_like("name", "D%")

    # Expected total number of where conditions
    expected_conditions = 16
    assert len(q._wheres) == expected_conditions
