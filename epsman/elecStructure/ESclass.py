"""
Basic methods for dealing with Gamess & Molden file IO for ePolyScat.

10/06/21  Added some basic error checks during testing. SHOULD SET AS A DECORATOR.

03/02/21 v2 Revisiting and finishing off...
            - Fixed formatting options.
            - Added wrappers for cclib moldenwriter.MOLDEN as new class.
            - Use EShandler class for general IO.
            - Tested with N2O demo file + ePS test job OK for Molden2006 format.

            Files from writeMoldenFile2006() are working with ePS (tested for N2O test file).
            Files from reformatMoldenFile() are NOT working due to line-endings issues.
            See `notes/epsman_EShandler_class_demo_050221.ipynb` for demo & testing.


26/08/20 v1 Quick hack from existing functions - needs some more sophistication for file handling. Should have utils for this...

Dev work currently in [Bemo] http://localhost:8888/notebooks/ePS/N2O/N2O_electronic_structure_proc_tests_250820.ipynb

"""

import fileinput
import sys
from pathlib import Path

import cclib
from cclib.io import moldenwriter  # Molden class + functions

# import epsman as em  # For base class
from epsman._util import fileParse

class EShandler():
    """
    Basic class for handling Gamess & Molden file IO.

    Uses `CCLIB <https://cclib.github.io/>`_ to read Gamess log files & convert to Molden format.

    For ePS compatibilty, this is slightly modified to match the "Molden2006" specifications defined therein (see source in `MoldenCnv2006.f90`).


    Parameters
    ----------

    fileName : str or Path obj, optional, default = None
        Gamess or Molden file.

    fileBase : str or Path obj, optional, default = None
        Path to file location, defaults to current working dir.

    outFile : str or Path obj, optional, default = None
        Name for output Molden file, defaults to fileName.molden if not set.

    If no args are passed, fileName = None will be set, and filePath = working dir.


    Examples
    --------
    >>> fileBase = Path(modPath, 'epsman', 'elecStructure','fileTest')  # Set for test file, where modPath = path to epsman root
    >>> fileName = r'N2O_aug-cc-pVDZ_geomOpt.log'
    >>> esData = EShandler(fileName, fileBase)  # Create class instance
    >>> esData.readGamessLog()  # Read Gamess file
    >>> esData.writeMoldenFile2006()  # Write Molden2006 file
    >>> esData.writeMoldenFile()  # Write Molden file as per CCLIB defaults.

    >>> esData = EShandler(fileName = 'test.molden') # Pass a Molden file to set & use the reformatter
    >>> esData.reformatMoldenFile()


    Notes
    -----

    Thanks to `the CCLIB authors <https://cclib.github.io/>`_ for making this possible!

    To do
    -----
    - Implement directory scan (or wrapper class/decorator for this).
    - Better file handling, should implement Pathlib tests for file(s).
    - Fix reformatMoldenFile() method, this currently outputs OS specific line endings.


    10/06/21: adding ES file handling & info functions following recent OCS run testing, first version of:

        - setOrbInfoPD, orbInfoSummary (source _orbInfo.py) to pull orbital/molecule info from ES file.
        - setChannel, setePSinputs, genSymList, convertSymList, writeInputConf (source _ePSsetup.py) for setting up ePS parameters based on ES file + additional inputs. Needs further work, may also move to ESjob class in future...?
        - wrapped into ESjob class for main ePS job creation routines.


    19/02/21: For full eps job class inheritance, use ESjob class instead.

    """

    # Orbital info methods.
    from ._orbInfo import setOrbInfoPD, orbInfoSummary
    from ._ePSsetup import setChannel, setePSinputs, genSymList, convertSymList, writeInputConf

    def __init__(self, fileName = None, fileBase = None, outFile = None, verbose = 1):

        self.setFiles(fileName=fileName, fileBase=fileBase, outFile=outFile)
        self.verbose = verbose

        # If a Gamess file is passed, read it.
        if (self.fileName is not None) and (self.fileName.suffix != '.molden'):
            self.readGamessLog()
        else:
            # Currently not reading data for Molden case, just set to None
            self.data = None



    def setFiles(self, fileName = None, fileBase = None, outFile = None):
        """
        Set fileName, fileBase and outFile

        Parameters
        ----------
        fileName : str or Path obj, optional, default = None
            Gamess or Molden file.

        fileBase : str or Path obj, optional, default = None
            Path to file location, defaults to current working dir.

        outFile : str or Path obj, optional, default = None
            Name for output Molden file, defaults to fileName.molden if not set.

        If no args are passed, fileName = None will be set, and filePath = working dir.

        """

        # Set fileBase and fileName - for now no error checking here
        if fileBase is None:
            self.fileBase = Path.cwd()
        else:
            self.fileBase = Path(fileBase)

        if fileName is None:
            if fileBase is None:
                # Case for empty class
                self.fileName = None
            else:
                print('*** No electronic structure file set. TODO - implement dir scan here, see em._util.getFileList')
                self.fileName = None

        else:
            self.fileName = Path(fileName)

        if self.fileName is not None:
            self.fullPath = (self.fileBase/self.fileName)
        else:
            self.fullPath = self.fileBase  # Just propagate fileBase in this case.


        # If a Molden file is passed, just set moldenFile for use later.
        # TODO: integrate this with setMoldenFile() below.
        if self.fileName is not None:
            # if self.fileName.suffix != '.molden':
                # self.readGamessLog()

            if outFile is None:
                self.moldenFile = self.fullPath.with_suffix('.' + 'molden')
            else:
                self.moldenFile = self.fullPath.with_name(outFile)

        else:
            self.moldenFile = self.fullPath

        print(f'\nSet input file as {self.fullPath}, use self.setFiles to change.')
        print(f'Set output file as {self.moldenFile}, use self.setMoldenFile to override.')


    def setMoldenFile(self, fileName, fileBase = None):
        """
        Set self.moldenFile with new fileName and existing path, or new path.

        Parameters
        ----------
        fileName : str or Path obj, optional, default = None
            Molden filename.

        fileBase : str or Path obj, optional, default = None
            Path to file location, defaults to currently set path.

        """

        # Assume current path is correct, and set fileName
        if fileBase is None:
            if self.fullPath.is_dir():
                self.moldenFile = self.fullPath/Path(fileName)
            else:
                self.moldenFile = self.fullPath.with_name(fileName)
        else:
            self.moldenFile = Path(fileBase, fileName)

        # self.fileName = fileName

        print(f'Set output file as {self.moldenFile}, run self.setMoldenFile to override.')


    def readGamessLog(self):
        """
        Read Gamess log file using CCLIB.io.ccread(self.fullPath).

        File parser details:

        - https://cclib.github.io/data.html
        - https://cclib.github.io/data_notes.html

        self.setOrbInfoPD() is used to reformat the CCLIB data to Pandas.

        For point-group, CCLIB metadata[symmetry_detected] and metadata[symmetry_used], see https://cclib.github.io/data_notes.html#metadata
        Not set for Gamess file import?

        """

        self.data = cclib.io.ccread(self.fullPath.as_posix())
        print(f"\n*** Read file {self.fullPath} with CCLIB, data set to self.data.")

        try:
            print("Read %i atoms and %i MOs" % (self.data.natom, self.data.nmo))

            # Set orb info
            self.setOrbInfoPD()

        # Generic error case, usually due to None returned from cclib.
        except AttributeError:
            print(f"*** Error: File {self.fullPath} not found or empty.")



    def writeMoldenFile(self):
        """
        Write data to Molden format file using CCLIB.io.ccwrite(self.data)

        """
        try:
            # Convert to Molden format
            cclib.io.ccwrite(self.data, terse=True, outputtype='molden', outputdest=self.moldenFile.as_posix())  # From data

            print(f"Written Molden format file {self.moldenFile}")
            # self.reformatMoldenFile()

        # Generic error case, usually due to None returned from cclib.
        except AttributeError:
            print(f"*** Error: Missing data, run self.readGamessLog().")


    def writeMoldenFile2006(self):
        """
        Write data to Molden format file using reformatted CCLIB code, for ePS compatible 'Molden2006' formatting.

        See :py:class:`moldenCCLIBReformatted` for details.

        """

        try:
            # Convert to Molden format
            f = 'molden'  # Set output format
            # self.moldenFile = self.fullPath.with_suffix('.' + f)
            # cclib.io.ccwrite(self.data, terse=True, outputtype=f, outputdest=self.moldenFile.as_posix())  # From data

            # Set object
            self.moldenData = moldenCCLIBReformatted(self.data)

            # Write to file using modified functions
            # Note newline='\n' to force Unix style output (default will otherwise use os.linesep, see https://docs.python.org/3/library/functions.html#open).
            with open(self.moldenFile, 'w', newline='\n') as f:
                # f.write(self.moldenData.generate_repr())  # Write full file - no further reformatting

                # With additional per-line checks
                moldenRepr = self.moldenData.generate_repr().split('\n')

                for line in moldenRepr:
                    if line.startswith(' Sym='):
                        pass   # Skip ' Sym=XX' orbital defn. lines, not in standard Molden 2006 output.
                    else:
                        # f.write(line, end='')
                        f.write(f'{line}\n')

            print(f"Written Molden2006 format file {self.moldenFile}")
            # self.reformatMoldenFile()

        # Generic error case, usually due to None returned from cclib.
        except AttributeError:
            print(f"*** Error: Missing data, run self.readGamessLog().")



    def reformatMoldenFile(self, inplace = True, backup = '', verbose = False):
        """
        Reformat atom details & coords in an exisiting Molden file to match ePS IO "Molden2006" formatting.

        Uses data in existing file, as set in self.moldenFile.

        Notes
        -----

        Default settings use inplace writing to replace existing file, pass backup='.bk' to set backup file extension for original file contents.

        See https://docs.python.org/3/library/fileinput.html#fileinput.FileInput for details.

        """

        lines = []

        # Get lines for reformat using standard function
        startPhrase="[Atoms]"
        endPhrase="[GTO]"   # None  #

        (lineListAtoms, dumpSegs) = fileParse(self.moldenFile, startPhrase, endPhrase, verbose=verbose)  # Why is this not returning any lines...????
        lineListAtoms = list(range(lineListAtoms[0][0]+1, lineListAtoms[1][0]))

        startPhrase="[GTO]"
        endPhrase="[MO]"   # None  #

        (lineListGTO, dumpSegs) = fileParse(self.moldenFile, startPhrase, endPhrase, verbose=verbose)  # Why is this not returning any lines...????

        lineListGTO = list(range(lineListGTO[0][0], lineListGTO[1][0]))

        # Context manager version of inplace file replace
        # From https://stackoverflow.com/a/58217364
        # Thanks Akif!

        with fileinput.input(self.moldenFile, inplace=inplace, backup = backup) as f:
            for line in f:

                if fileinput.filelineno() in lineListAtoms:
                    line = ' {:<2} {:>4} {:>4} {:>16} {:>19} {:>19} \n'.format(*line.split())


                # Undo scientific notation if set (see, e.g. lines from, and to reverse, cclib.io.molenWriter.py, lines 267-271)
                # May not be necessary for ePS IO?
                if (fileinput.filelineno() in lineListGTO) and ('e' in line):
#                     vals = line.split()
#                     vals = [self.scinotation(i) for i in vals]
#                     line = ' '.join(vals)
#                     line = f" {line.replace('e','D')}"  # TODO: fix -ve number alignment?
                    line = '{:>18}{:>18} \n'.format(*line.replace('e','D').split())


                if line.startswith(' Sym='):
                    pass   # Skip ' Sym=XX' orbital defn. lines, not in standard Molden 2006 output.
                else:
                    # print(line, end='')  # end='' to avoid adding extra newline chars and double spacing! Do need to manually add above however.
                    print(line, end='\n')  # TESTING - need to force Unix line endings here.

        print(f"*** Molden file {self.moldenFile} reformatted for ePS.")


# Try redefining existing methods - class version with inheritance
class moldenCCLIBReformatted(moldenwriter.MOLDEN):
    """
    Patch for cclib's modenwriter to conform to ePS 'Molden2006' format spec.

    This class inherits from :py:class:`cclib.io.moldenwriter.MOLDEN` (`github source <https://github.com/cclib/cclib/blob/bbc231295e64c7f25d5d235492c103688a4e068b/cclib/io/moldenwriter.py#L34>`_), and:

    - Redefines :py:func:`_coords_from_ccdata` and :py:func:`_gto_from_ccdata`.
    - :py:func:`_coords_from_ccdata`  uses super() to run the original function, than applies a slightly different coordinates format spec. to the output.
    - :py:func:`_gto_from_ccdata` is basically a modified version of the original cclib code, again with just a modified format spec.

    Thanks to `the CCLIB authors <https://cclib.github.io/>`_ for making this possible!

    """

    def _coords_from_ccdata(self, index):
        """
        Create [Atoms] section for 'Molden2006' output.

        Runs super :py:method:`cclib.io.moldenwriter.MOLDEN._coords_from_ccdata` then modifies output format before return.

        """

        lines = super()._coords_from_ccdata(index)  # Just use super here? Can't remember how to test this when monkey patching however - doesn't resolve properly?
    #     super()

        linesReformat = []
        for line in lines:
            # line = ' {:<2} {:>4} {:>4} {:>16} {:>19} {:>19} \n'.format(*line.split())
            # linesReformat.append('{:>3} {:>5} {:>5} {:>20} {:>20} {:>20}'.format(*line.split()))
            linesReformat.append('{:<2} {:>4} {:>4} {:>16} {:>19} {:>19}'.format(*line.split()))

        return linesReformat


    # Code from cclib, with minor mods, see https://github.com/cclib/cclib/blob/bbc231295e64c7f25d5d235492c103688a4e068b/cclib/io/moldenwriter.py#L68
    def _gto_from_ccdata(self):
        """
        Create [GTO] section for 'Molden2006' output.

        Modified code from :py:method:`cclib.io.moldenwriter.MOLDEN._gto_from_ccdata` with format changes.

        `github source <https://github.com/cclib/cclib/blob/bbc231295e64c7f25d5d235492c103688a4e068b/cclib/io/moldenwriter.py#L34>`_

        Note: this currently sets output format to standard scientific notation, but replaces 'e' with 'D'. May also need to fix exponent, e.g. https://stackoverflow.com/a/8262434

        """

        gbasis = self.ccdata.gbasis
        label_template = ' {:s}{:5d} 1.00'     # Changed spacing here - single space for basis label, three spaces for components.
        # basis_template = '{:15.9e} {:15.9e}'  # Original format
        basis_template = ' {:> 15.10e} {:> 15.10e}'
        # basis_template = '   {:>15}  {:>15}'
        lines = []

        for no, basis in enumerate(gbasis):
            lines.append('{:3d} 0'.format(no + 1))
            for prims in basis:
                lines.append(label_template.format(prims[0].lower(),
                                                   len(prims[1])))
                for prim in prims[1]:
                    lines.append(basis_template.format(prim[0], prim[1]))

                    lines[-1] = lines[-1].replace('e','D')  # Added for D format output - may not be required


            lines.append('')
        lines.append('')
        return lines
