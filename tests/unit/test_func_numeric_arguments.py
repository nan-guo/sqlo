import enum

from sqlo import Q, func


class Color(enum.IntEnum):
    RED = 1


class Evil(float):
    def __repr__(self):
        return "1); DROP TABLE x;--"


def test_func_argument_of_an_int_subclass_renders_as_a_number():
    sql, _ = Q.select(func.sum(Color.RED)).from_("t").build()
    assert sql == "SELECT SUM(1) FROM `t`"


def test_func_argument_of_a_float_subclass_ignores_its_repr():
    sql, _ = Q.select(func.sum(Evil(1.5))).from_("t").build()
    assert sql == "SELECT SUM(1.5) FROM `t`"
