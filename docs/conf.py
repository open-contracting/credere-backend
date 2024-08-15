# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

sys.path.insert(0, os.path.abspath(".."))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Credere"
copyright = "2023, Open Contracting Partnership"
author = "Open Contracting Partnership"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.extlinks",
    "sphinx.ext.viewcode",
    "sphinx_design",
    "sphinxcontrib.typer",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_static_path = ["_static"]
html_additional_pages = {
    "api/redoc": "redoc.html",
    "api/swagger-ui": "swagger-ui.html",
}

# -- Extension configuration -------------------------------------------------

autodoc_default_options = {
    "members": None,
    "member-order": "bysource",
}
# autodoc_typehints = "description"

extlinks = {
    "issue": ("https://github.com/open-contracting/credere-backend/issues/%s", "#%s"),
}
