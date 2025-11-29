sqlo - Lightweight SQL Query Builder
====================================

A **lightweight** and **simple** SQL query builder for Python. Build SQL queries 
with a clean, intuitive API while staying safe from SQL injection.

Features
--------

* 🪶 **Lightweight**: Zero dependencies, minimal footprint
* ✨ **Simple**: Intuitive fluent API, easy to learn
* 🛡️ **Secure by Default**: Built-in SQL injection protection
* 🐍 **Pythonic**: Fluent API design that feels natural to Python developers
* 🧩 **Composable**: Build complex queries from reusable parts

Quick Example
-------------

.. code-block:: python

   from sqlo import Q

   # SELECT query
   query = Q.select("id", "name").from_("users").where("active", True)
   sql, params = query.build()
   # SQL: SELECT `id`, `name` FROM `users` WHERE `active` = %s
   # Params: (True,)

Documentation
-------------

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   getting-started
   security
   
.. toctree::
   :maxdepth: 2
   :caption: Query Types

   select
   insert
   update
   delete
   
.. toctree::
   :maxdepth: 2
   :caption: Advanced Topics

   conditions
   expressions
   joins
   
.. toctree::
   :maxdepth: 2
   :caption: Reference

   reference


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
