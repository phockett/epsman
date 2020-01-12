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
    dirList = [Path(f.path).relative_to(sourceDir) for f in os.scandir(sourceDir) if f.is_dir()]

    # Set main index string.
    indexSting = f"""
ePS data
==========================================

.. toctree::
 :maxdepth: 2
 :caption: Contents:

 about
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
