"""Tests for security utilities."""

from sqlo import security


class TestValidateIdentifier:
    """Test validate_identifier function."""

    def test_valid_identifiers(self):
        """Test valid identifier patterns."""
        assert security.validate_identifier("users") is True
        assert security.validate_identifier("user_id") is True
        assert security.validate_identifier("users_table") is True
        assert security.validate_identifier("users.id") is True
        assert security.validate_identifier("table1") is True
        assert security.validate_identifier("_private") is True

    def test_invalid_identifiers(self):
        """Test invalid identifier patterns."""
        assert security.validate_identifier("users; DROP TABLE users; --") is False
        assert security.validate_identifier("123invalid") is False
        assert security.validate_identifier("") is False
        assert security.validate_identifier("users'") is False
        assert security.validate_identifier("users--") is False
        assert security.validate_identifier("users/*") is False

    def test_allow_dot_false(self):
        """Test allow_dot parameter."""
        assert security.validate_identifier("users.id", allow_dot=True) is True
        assert security.validate_identifier("users.id", allow_dot=False) is False

    def test_non_string_input(self):
        """Test non-string input."""
        assert security.validate_identifier(None) is False
        assert security.validate_identifier(123) is False
        assert security.validate_identifier([]) is False


class TestValidateIdentifiers:
    """Test validate_identifiers function."""

    def test_all_valid(self):
        """Test all valid identifiers."""
        assert security.validate_identifiers(["users", "orders", "products"]) is True

    def test_some_invalid(self):
        """Test some invalid identifiers."""
        assert (
            security.validate_identifiers(["users", "orders; DROP TABLE users; --"])
            is False
        )

    def test_empty_list(self):
        """Test empty list."""
        assert security.validate_identifiers([]) is True


class TestValidateIdentifierWhitelist:
    """Test validate_identifier_whitelist function."""

    def test_in_whitelist(self):
        """Test identifier in whitelist."""
        whitelist = {"users", "orders", "products"}
        assert security.validate_identifier_whitelist("users", whitelist) is True
        assert security.validate_identifier_whitelist("orders", whitelist) is True

    def test_not_in_whitelist(self):
        """Test identifier not in whitelist."""
        whitelist = {"users", "orders", "products"}
        assert (
            security.validate_identifier_whitelist("malicious_table", whitelist)
            is False
        )
        assert security.validate_identifier_whitelist("users; DROP", whitelist) is False

    def test_case_sensitive(self):
        """Test case sensitivity."""
        whitelist = {"users", "orders"}
        assert (
            security.validate_identifier_whitelist(
                "Users", whitelist, case_sensitive=True
            )
            is False
        )
        assert (
            security.validate_identifier_whitelist(
                "Users", whitelist, case_sensitive=False
            )
            is True
        )

    def test_non_string_input(self):
        """Test non-string input."""
        whitelist = {"users", "orders"}
        assert security.validate_identifier_whitelist(None, whitelist) is False
        assert security.validate_identifier_whitelist(123, whitelist) is False


class TestEscapeIdentifier:
    """Test escape_identifier function."""

    def test_simple_identifier(self):
        """Test escaping simple identifier."""
        assert security.escape_identifier("users") == "`users`"

    def test_identifier_with_dot(self):
        """Test escaping identifier with dot."""
        assert security.escape_identifier("users.id") == "`users`.`id`"

    def test_multiple_dots(self):
        """Test escaping identifier with multiple dots."""
        assert security.escape_identifier("db.users.id") == "`db`.`users`.`id`"

    def test_custom_quote_char(self):
        """Test custom quote character."""
        assert security.escape_identifier("users", quote_char='"') == '"users"'

    def test_empty_string(self):
        """Test empty string."""
        assert security.escape_identifier("") == ""
