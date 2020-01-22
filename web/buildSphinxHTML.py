"""
epsman

Local python script for HTML generation with Sphinx.

Can be called from Fabric for remote run case, only requires standard libs.

12/01/20    v1

"""
import os

def genSphinxIndex(sourceDir):
    """
    Generate index.rst for Sphinx based on dir structure.

    Some redundency here, but more control (maybe).
    May be other/better ways to do this directly with globbing in index.rst, but didn't find one yet.

    Use \""" strings for basic templating engine.

    """

    # Generate dir list using os.scandir
    # See https://stackoverflow.com/questions/973473/getting-a-list-of-all-subdirectories-in-the-current-directory
    # Additionally set here for relative paths.
    # dirList = [Path(f.path).relative_to(sourceDir) for f in os.scandir(sourceDir) if f.is_dir()]
    # Skip _ dits - bit of an ugly one-liner but works... probably a neater way to do this.
    dirList = [Path(f.path).relative_to(sourceDir) for f in os.scandir(sourceDir) if f.is_dir() and not Path(f.path).relative_to(sourceDir).as_posix().startswith('_')]

    # Set main index string.
    indexSting = f"""
ePS data: Photoionization calculations archive
===============================================

Photoionization calculation results with `ePolyScat <http://www.chem.tamu.edu/rgroup/lucchese/>`_ and `ePSproc <https://epsproc.readthedocs.io>`_ - data and processed results, Jupyter notebooks and HTML.

.. toctree::
 :maxdepth: 2
 :caption: Intro:

 about
 methods
 cite

 .. image:: http://femtolab.ca/wordpress/wp-content/uploads/2017/03/grav_box_img23164957.jpg 
                """

    # Set toc per dir
    dirString = ''
    for item in dirList:
        dirName = Path(item).name
        dirString += f"""
.. toctree::
   :maxdepth: 2
   :caption: {dirName}
   :glob:

   {dirName}/*

                       """

    footerString = """
Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
                    """

    return (indexSting + dirString + footerString)
