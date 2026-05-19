"""Sphinx configuration for the qkdsec documentation."""

from __future__ import annotations

import sys
from pathlib import Path

# Make the package importable when building outside an editable install
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# ── Project information ───────────────────────────────────────────────────

project = "qkdsec"
author = "John Jepsen"
copyright = f"2026, {author}"

try:
    from qkdsec import __version__ as release  # type: ignore
except Exception:
    release = "0.2.0"
version = ".".join(release.split(".")[:2])

# ── General configuration ─────────────────────────────────────────────────

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
    "sphinx_copybutton",
    "myst_parser",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "fieldlist",
]

autosummary_generate = True
autodoc_typehints = "description"
autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
}

napoleon_google_docstring = True
napoleon_numpy_docstring = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "requests": ("https://requests.readthedocs.io/en/latest", None),
}

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# ── HTML output ───────────────────────────────────────────────────────────

html_theme = "furo"
html_title = f"qkdsec {release}"
html_static_path = ["_static"]
html_theme_options = {
    "sidebar_hide_name": False,
    "navigation_with_keys": True,
    "source_repository": "https://github.com/John-Jepsen/qkdsec/",
    "source_branch": "main",
    "source_directory": "docs/",
    "footer_icons": [
        {
            "name": "GitHub",
            "url": "https://github.com/John-Jepsen/qkdsec",
            "html": (
                '<svg stroke="currentColor" fill="currentColor" '
                'stroke-width="0" viewBox="0 0 16 16" height="1em" '
                'width="1em" xmlns="http://www.w3.org/2000/svg">'
                '<path fill-rule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 '
                "2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 "
                "0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-"
                ".94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 "
                "1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-"
                ".2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02."
                "08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36."
                "09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51."
                "56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 "
                "1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 "
                '0 0 16 8c0-4.42-3.58-8-8-8z"></path></svg>'
            ),
            "class": "",
        },
    ],
}

# Create _static directory at build time if it does not exist
_static_dir = Path(__file__).resolve().parent / "_static"
_static_dir.mkdir(exist_ok=True)
