from typing import TYPE_CHECKING, Any, Optional, Union

import math

from .constants import COMPACT_PATTERN, JSON_PATH_PATTERN
from .context import CompileContext
from .security import require_identifier, validate_identifier, validate_operator

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
        render_func(name, args)  # Fail early on an invalid name or argument
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


def _render_func_arg(arg: Any) -> str:
    """Render one function argument as SQL, rejecting anything unsafe."""
    if isinstance(arg, Func):
        return render_func(arg.name, arg.args)
    if isinstance(arg, Raw):
        if arg.params:
            raise ValueError(
                "Raw() with params is not supported as a function argument"
            )
        return arg.sql
    if arg is None:
        return "NULL"
    if isinstance(arg, bool):
        return "TRUE" if arg else "FALSE"
    if isinstance(arg, (int, float)):
        if isinstance(arg, float) and not math.isfinite(arg):
            raise ValueError(f"Invalid function argument {arg!r}")
        return repr(arg)
    if isinstance(arg, str):
        if arg == "*" or validate_identifier(arg):
            return arg
        raise ValueError(
            f"Invalid function argument {arg!r}. String arguments must be a column "
            "name or '*'. Use Raw() for SQL expressions."
        )
    raise TypeError(f"Unsupported function argument type: {type(arg).__name__}")


def render_func(name: str, args: tuple) -> str:
    """Render ``NAME(arg, ...)``.

    The name must be an identifier. String arguments must be column names
    (optionally dotted) or ``*``; numbers, booleans and ``None`` are inlined;
    nested ``Func`` are rendered recursively; ``Raw`` is emitted as-is.

    :raises ValueError: for an invalid name or an unsafe string argument
    :raises TypeError: for an unsupported argument type
    """
    if not validate_identifier(name, allow_dot=False):
        raise ValueError(f"Invalid function name {name!r}")
    return f"{name}({', '.join(_render_func_arg(a) for a in args)})"


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


def _column_sql(ctx: CompileContext, column: Union[str, Raw]) -> str:
    """Render the left-hand side: a quoted identifier or a Raw expression."""
    if isinstance(column, Raw):
        ctx.params.extend(column.params)
        return column.sql
    return ctx.quote(column)


class _RawPredicate:
    """A complete predicate given as ``Raw`` SQL, e.g. ``MATCH(...) AGAINST(%s)``."""

    __slots__ = ("raw",)

    def __init__(self, raw: Raw):
        self.raw = raw

    def render(self, ctx: CompileContext) -> str:
        ctx.params.extend(self.raw.params)
        return self.raw.sql


class _Compare:
    """``column <operator> value`` where value is a parameter or a Raw fragment."""

    __slots__ = ("column", "operator", "value")

    def __init__(self, column: str, operator: str, value: Any):
        self.column = column
        self.operator = operator
        self.value = value

    def render(self, ctx: CompileContext) -> str:
        column = _column_sql(ctx, self.column)
        if isinstance(self.value, Raw):
            ctx.params.extend(self.value.params)
            return f"{column} {self.operator} {self.value.sql}"
        return f"{column} {self.operator} {ctx.param(self.value)}"


class _NullCheck:
    """``column IS NULL`` / ``column IS NOT NULL``."""

    __slots__ = ("column", "operator")

    def __init__(self, column: str, operator: str):
        self.column = column
        self.operator = operator

    def render(self, ctx: CompileContext) -> str:
        return f"{_column_sql(ctx, self.column)} {self.operator}"


class _In:
    """``column [NOT] IN (values)`` where values is a tuple or a subquery."""

    __slots__ = ("column", "operator", "values")

    def __init__(self, column: str, operator: str, values: Any):
        self.column = column
        self.operator = operator
        self.values = values

    def render(self, ctx: CompileContext) -> str:
        column = _column_sql(ctx, self.column)
        if isinstance(self.values, tuple):
            if not self.values:
                # IN () is invalid SQL: it is always false, NOT IN () always true
                return "TRUE" if self.operator == "NOT IN" else "FALSE"
            inner = ", ".join([ctx.param(v) for v in self.values])
        else:
            inner = ctx.subquery(self.values)
        return f"{column} {self.operator} ({inner})"


class _Exists:
    """``[NOT] EXISTS (subquery)``."""

    __slots__ = ("subquery", "negate")

    def __init__(self, subquery: Any, negate: bool):
        self.subquery = subquery
        self.negate = negate

    def render(self, ctx: CompileContext) -> str:
        keyword = "NOT EXISTS" if self.negate else "EXISTS"
        return f"{keyword} ({ctx.subquery(self.subquery)})"


class _ConditionNode(Expression):
    """Base class of condition nodes: dialect-independent data that renders SQL."""

    def render(self, ctx: CompileContext) -> str:
        """Render the node, recording its parameters in ``ctx``."""
        raise NotImplementedError

    def build(self, dialect=None) -> tuple[str, tuple[Any, ...]]:
        """
        Build the condition and return (sql, params) tuple.

        Args:
            dialect: Optional dialect to render with. Defaults to ``Q.get_dialect()``.

        Returns:
            Tuple of (sql_string, params_tuple)

        Example:
            >>> c = Condition("age>=", 18)
            >>> sql, params = c.build()
            >>> assert sql == "`age` >= %s"
            >>> assert params == (18,)
        """
        ctx = CompileContext(dialect)
        sql = self.render(ctx)
        return sql, tuple(ctx.params)


class Condition(_ConditionNode):
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
        column: Optional[Union[str, Raw]] = None,
        value: Any = None,
        operator: str = "=",
    ):
        self._terms: list[Any] = []  # ANDed terms, rendered with a CompileContext
        self.connector = "AND"

        if column is not None:
            self._add_condition(column, value, operator)

    def _add_condition(
        self, column: Union[str, Raw], value: Any, operator: str
    ) -> None:
        """Add a condition to this Condition object.

        The column and operator are validated here; quoting and placeholders
        are decided later, when the condition is rendered for a dialect.
        """
        col_name = None
        op = None

        # A Raw column with no value and the default operator is a complete
        # predicate: Condition(Raw("MATCH(t) AGAINST(%s)", ["x"]))
        if isinstance(column, Raw) and value is None and operator == "=":
            self._terms.append(_RawPredicate(column))
            return

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

        operator = validate_operator(operator)
        if not isinstance(column, Raw):
            require_identifier(column)

        # Handle IS NULL / IS NOT NULL
        if operator in ("IS NULL", "IS NOT NULL"):
            self._terms.append(_NullCheck(column, operator))
            return

        # Handle IS / IS NOT with None value
        if operator in ("IS", "IS NOT") and value is None:
            null_op = "IS NULL" if operator == "IS" else "IS NOT NULL"
            self._terms.append(_NullCheck(column, null_op))
            return

        # Handle IN / NOT IN operators
        if operator in ("IN", "NOT IN"):
            # Check if value is a subquery (has build method)
            if hasattr(value, "build"):
                self._terms.append(_In(column, operator, value))
            elif isinstance(value, (list, tuple)):
                self._terms.append(_In(column, operator, tuple(value)))
            else:
                raise ValueError(
                    f"{operator} operator requires a list, tuple, or subquery"
                )
            return

        # A missing value must not silently drop the condition
        if value is None:
            raise ValueError(
                f"Condition({column!r}) has no value to compare with. To test for "
                "NULL use Condition.null(...), Condition.not_null(...) or "
                "operator='IS NULL' / 'IS NOT NULL'."
            )

        # Handle Raw values (e.g., Raw("users.id") for column references)
        # and standard operators with a value
        self._terms.append(_Compare(column, operator, value))

    def render(self, ctx: CompileContext) -> str:
        if not self._terms:
            return ""
        sql = " AND ".join([term.render(ctx) for term in self._terms])
        # Wrap in parentheses if multiple terms
        return f"({sql})" if len(self._terms) > 1 else sql

    def __and__(self, other: "_ConditionNode") -> "_ConditionNode":
        if isinstance(other, Condition):
            new_cond = Condition()
            new_cond._terms = self._terms + other._terms
            return new_cond
        if isinstance(other, ComplexCondition):
            return ComplexCondition("AND", self, other)
        return NotImplemented

    def __or__(self, other: "_ConditionNode") -> "ComplexCondition":
        # Use ComplexCondition for OR to properly handle precedence
        if not isinstance(other, _ConditionNode):
            return NotImplemented
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
        cond._terms.append(_Exists(subquery, negate=False))
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
        cond._terms.append(_Exists(subquery, negate=True))
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


class ComplexCondition(_ConditionNode):
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

    def render(self, ctx: CompileContext) -> str:
        left_sql = self.left.render(ctx)
        right_sql = self.right.render(ctx)
        # An empty side is the identity of both AND and OR: it is left out
        if not left_sql:
            return right_sql
        if not right_sql:
            return left_sql
        return f"({left_sql} {self.operator} {right_sql})"

    def __and__(self, other):
        if not isinstance(other, _ConditionNode):
            return NotImplemented
        return ComplexCondition("AND", self, other)

    def __or__(self, other):
        if not isinstance(other, _ConditionNode):
            return NotImplemented
        return ComplexCondition("OR", self, other)


func = FunctionFactory()


def values_of(column: str) -> Raw:
    """Reference the value that INSERT would have written to ``column``.

    Use it in ``on_duplicate_key_update`` to get ``VALUES(`column`)`` with the
    column name validated and quoted.

    Example:
        >>> q = Q.insert_into("users").values({"id": 1, "name": "a"})
        >>> q = q.on_duplicate_key_update({"name": values_of("name")})
    """
    from .dialects.mysql import MySQLDialect

    return Raw(f"VALUES({MySQLDialect().quote(column)})")


class JSONPath(Expression):
    """Represents a JSON path extraction."""

    def __init__(self, column: str, path: str):
        if not isinstance(path, str) or not JSON_PATH_PATTERN.match(path):
            raise ValueError(
                f"Invalid JSON path {path!r}. Use keys, indexes and wildcards "
                "such as 'a.b[0].c' or 'tags[*]'."
            )
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
