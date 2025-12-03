"""Tests for batch update functionality."""

import pytest

from sqlo import Q


def test_batch_update_basic():
    """Test basic batch update with CASE WHEN."""
    values = [
        {"id": 1, "name": "Alice", "role": "admin"},
        {"id": 2, "name": "Bob", "role": "user"},
    ]

    q = Q.update("users").batch_update(values, key="id")
    sql, params = q.build()

    # Verify SQL structure
    assert "UPDATE `users` SET" in sql
    assert "CASE `id`" in sql
    assert "WHEN %s THEN %s" in sql
    assert "WHERE `id` IN (%s, %s)" in sql

    # Verify params count (4 for name + 4 for role + 2 for WHERE IN = 10)
    assert len(params) == 10
    assert params == (1, "Alice", 2, "Bob", 1, "admin", 2, "user", 1, 2)


def test_batch_update_single_column():
    """Test batch update with single column."""
    values = [
        {"id": 1, "status": "active"},
        {"id": 2, "status": "inactive"},
    ]

    q = Q.update("users").batch_update(values, key="id")
    sql, params = q.build()

    assert "CASE `id`" in sql
    assert "WHERE `id` IN (%s, %s)" in sql
    assert len(params) == 6  # 2*2 for CASE + 2 for WHERE IN


def test_batch_update_empty_values():
    """Test batch update with empty values list."""
    q = Q.update("users").batch_update([], key="id")

    # Should not raise error, just return self
    assert q._values == {}


def test_batch_update_missing_key():
    """Test batch update with missing key in values."""
    values = [{"name": "Alice"}]

    with pytest.raises(ValueError, match="Key 'id' not found"):
        Q.update("users").batch_update(values, key="id")
