from typing import Any, Union

from .expressions import Func, Raw
from .query.delete import DeleteQuery
from .query.insert import InsertQuery
from .query.select import SelectQuery
from .query.update import UpdateQuery


class Q:
    """Query Builder Factory."""

    @staticmethod
    def select(*columns: Union[str, Raw, Func]) -> SelectQuery:
        return SelectQuery(*columns)

    @staticmethod
    def insert_into(table: str) -> InsertQuery:
        return InsertQuery(table)

    @staticmethod
    def update(table: str) -> UpdateQuery:
        return UpdateQuery(table)

    @staticmethod
    def delete_from(table: str) -> DeleteQuery:
        return DeleteQuery(table)

    @staticmethod
    def raw(sql: str, params: Any = None) -> Raw:
        return Raw(sql, params)
