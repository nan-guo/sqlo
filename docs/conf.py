# Configuration file for the Sphinx documentation builder.

import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.abspath("../src"))

# -- Project information -----------------------------------------------------
project = "sqlo"
copyright = "2025, Nan Guo"
author = "Nan Guo"
version = "0.1.1"
release = "0.1.1"

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "myst_parser",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# The suffix of source filenames
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# -- Options for HTML output -------------------------------------------------
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_title = "sqlo Documentation"
html_short_title = "sqlo"

# -- MyST-Parser configuration -----------------------------------------------
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "substitution",
    "tasklist",
]

# Enable parsing of admonitions (WARNING, NOTE, etc.)
myst_admonition_enable = True

# -- Autodoc settings --------------------------------------------------------
autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
}

# Resolve ambiguous references by preferring the main package exports
autodoc_typehints = "description"
autodoc_member_order = "bysource"

# -- Napoleon settings -------------------------------------------------------
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True

# -- Intersphinx configuration -----------------------------------------------
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

# -- Suppress warnings -------------------------------------------------------
suppress_warnings = [
    "myst.xref_missing",  # Missing cross-references in markdown
    "toc.not_included",  # Documents not in toctree
    "ref.python",  # Ambiguous Python cross-references
]
