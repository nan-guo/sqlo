import pytest

from sqlo import Q


def test_row_missing_a_column_is_rejected():
    with pytest.raises(ValueError, match="Row 1"):
        Q.insert_into("u").values([{"a": 1, "b": 2}, {"a": 3}])


def test_row_with_an_extra_column_is_rejected():
    with pytest.raises(ValueError, match="Row 1"):
        Q.insert_into("u").values([{"a": 1}, {"a": 2, "b": 3}])


def test_row_with_different_columns_is_rejected():
    with pytest.raises(ValueError):
        Q.insert_into("u").values([{"a": 1}, {"b": 2}])


def test_error_lists_the_expected_columns():
    with pytest.raises(ValueError, match=r"\['a', 'b'\]"):
        Q.insert_into("u").values([{"a": 1, "b": 2}, {"a": 3}])


def test_columns_are_matched_across_values_calls():
    q = Q.insert_into("u").values({"a": 1})
    with pytest.raises(ValueError):
        q.values({"b": 2})
    with pytest.raises(ValueError):
        q.values([{"a": 2}, {"a": 3, "b": 4}])


def test_rejected_values_do_not_modify_the_query():
    q = Q.insert_into("u").values({"a": 1})
    with pytest.raises(ValueError):
        q.values([{"a": 2}, {"b": 3}])
    sql, params = q.build()
    assert sql == "INSERT INTO `u` (`a`) VALUES (%s)"
    assert params == (1,)


def test_key_order_may_differ_and_follows_the_first_row():
    sql, params = (
        Q.insert_into("u").values([{"a": 1, "b": 2}, {"b": 4, "a": 3}]).build()
    )
    assert sql == "INSERT INTO `u` (`a`, `b`) VALUES (%s, %s), (%s, %s)"
    assert params == (1, 2, 3, 4)


def test_dict_then_list_with_the_same_columns_is_accepted():
    sql, params = (
        Q.insert_into("u").values({"a": 1}).values([{"a": 2}, {"a": 3}]).build()
    )
    assert sql == "INSERT INTO `u` (`a`) VALUES (%s), (%s), (%s)"
    assert params == (1, 2, 3)


@pytest.mark.parametrize("bad", [(), ({"a": 1},), "x", 5, None, {"a": 1}.items()])
def test_values_rejects_unsupported_types(bad):
    with pytest.raises(TypeError):
        Q.insert_into("u").values(bad)


@pytest.mark.parametrize("bad_row", [[1, 2], "x", None, ("a", 1)])
def test_values_rejects_non_dict_rows(bad_row):
    with pytest.raises(TypeError):
        Q.insert_into("u").values([{"a": 1}, bad_row])


def test_empty_list_is_still_accepted_and_fails_at_build():
    q = Q.insert_into("u").values([])
    with pytest.raises(ValueError, match="No values to insert"):
        q.build()


def test_invalid_column_names_are_still_rejected_at_build():
    q = Q.insert_into("u").values([{"a; DROP TABLE x": 1}])
    with pytest.raises(ValueError, match="Invalid identifier"):
        q.build()


@pytest.mark.parametrize("bad_row", [1, "x", None, ["a"]])
def test_values_rejects_a_non_dict_first_row(bad_row):
    with pytest.raises(TypeError):
        Q.insert_into("u").values([bad_row])
    with pytest.raises(TypeError):
        Q.insert_into("u").values([bad_row, {"a": 1}])
