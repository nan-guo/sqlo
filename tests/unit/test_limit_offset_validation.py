import pytest

from sqlo import Q

BAD_TYPES = ["1; DROP TABLE x", 1.5, None, True, [1], "10"]


@pytest.mark.parametrize("bad", BAD_TYPES)
def test_select_limit_rejects_non_int(bad):
    with pytest.raises(TypeError):
        Q.select("*").from_("users").limit(bad)


@pytest.mark.parametrize("bad", BAD_TYPES)
def test_select_offset_rejects_non_int(bad):
    with pytest.raises(TypeError):
        Q.select("*").from_("users").offset(bad)


@pytest.mark.parametrize("bad", BAD_TYPES)
def test_update_delete_limit_reject_non_int(bad):
    with pytest.raises(TypeError):
        Q.update("users").limit(bad)
    with pytest.raises(TypeError):
        Q.delete_from("users").limit(bad)


def test_negative_limit_and_offset_rejected():
    with pytest.raises(ValueError):
        Q.select("*").from_("users").limit(-1)
    with pytest.raises(ValueError):
        Q.select("*").from_("users").offset(-1)
    with pytest.raises(ValueError):
        Q.update("users").limit(-1)
    with pytest.raises(ValueError):
        Q.delete_from("users").limit(-1)


def test_zero_limit_and_offset_allowed():
    sql, _ = Q.select("*").from_("users").limit(0).offset(0).build()
    assert sql == "SELECT * FROM `users` LIMIT 0"


@pytest.mark.parametrize("bad", ["1", 1.5, None, True])
def test_paginate_rejects_non_int(bad):
    with pytest.raises(TypeError):
        Q.select("*").from_("users").paginate(bad, 10)
    with pytest.raises(TypeError):
        Q.select("*").from_("users").paginate(1, bad)


@pytest.mark.parametrize("per_page", [0, -1])
def test_paginate_rejects_non_positive_per_page(per_page):
    with pytest.raises(ValueError):
        Q.select("*").from_("users").paginate(1, per_page)
