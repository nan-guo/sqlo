from sqlo import Q
from sqlo.query.delete import DeleteQuery
from sqlo.query.insert import InsertQuery
from sqlo.query.select import SelectQuery
from sqlo.query.update import UpdateQuery


def test_select_query_stays_subscriptable_for_type_hints():
    """`SelectQuery[Row]` is part of the public typing surface and keeps working."""
    assert SelectQuery[int] is not None
    assert isinstance(Q.select("a"), SelectQuery)


def test_queries_do_not_declare_ineffective_slots():
    """A __slots__ on a subclass of a class without slots saves nothing.

    The base classes keep a __dict__, so the declarations only misled readers.
    """
    for cls in (SelectQuery, UpdateQuery, DeleteQuery, InsertQuery):
        assert "__slots__" not in vars(cls), cls.__name__
