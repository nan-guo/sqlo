import pytest

from sqlo import Q


def _update():
    return Q.update("users")


def test_row_missing_a_column_is_rejected():
    rows = [{"id": 1, "a": 1, "b": 2}, {"id": 2, "a": 3}]
    with pytest.raises(ValueError, match="Row 1"):
        _update().batch_update(rows, key="id")


def test_row_with_an_extra_column_is_rejected():
    rows = [{"id": 1, "a": 1}, {"id": 2, "a": 3, "b": 4}]
    with pytest.raises(ValueError, match="Row 1"):
        _update().batch_update(rows, key="id")


def test_key_missing_from_a_later_row_is_rejected():
    rows = [{"id": 1, "a": 1}, {"a": 3}]
    with pytest.raises(ValueError, match="Row 1"):
        _update().batch_update(rows, key="id")


def test_key_missing_from_the_first_row_keeps_its_message():
    with pytest.raises(ValueError, match="Key 'id' not found"):
        _update().batch_update([{"a": 1}, {"a": 2}], key="id")


def test_error_lists_the_expected_columns():
    rows = [{"id": 1, "a": 1}, {"id": 2, "b": 3}]
    with pytest.raises(ValueError, match=r"\['id', 'a'\]"):
        _update().batch_update(rows, key="id")


def test_duplicate_key_values_are_rejected():
    rows = [{"id": 1, "a": 1}, {"id": 2, "a": 2}, {"id": 1, "a": 3}]
    with pytest.raises(ValueError, match="Duplicate"):
        _update().batch_update(rows, key="id")


@pytest.mark.parametrize("bad_row", [[1, 2], "x", None, ("id", 1)])
def test_non_dict_rows_are_rejected(bad_row):
    with pytest.raises(TypeError):
        _update().batch_update([{"id": 1, "a": 1}, bad_row], key="id")
    with pytest.raises(TypeError):
        _update().batch_update([bad_row], key="id")


def test_failed_validation_leaves_the_query_untouched():
    q = _update()
    with pytest.raises(ValueError):
        q.batch_update([{"id": 1, "a": 1}, {"id": 2}], key="id")
    assert q._values == {}
    assert q._wheres == []


def test_key_order_may_differ_between_rows():
    rows = [{"id": 1, "a": 10, "b": 20}, {"b": 40, "id": 2, "a": 30}]
    sql, params = _update().batch_update(rows, key="id").build()
    assert sql == (
        "UPDATE `users` SET "
        "`a` = CASE `id` WHEN %s THEN %s WHEN %s THEN %s END, "
        "`b` = CASE `id` WHEN %s THEN %s WHEN %s THEN %s END "
        "WHERE `id` IN (%s, %s)"
    )
    assert params == (1, 10, 2, 30, 1, 20, 2, 40, 1, 2)


def test_empty_values_is_still_a_noop():
    q = _update()
    assert q.batch_update([], key="id") is q
    assert q._values == {} and q._wheres == []


def test_rows_with_only_the_key_still_work_with_a_separate_set():
    sql, params = (
        _update()
        .set({"flag": True})
        .batch_update([{"id": 1}, {"id": 2}], key="id")
        .build()
    )
    assert sql == "UPDATE `users` SET `flag` = %s WHERE `id` IN (%s, %s)"
    assert params == (True, 1, 2)


def test_invalid_column_names_are_still_rejected():
    q = _update().batch_update([{"id": 1, "a; DROP TABLE x": 2}], key="id")
    with pytest.raises(ValueError, match="Invalid identifier"):
        q.build()
    with pytest.raises(ValueError, match="Invalid identifier"):
        _update().batch_update([{"id; DROP": 1, "a": 2}], key="id; DROP")
