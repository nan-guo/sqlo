import pytest

from sqlo import Condition, Q
from sqlo.expressions import JSON
from sqlo.security import validate_operator

MALICIOUS = [
    "= 1 OR 1=1 --",
    "=; DROP TABLE x",
    "LIKE '%' OR",
    "MY_OP",
    "",
    "=\n1 OR 1=1",
]


@pytest.mark.parametrize("op", MALICIOUS)
def test_where_operator_argument_rejected(op):
    with pytest.raises(ValueError):
        Q.select("*").from_("u").where("a", 1, op)


@pytest.mark.parametrize("op", MALICIOUS)
def test_having_operator_argument_rejected(op):
    with pytest.raises(ValueError):
        Q.select("a").from_("u").group_by("a").having("a", 1, op)


@pytest.mark.parametrize("op", [op for op in MALICIOUS if op])
def test_embedded_spaced_operator_rejected(op):
    with pytest.raises(ValueError):
        Q.select("*").from_("u").where(f"a {op}", 1)


def test_embedded_compact_operator_rejected():
    # Matches COMPACT_PATTERN but is not a known operator
    with pytest.raises(ValueError):
        Q.select("*").from_("u").where("a=!<", 1)


@pytest.mark.parametrize("op", MALICIOUS)
def test_condition_operator_rejected(op):
    with pytest.raises(ValueError):
        Condition("a", 1, op)


def test_condition_embedded_operator_rejected():
    with pytest.raises(ValueError):
        Condition("a = 1 OR 1=1 --", 1)


def test_jsonpath_where_operator_rejected():
    with pytest.raises(ValueError):
        Q.select("*").from_("u").where(JSON("d").extract("a"), 1, "= 1 OR 1=1 --")


def test_update_and_delete_where_operator_rejected():
    with pytest.raises(ValueError):
        Q.update("u").set({"a": 1}).where("id", 1, "= 1 OR 1=1 --")
    with pytest.raises(ValueError):
        Q.delete_from("u").where("id", 1, "= 1 OR 1=1 --")


@pytest.mark.parametrize(
    "op",
    ["=", "!=", "<>", "<", "<=", ">", ">=", "<=>", "LIKE", "NOT LIKE", "REGEXP",
     "NOT REGEXP", "IN", "NOT IN", "IS", "IS NOT", "IS NULL", "IS NOT NULL"],
)  # fmt: skip
def test_known_operators_accepted(op):
    assert validate_operator(op) == op


def test_operator_is_normalized():
    assert validate_operator("not   like") == "NOT LIKE"
    sql, _ = Q.select("*").from_("u").where("name not like", "x%").build()
    assert sql == "SELECT * FROM `u` WHERE `name` NOT LIKE %s"


def test_validate_operator_rejects_non_str():
    with pytest.raises(ValueError):
        validate_operator(None)  # type: ignore[arg-type]
