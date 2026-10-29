import logging
from contextlib import redirect_stdout
from io import StringIO

import pytest

from sqlo import Q
from sqlo.query.select import SelectQuery

SQL_LINE = "[sqlo DEBUG] SELECT `id` FROM `users` WHERE `id` = %s"
PARAMS_LINE = "[sqlo DEBUG] Params: (1,)"


@pytest.fixture(autouse=True)
def _reset_debug():
    Q.set_debug(False)
    yield
    Q.set_debug(False)


def _build_and_capture(make=lambda: Q.select("id").from_("users").where("id", 1)):
    out = StringIO()
    with redirect_stdout(out):
        make().build()
    return out.getvalue()


# --- set_debug keeps working as before ------------------------------------


def test_set_debug_prints_the_query_and_its_params_to_stdout():
    Q.set_debug(True)
    assert _build_and_capture().splitlines() == [SQL_LINE, PARAMS_LINE]


def test_nothing_is_printed_by_default():
    assert _build_and_capture() == ""


def test_set_debug_false_stops_the_output():
    Q.set_debug(True)
    Q.set_debug(False)
    assert _build_and_capture() == ""


def test_output_follows_a_later_stdout_redirect():
    Q.set_debug(True)  # enabled before the redirect, like the existing tests do
    out = StringIO()
    with redirect_stdout(out):
        Q.select("id").from_("users").where("id", 1).build()
    assert SQL_LINE in out.getvalue()


def test_enabling_twice_still_logs_each_query_once():
    Q.set_debug(True)
    Q.set_debug(True)
    assert _build_and_capture().splitlines() == [SQL_LINE, PARAMS_LINE]


def test_queries_created_before_enabling_are_logged_too():
    query = Q.select("id").from_("users").where("id", 1)
    Q.set_debug(True)
    out = StringIO()
    with redirect_stdout(out):
        query.build()
    assert out.getvalue().splitlines() == [SQL_LINE, PARAMS_LINE]


@pytest.mark.parametrize(
    "make",
    [
        lambda: Q.insert_into("t").values({"a": 1}),
        lambda: Q.update("t").set({"a": 1}).where("id", 1),
        lambda: Q.delete_from("t").where("id", 1),
    ],
)
def test_every_query_type_is_logged(make):
    Q.set_debug(True)
    assert "[sqlo DEBUG] " in _build_and_capture(make)


# --- hiding parameters ------------------------------------------------------


def test_hide_params_keeps_the_sql_and_drops_the_values():
    Q.set_debug(True, hide_params=True)
    out = _build_and_capture(
        lambda: Q.insert_into("users").values({"password": "s3cret-value"})
    )
    assert "INSERT INTO `users`" in out
    assert "s3cret-value" not in out
    assert "Params" not in out


def test_params_are_shown_again_after_toggling():
    Q.set_debug(True, hide_params=True)
    Q.set_debug(True)
    assert PARAMS_LINE in _build_and_capture()


# --- standard logging integration -------------------------------------------


def test_records_reach_standard_logging_handlers_without_set_debug(caplog):
    with caplog.at_level(logging.DEBUG, logger="sqlo"):
        Q.select("id").from_("users").where("id", 1).build()
    assert [(r.name, r.getMessage()) for r in caplog.records] == [
        ("sqlo", "SELECT `id` FROM `users` WHERE `id` = %s"),
        ("sqlo.params", "Params: (1,)"),
    ]


def test_params_can_be_silenced_with_ordinary_logger_levels(caplog):
    params_logger = logging.getLogger("sqlo.params")
    params_logger.setLevel(logging.WARNING)
    try:
        with caplog.at_level(logging.DEBUG, logger="sqlo"):
            Q.select("id").from_("users").where("id", 1).build()
    finally:
        params_logger.setLevel(logging.NOTSET)
    assert [r.name for r in caplog.records] == ["sqlo"]


def test_nothing_is_logged_at_the_default_level(caplog):
    Q.select("id").from_("users").where("id", 1).build()
    assert caplog.records == []


def test_params_are_not_formatted_when_logging_is_off():
    class Probe:
        calls = 0

        def __repr__(self):
            Probe.calls += 1
            return "probe"

    Q.select("*").from_("t").where("a", Probe()).build()
    assert Probe.calls == 0


def test_disabling_restores_the_logger_state():
    logger = logging.getLogger("sqlo")
    before = (logger.level, logger.propagate, list(logger.handlers))
    Q.set_debug(True)
    assert logger.propagate is False and logger.level == logging.DEBUG
    Q.set_debug(False)
    assert (logger.level, logger.propagate, list(logger.handlers)) == before


def test_a_logger_level_set_by_the_user_survives_toggling():
    logger = logging.getLogger("sqlo")
    logger.setLevel(logging.INFO)
    try:
        Q.set_debug(True)
        Q.set_debug(False)
        assert logger.level == logging.INFO
    finally:
        logger.setLevel(logging.NOTSET)


# --- explicit debugging stays explicit --------------------------------------


def test_the_debug_method_still_prints():
    out = StringIO()
    with redirect_stdout(out):
        Q.select("id").from_("users").where("id", 1).debug()
    assert out.getvalue().splitlines()[:2] == [SQL_LINE, PARAMS_LINE]


def test_a_query_created_with_debug_true_prints_once_even_when_global_debug_is_on():
    Q.set_debug(True)
    out = StringIO()
    with redirect_stdout(out):
        SelectQuery("id", debug=True).from_("users").where("id", 1).build()
    assert out.getvalue().splitlines() == [SQL_LINE, PARAMS_LINE]
