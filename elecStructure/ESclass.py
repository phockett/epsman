"""
Basic methods for dealing with Gamess & Molden file IO for ePolyScat.

03/02/21 v2 Revisiting and finishing off...
            - Fixed formatting options.
            - Added wrappers for cclib moldenwriter.MOLDEN as new class.
            - Use EShandler class for general IO.

26/08/20 v1 Quick hack from existing functions - needs some more sophistication for file handling. Should have utils for this...

Dev work currently in [Bemo] http://localhost:8888/notebooks/ePS/N2O/N2O_electronic_structure_proc_tests_250820.ipynb

"""

import fileinput
import sys
from pathlib import Path

import cclib
from cclib.io import moldenwriter  # Molden class + functions



class EShandler():
    """
    Basic class for handling Gamess & Molden file IO.

    Uses `CCLIB <https://cclib.github.io/>`_ to read Gamess log files & convert to Molden format.

    For ePS compatibilty, this is slightly modified to match the "Molden2006" specifications defined therein (see source in `MoldenCnv2006.f90`).

    Parameters
    -----------



    Example
    -------
    >>> fileBase = Path(modPath, 'epsman', 'elecStructure','fileTest')  # Set for test file, where modPath = path to epsman root
    >>> fileName = r'N2O_aug-cc-pVDZ_geomOpt.log'
    >>> esData = EShandler(fileName, fileBase)  # Create class instance
    >>> esData.readGamessLog()  # Read Gamess file
    >>> esData.writeMoldenFile2006()  # Write Molden2006 file
    >>> esData.writeMoldenFile()  # Write Molden file as per CCLIB defaults.

    >>> esData = EShandler(fileName = 'test.molden') # Pass a Molden file to set & use the reformatter
    >>>
    >>> esData.reformatMoldenFile()

    Notes
    -----

    Thanks to `the CCLIB authors <https://cclib.github.io/>`_ for making this possible!

    To do
    -----
    - Implement directory scan (or wrapper class/decorator for this).
    - Better file handling, should implement Pathlib tests for file(s).

    """


    def __init__(self, fileName = None, fileBase = None, outFile = None):

        self.setFiles(fileName=fileName, fileBase=fileBase, outFile=outFile)

        # If a Gamess file is passed, read it.
        if (self.fileName is not None) and (self.fileName.suffix != '.molden'):
            self.readGamessLog()


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
                print('TODO - implement dir scan here')

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

        print(f'Set input file as {self.fullPath}, use self.setFiles to change.')
        print(f'Set output file as {self.moldenFile}, use self.setMoldenFile to override.')


    def setMoldenFile(self, fileName, fileBase = None):
        """Set self.moldenFile with new fileName and existing path, or new path."""

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
        self.data = cclib.io.ccread(self.fullPath.as_posix())
        print(f"Read file {self.fullPath}")

        try:
            print("Read %i atoms and %i MOs" % (self.data.natom, self.data.nmo))

        # Generic error case, usually due to None returned from cclib.
        except AttributeError:
            print(f"*** Error: File {self.fullPath} not found or empty.")



    def writeMoldenFile(self):
        """
        Write data to Molden format file using CCLIB

        """

        # Convert to Molden format
        cclib.io.ccwrite(self.data, terse=True, outputtype='molden', outputdest=self.moldenFile.as_posix())  # From data

        print(f"Written Molden format file {self.moldenFile}")
        self.reformatMoldenFile()


    def writeMoldenFile2006(self):
        """
        Write data to Molden format file using reformatted CCLIB code, for ePS compatible 'Molden2006' formatting.

        """

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
                    print(line, end='')  # end='' to avoid adding extra newline chars and double spacing! Do need to manually add above however.

        print(f"*** Molden file {self.moldenFile} reformatted for ePS.")


# Try redefining existing methods - class version with inheritance
class moldenCCLIBReformatted(moldenwriter.MOLDEN):
    """
    Pathc for cclib's modenwriter to conform to ePS 'Molden2006' format spec.

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





# FILEPARSE from epsproc
# Should just import... but included directly here for now!

# File parsing function - scan file for keywords & read segments
#   Following above idiomatic solution, with full IO
#   https://stackoverflow.com/questions/3961265/get-line-number-of-certain-phrase-in-file-python
def fileParse(fileName, startPhrase = None, endPhrase = None, comment = None, verbose = False):
    """
    Parse a file, return segment(s) from startPhrase:endPhase, excluding comments.

    Parameters
    ----------
    fileName : str
        File to read (file in working dir, or full path)
    startPhrase : str, optional
        Phrase denoting start of section to read. Default = None
    endPhase : str, optional
        Phrase denoting end of section to read. Default = None
    comment : str, optional
        Phrase denoting comment lines, which are skipped. Default = None

    Returns
    -------
    list
        [lineStart, lineStop], ints for line #s found from start and end phrases.
    list
        segments, list of lines read from file.

    All lists can contain multiple entries, if more than one segment matches the search criteria.

    """

    lineStart = []    # Create empty list to hold line #s
    lineStop = []     # Create empty list to hold line #s
    segments = [[]]   # Possible to create empty multi-dim array here without knowing # of segments? Otherwise might be easier to use np textscan functions
    readFlag = False
    n = 0

    # Force list to ensure endPhase is used correctly for single phase case (otherwise will test chars)
    if type(endPhrase) is str:
        endPhrase = [endPhrase]

    # Open file & scan each line.
    with open(fileName,'r') as f:
        for (i, line) in enumerate(f):  # Note enumerate() here gives lines with numbers, e.g. fullFile=enumerate(f) will read in file with numbers
            i = i + 1  # Offset for file line numbers (1 indexed)
            # If line matches startPhrase, print line & append to list.
            # Note use of lstrip to skip any leading whitespace.
            # if startPhrase in line:
            if line.lstrip().startswith(startPhrase):
                if verbose:
                    print('Found "', startPhrase, '" at line: ', i)

                lineStart.append(i)

                readFlag = True

            # Read lines into segment[] until endPhrase found
            if readFlag:
                # Check for end of segment (start of next Command sequence)
                if endPhrase and ([line.startswith(endP) for endP in endPhrase].count(True) > 0):  # This allows for multiple endPhases
                                                                                                    # NOTE: this will iterate over all chars in a phrase if a single str is passed.
                    # Log stop line and list
                    lineStop.append(i)
                    readFlag = False

                    # Log segment and create next
                    segments.append([])
                    n += 1

                    continue            # Continue will skip rest of loop

                 # Check for comments, skip line but keep reading
                elif comment and line.startswith(comment):
                    continue            # Continue will skip rest of loop

                segments[n].append([n, i, line])    # Store line if part  of defined segment

    if verbose:
        print('Found {0} segments.'.format(n+1))

    return ([lineStart, lineStop], segments) # [:-1])
