import datetime
import pathlib
import sys

import sphinx.ext.apidoc as apidoc
from sphinx.highlighting import lexers

sphinx_root_dir = pathlib.Path(__file__).parent.resolve()
caldera_root_dir = pathlib.Path(__file__).absolute().parent.parent.parent.parent

sys.path.insert(0, str(caldera_root_dir))

from plugins.fieldmanual.utils.ability_csv import generate_ability_csv
from plugins.fieldmanual.utils.command_lexer import CalderaCommandLexer
from plugins.fieldmanual.utils.plugin_docs import import_plugin_docs


def visit_document(*_):
    pass


# Call sphinx-apidoc to generate stub files from our source code.
# -o generated: output rst stubs to this directory
# --implicit-namespaces: will find modules in packages without explicit __init__.py
# --force: overwrite existing generated stubs
# ../app/: this is the directory where caldera lives
apidocs_argv = [
    '-o',
    '_generated',
    '--implicit-namespaces',
    '--force',
    str(caldera_root_dir / 'app'),
]
apidoc.main(apidocs_argv)

# Import documentation from plugins
import_plugin_docs(caldera_root_dir, sphinx_root_dir)

# Export csv info to csv:
generate_ability_csv(caldera_root_dir, sphinx_root_dir / '_generated' / 'abilities.csv')

# -- Project information -----------------------------------------------------

project = 'caldera'
copyright = f'{datetime.date.today().year}, The MITRE Corporation'
author = 'The MITRE Corporation'
master_doc = 'index'


# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'myst_parser',
]

exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_static_path = ['_static']

lexers['caldera'] = CalderaCommandLexer()

# -- Options for HTML output -------------------------------------------------

html_theme = 'sphinx_rtd_theme'
html_logo = 'img/caldera-logo.png'
html_theme_options = {
    'logo_only': True,
}

# -- MyST Parser configuration -----------------------------------------------

suppress_warnings = ['myst.header']
myst_heading_anchors = 4
