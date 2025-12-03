from typing import TYPE_CHECKING, Any, Optional, Union

from .constants import COMPACT_PATTERN

if TYPE_CHECKING:
    from .query.select import SelectQuery


class Expression:
    """Base class for SQL expressions."""

    alias: Optional[str] = None

    def as_(self, alias: str) -> "Expression":
        """Set an alias for the expression."""
        self.alias = alias
        return self


class Raw(Expression):
    """Raw SQL fragment.

    WARNING: Raw SQL bypasses parameter binding and can be vulnerable to SQL injection.
    Only use Raw() with trusted input or when you need to reference columns/functions.

    For dynamic user input, always use parameterized queries instead.
    """

    def __init__(
        self,
        sql: str,
        params: Optional[Union[list[Any], tuple[Any, ...]]] = None,
    ):
        if not isinstance(sql, str):
            raise TypeError("Raw SQL must be a string")
        self.sql = sql
        self.params = params or []


class Func(Expression):
    """
    Represents a SQL function call.

    This class allows you to wrap any SQL function (e.g., COUNT, MAX, AVG, custom functions)
    and use it within your queries. It supports arguments and aliasing.

    Args:
        name (str): The name of the SQL function (e.g., "COUNT").
        *args (Any): Arguments to pass to the function.

    Example:
        >>> f = Func("COUNT", "*")
        >>> f.as_("total")
    """

    def __init__(self, name: str, *args: Any):
        self.name = name
        self.args = args
        self.alias: Optional[str] = None

    def over(self, window: Optional[Any] = None) -> Any:
        """
        Create a window function with OVER clause.

        Args:
            window: Optional Window object for PARTITION BY / ORDER BY

        Returns:
            WindowFunc object

        Example:
            >>> func.row_number().over(Window.partition_by("dept"))
        """
        from .window import WindowFunc

        return WindowFunc(self.name, self.args, window)


class FunctionFactory:
    """Factory for creating SQL function expressions."""

    def __init__(self):
        pass

    def __getattr__(self, name: str):
        if name.startswith("_"):
            # Avoid private attributes
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            )

        def _create(*args: Any) -> Func:
            return Func(name.upper(), *args)

        return _create

    @staticmethod
    def count(expression: str = "*") -> Func:
        return Func("COUNT", expression)

    @staticmethod
    def sum(expression: str) -> Func:
        return Func("SUM", expression)

    @staticmethod
    def avg(expression: str) -> Func:
        return Func("AVG", expression)

    @staticmethod
    def min(expression: str) -> Func:
        return Func("MIN", expression)

    @staticmethod
    def max(expression: str) -> Func:
        return Func("MAX", expression)


class Condition(Expression):
    r"""
    Represents a SQL condition for use in WHERE or HAVING clauses.

    This class allows you to build simple or complex conditions with support for
    compact operator syntax (e.g., "age>") and standard syntax (e.g., "age >").
    Conditions can be combined using bitwise operators (& and \|) or static methods.

    Args:
        column (str, optional): Column name with optional operator (e.g., "age>=" or "age >=").
        value (Any, optional): The value to compare against. Can be a list for IN operator.
        operator (str, optional): The comparison operator if not included in column. Defaults to "=".

    Examples:
        >>> # Simple condition
        >>> c = Condition("age>=", 18)
        >>> sql, params = c.build()
        >>>
        >>> # IN operator
        >>> c = Condition("status", ["pending", "done"], operator="IN")
        >>>
        >>> # IS NULL
        >>> c = Condition("deleted_at", operator="IS NULL")
        >>>
        >>> # Static factory methods
        >>> c = Condition.null("deleted_at")
        >>> c = Condition.in_("status", ["pending", "done"])
        >>> c = Condition.exists(subquery)
        >>>
        >>> # Combining conditions
        >>> c1 = Condition("age>=", 18)
        >>> c2 = Condition("country", "US")
        >>> combined = c1 & c2  # AND
        >>> combined = c1 \| c2  # OR
    """

    def __init__(
        self,
        column: Optional[str] = None,
        value: Any = None,
        operator: str = "=",
    ):
        from .dialects.mysql import MySQLDialect

        self.parts: list[tuple[str, Any]] = []  # (sql, params)
        self.connector = "AND"
        self._dialect = MySQLDialect()

        if column:
            self._add_condition(column, value, operator)

    def _add_condition(self, column: str, value: Any, operator: str) -> None:
        """Add a condition to this Condition object."""
        col_name = None
        op = None

        # Parse column for embedded operator (e.g., "age>=")
        if isinstance(column, str):
            if " " in column:
                parts = column.split(" ", 1)
                col_name = parts[0]
                op = parts[1]
            else:
                match = COMPACT_PATTERN.match(column)
                if match:
                    col_name = match.group(1)
                    op = match.group(2)

        # Use parsed operator if found
        if col_name and op:
            column = col_name
            operator = op

        # Handle IS NULL / IS NOT NULL
        if operator.upper() in ("IS NULL", "IS NOT NULL"):
            self.parts.append((f"`{column}` {operator.upper()}", []))
            return

        # Handle IS / IS NOT with None value
        if operator.upper() in ("IS", "IS NOT") and value is None:
            null_op = "IS NULL" if operator.upper() == "IS" else "IS NOT NULL"
            self.parts.append((f"`{column}` {null_op}", []))
            return

        # Handle IN / NOT IN operators
        if operator.upper() in ("IN", "NOT IN"):
            # Check if value is a subquery (has build method)
            if hasattr(value, "build"):
                sub_sql, sub_params = value.build()
                self.parts.append(
                    (f"`{column}` {operator.upper()} ({sub_sql})", list(sub_params))
                )
            elif isinstance(value, (list, tuple)):
                ph = self._dialect.parameter_placeholder()
                placeholders = ", ".join([ph] * len(value))
                self.parts.append(
                    (f"`{column}` {operator.upper()} ({placeholders})", list(value))
                )
            else:
                raise ValueError(
                    f"{operator} operator requires a list, tuple, or subquery"
                )
            return

        # Handle Raw values (e.g., Raw("users.id") for column references)
        if isinstance(value, Raw):
            # Use raw SQL directly without placeholder
            sql_fragment = f"`{column}` {operator} {value.sql}"
            # Include Raw's params if any
            self.parts.append((sql_fragment, list(value.params)))
            return

        # Handle standard operators with value
        if value is not None:
            self.parts.append(
                (
                    f"`{column}` {operator} {self._dialect.parameter_placeholder()}",
                    [value],
                )
            )

    def build(self, dialect=None) -> tuple[str, tuple[Any, ...]]:
        """
        Build the condition and return (sql, params) tuple.

        Args:
            dialect: Optional dialect to use for quoting. Defaults to MySQLDialect.

        Returns:
            Tuple of (sql_string, params_tuple)

        Example:
            >>> c = Condition("age>=", 18)
            >>> sql, params = c.build()
            >>> assert sql == "`age` >= ?"
            >>> assert params == (18,)
        """
        if not self.parts:
            return "", ()

        parts_sql = []
        params = []

        for sql, p in self.parts:
            if sql in ("AND", "OR"):
                parts_sql.append(sql)
            else:
                parts_sql.append(sql)
                if p:
                    params.extend(p)

        sql = " ".join(parts_sql)

        # Wrap in parentheses if multiple parts
        if len(self.parts) > 1:
            sql = f"({sql})"

        return sql, tuple(params)

    def __and__(self, other: "Condition") -> "Condition":
        new_cond = Condition()
        new_cond.parts = self.parts + [("AND", None)] + other.parts
        return new_cond

    def __or__(self, other: "Condition") -> "ComplexCondition":
        # Use ComplexCondition for OR to properly handle precedence
        return ComplexCondition("OR", self, other)

    # Static factory methods
    @staticmethod
    def null(column: str) -> "Condition":
        """
        Create an IS NULL condition.

        Args:
            column: Column name to check for NULL

        Returns:
            Condition object

        Example:
            >>> c = Condition.null("deleted_at")
            >>> sql, params = c.build()
            >>> # SQL: `deleted_at` IS NULL
        """
        return Condition(column, operator="IS NULL")

    @staticmethod
    def not_null(column: str) -> "Condition":
        """
        Create an IS NOT NULL condition.

        Args:
            column: Column name to check for NOT NULL

        Returns:
            Condition object

        Example:
            >>> c = Condition.not_null("email")
            >>> sql, params = c.build()
            >>> # SQL: `email` IS NOT NULL
        """
        return Condition(column, operator="IS NOT NULL")

    @staticmethod
    def in_(
        column: str, values: Union[list[Any], tuple[Any, ...], "SelectQuery"]
    ) -> "Condition":
        """
        Create an IN condition.

        Args:
            column: Column name
            values: List/tuple of values or a SelectQuery subquery

        Returns:
            Condition object

        Example:
            >>> c = Condition.in_("status", ["pending", "done"])
            >>> sql, params = c.build()
            >>> # SQL: `status` IN (?, ?)
        """
        return Condition(column, values, operator="IN")

    @staticmethod
    def not_in(
        column: str, values: Union[list[Any], tuple[Any, ...], "SelectQuery"]
    ) -> "Condition":
        """
        Create a NOT IN condition.

        Args:
            column: Column name
            values: List/tuple of values or a SelectQuery subquery

        Returns:
            Condition object

        Example:
            >>> c = Condition.not_in("status", ["canceled", "failed"])
            >>> sql, params = c.build()
            >>> # SQL: `status` NOT IN (?, ?)
        """
        return Condition(column, values, operator="NOT IN")

    @staticmethod
    def exists(subquery: "SelectQuery") -> "Condition":
        """
        Create an EXISTS condition with a subquery.

        Args:
            subquery: SelectQuery object

        Returns:
            Condition object

        Example:
            >>> subquery = Q.select("1").from_("orders").where(Condition("user_id", 123))
            >>> c = Condition.exists(subquery)
            >>> sql, params = c.build()
            >>> # SQL: EXISTS (SELECT 1 FROM `orders` WHERE `user_id` = ?)
        """
        cond = Condition()
        sub_sql, sub_params = subquery.build()
        cond.parts.append((f"EXISTS ({sub_sql})", list(sub_params)))
        return cond

    @staticmethod
    def not_exists(subquery: "SelectQuery") -> "Condition":
        """
        Create a NOT EXISTS condition with a subquery.

        Args:
            subquery: SelectQuery object

        Returns:
            Condition object

        Example:
            >>> subquery = Q.select("1").from_("orders").where(Condition("user_id", 123))
            >>> c = Condition.not_exists(subquery)
            >>> sql, params = c.build()
            >>> # SQL: NOT EXISTS (SELECT 1 FROM `orders` WHERE `user_id` = ?)
        """
        cond = Condition()
        sub_sql, sub_params = subquery.build()
        cond.parts.append((f"NOT EXISTS ({sub_sql})", list(sub_params)))
        return cond

    @staticmethod
    def and_(*conditions: "Condition") -> "Condition":
        """
        Combine multiple conditions with AND logic.

        Args:
            *conditions: Variable number of Condition objects

        Returns:
            Combined Condition object

        Example:
            >>> c1 = Condition("age>=", 18)
            >>> c2 = Condition("country", "US")
            >>> c3 = Condition("verified", True)
            >>> combined = Condition.and_(c1, c2, c3)
            >>> # SQL: (`age` >= ? AND `country` = ? AND `verified` = ?)
        """
        if not conditions:
            return Condition()

        result = conditions[0]
        for cond in conditions[1:]:
            result = result & cond
        return result

    @staticmethod
    def or_(*conditions: "Condition") -> Union["Condition", "ComplexCondition"]:
        """
        Combine multiple conditions with OR logic.

        Args:
            *conditions: Variable number of Condition objects

        Returns:
            ComplexCondition object

        Example:
            >>> c1 = Condition("status", "pending")
            >>> c2 = Condition("status", "processing")
            >>> combined = Condition.or_(c1, c2)
            >>> # SQL: (`status` = ? OR `status` = ?)
        """
        if not conditions:
            return ComplexCondition("OR", Condition(), Condition())

        result: Union[Condition, ComplexCondition] = conditions[0]
        for cond in conditions[1:]:
            result = result | cond
        return result


class ComplexCondition(Expression):
    r"""
    Represents a complex SQL condition combining multiple conditions with AND/OR logic.

    This class is typically created automatically when using bitwise operators (& or \|)
    on Condition objects, or when using Condition.and_() / Condition.or_() static methods.
    It properly handles operator precedence and nested conditions.

    Args:
        operator (str): The logical operator ("AND" or "OR").
        left (Union[Condition, ComplexCondition]): The left-hand condition.
        right (Union[Condition, ComplexCondition]): The right-hand condition.

    Examples:
        >>> c1 = Condition("age>=", 18)
        >>> c2 = Condition("country", "US")
        >>> c3 = Condition("verified", True)
        >>>
        >>> # Creates ComplexCondition automatically
        >>> complex = (c1 & c2) \| c3
        >>> # Represents: (age >= 18 AND country = 'US') OR verified = True
    """

    def __init__(
        self,
        operator: str,
        left: Union[Condition, "ComplexCondition"],
        right: Union[Condition, "ComplexCondition"],
    ):
        self.operator = operator
        self.left = left
        self.right = right

    def build(self, dialect=None) -> tuple[str, tuple[Any, ...]]:
        r"""
        Build the complex condition and return (sql, params) tuple.

        Args:
            dialect: Optional dialect to use for quoting. Defaults to MySQLDialect.

        Returns:
            Tuple of (sql_string, params_tuple)

        Example:
            >>> c1 = Condition("age>=", 18)
            >>> c2 = Condition("country", "US")
            >>> complex = c1 \| c2
            >>> sql, params = complex.build()
            >>> # SQL: (`age` >= ? OR `country` = ?)
        """
        # Build left and right conditions
        left_sql, left_params = (
            self.left.build(dialect) if hasattr(self.left, "build") else ("", ())
        )
        right_sql, right_params = (
            self.right.build(dialect) if hasattr(self.right, "build") else ("", ())
        )

        # Combine with operator
        sql = f"({left_sql} {self.operator} {right_sql})"
        params = left_params + right_params

        return sql, params

    def __and__(self, other):
        return ComplexCondition("AND", self, other)

    def __or__(self, other):
        return ComplexCondition("OR", self, other)


func = FunctionFactory()


class JSONPath(Expression):
    """Represents a JSON path extraction."""

    def __init__(self, column: str, path: str):
        self.column = column
        self.path = path


class JSON(Expression):
    """
    Represents a JSON column.

    Example:
        >>> JSON("data").extract("name")
    """

    def __init__(self, column: str):
        self.column = column

    def extract(self, path: str) -> JSONPath:
        """Extract a value from the JSON column."""
        return JSONPath(self.column, path)
