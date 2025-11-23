from typing import Any, List, Tuple, Union


class Expression:
    """Base class for SQL expressions."""


class Raw(Expression):
    """Raw SQL fragment."""

    def __init__(
        self, sql: str, params: Union[List[Any], Tuple[Any, ...]] = None
    ):
        self.sql = sql
        self.params = params or []


class Func(Expression):
    """SQL Function wrapper."""

    def __init__(self, name: str, *args: Any):
        self.name = name
        self.args = args
        self.alias = None  # Initialize alias in __init__

    def as_(self, alias: str) -> "Func":
        self.alias = alias
        return self


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

    def count(self, expression: str = "*") -> Func:
        return Func("COUNT", expression)

    def sum(self, expression: str) -> Func:
        return Func("SUM", expression)

    def avg(self, expression: str) -> Func:
        return Func("AVG", expression)

    def min(self, expression: str) -> Func:
        return Func("MIN", expression)

    def max(self, expression: str) -> Func:
        return Func("MAX", expression)


class Condition(Expression):
    """Condition object for complex WHERE clauses (AND/OR)."""

    def __init__(
        self, column: str = None, value: Any = None, operator: str = "="
    ):
        self.parts: List[Tuple[str, Any]] = []  # (sql, params)
        self.connector = "AND"

        if column:
            # Simple condition initialization
            if " " in column and value is not None:
                parts = column.split(" ", 1)
                col_name = parts[0]
                op = parts[1]
                self.parts.append((f"`{col_name}` {op} ?", [value]))
            elif value is not None:
                self.parts.append((f"`{column}` {operator} ?", [value]))

    def __and__(self, other: "Condition") -> "Condition":
        new_cond = Condition()
        new_cond.parts = self.parts + [("AND", None)] + other.parts
        return new_cond

    def __or__(self, other: "Condition") -> "ComplexCondition":
        # Use ComplexCondition for OR to properly handle precedence
        return ComplexCondition("OR", self, other)


class ComplexCondition(Expression):
    def __init__(
        self,
        operator: str,
        left: Union[Condition, "ComplexCondition"],
        right: Union[Condition, "ComplexCondition"],
    ):
        self.operator = operator
        self.left = left
        self.right = right

    def __and__(self, other):
        return ComplexCondition("AND", self, other)

    def __or__(self, other):
        return ComplexCondition("OR", self, other)


func = FunctionFactory()
