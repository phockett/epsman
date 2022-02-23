# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
sys.path.insert(0, os.path.abspath('.'))
#sys.path.insert(0, os.path.abspath('..\\'))    # Add module path (relative to docs path)
#sys.path.insert(0, os.path.abspath('..\\..\\'))    # Add module path (relative to docs path)
sys.path.insert(0, os.path.abspath('../../'))       # Add module path (relative to docs path) FOR READTHEDOCs (above originally worked, but then broke!)
#sys.path.insert(0, os.path.abspath('..\\..\\..\\'))    # Add module path (relative to docs path)
# print(sys.path)

# Set RTD flag, use this to skip imports for RTD build.
# See https://docs.readthedocs.io/en/stable/faq.html#how-do-i-change-behavior-when-building-with-read-the-docs
on_rtd = os.environ.get('READTHEDOCS') == 'True'
# if on_rtd:
#     html_theme = 'default'
# else:
#     html_theme = 'nature'


# -- Project information -----------------------------------------------------

project = 'ePSman'
copyright = '2018, Paul Hockett'
author = 'Paul Hockett'

# Version from package https://stackoverflow.com/questions/26141851/let-sphinx-use-version-from-setup-py
if on_rtd:
    version = "RTD"  # Dummy variable, RTD will use version from Github branch/tag.
                    # See https://readthedocs.org/projects/epsproc/versions/
else:
    from pemtk import __version__
    version = __version__

# The full version, including alpha/beta/rc tags
release = version


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
# NOTE 'IPython.sphinxext.ipython_console_highlighting' for RTD ipython highlighting.
# See https://github.com/spatialaudio/nbsphinx/issues/24
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.napoleon',
                'sphinxcontrib.apidoc', 'recommonmark',
                'sphinx.ext.viewcode', 'nbsphinx']
                # 'IPython.sphinxext.ipython_console_highlighting']  # Actually this throws an error on RTD - try adding ipyhton to requirements.txt instead...

# api doc settings
apidoc_module_dir = '../../epsman'
apidoc_output_dir = 'modules'
apidoc_excluded_paths = ['tests']
apidoc_separate_modules = True

# Sphinx-autodoc mock imports for minimal build-chain.
# https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#confval-autodoc_mock_imports
if on_rtd:
    autodoc_mock_imports = ["numpy_quaternion", "quaternion", "spherical_functions","cclib",
                            "numpy","scipy","xarray","pandas","numba",
                            "matplotlib","mpl_toolkits","seaborn","plotly",
                            "pyvista","holoviews",
                            "fabric"]  #, "epsman"]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['**.ipynb_checkpoints','**-verified*','**Dev*']

# For Read the Docs, see https://stackoverflow.com/questions/56336234/build-fail-sphinx-error-contents-rst-not-found
master_doc = 'index'

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
# html_theme = 'alabaster'
html_theme = 'sphinx_rtd_theme'
# html_theme = "sphinx_book_theme"  # Builds OK, but lacking heading formatting? Need to set options or add CSS?
                                    # E.g. https://github.com/jcmgray/xyzpy/blob/develop/docs/_static/my-styles.css
                                    # TODO: check theme docs, https://sphinx-book-theme.readthedocs.io/en/latest/

html_logo = 'figs/ePSproc_logo.png'

# RTD theme options, see https://sphinx-rtd-theme.readthedocs.io/en/stable/configuring.html
html_theme_options = {
    "github_url": "https://github.com/phockett/epsman",
    'body_max_width': '70%'
    }


# Sphinx book theme options, cribbed from XYZPY docs, https://github.com/jcmgray/xyzpy/blob/develop/docs/conf.py
# html_theme_options = {
#     "github_url": "https://github.com/phockett/PEMtk",
#     "repository_url": "https://github.com/phockett/PEMtk",
#     "use_repository_button": True,
#     "use_issues_button": True,
#     "use_edit_page_button": True,
#     "path_to_docs": "docs",
#     "use_fullscreen_button": False,
#     "use_download_button": False,
# }

# For Alabaster theme, see https://alabaster.readthedocs.io/en/latest/customization.html
# html_theme_options = {
#     "page_width": "80%",
#     "github_button": True,
#     "github_user": "phockett",
#     "github_repo": "PEMtk",
#     "github_url": "https://github.com/phockett/PEMtk",
#     "repository_url": "https://github.com/phockett/PEMtk",
# }


# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Add custom CSS to fix max width issue
# Fix RTD standard template (sphinx_rtd_theme) max width.
# See
# https://github.com/readthedocs/sphinx_rtd_theme/issues/295
# https://stackoverflow.com/questions/23211695/modifying-content-width-of-the-sphinx-theme-read-the-docs

# Option (1): include .css file with fix.
# Applied & tested on RTD (RTD theme) OK, 01/09/21
# NOT working for Alabaster theme.
html_css_files = [
    'max_width_fix.css',
]

# Option (2): set theme option
# This might also work (no additional CSS required):
# DOESN'T WORK ON RTD with sphinx_rtd_theme
# html_theme_options = {'body_max_width': '70%'}
# html_theme_options['body_max_width'] = '80%'
# html_theme_options['page_width'] = '80%'  # For Alabaster theme, see https://alabaster.readthedocs.io/en/latest/customization.html
                                            # NOT working!

# Option (3): include .css file with patch (similar to (1), but imports theme into the patch CSS file)
# This might work too - patches existing theme:
# html_style = 'max_width_patch.css'
