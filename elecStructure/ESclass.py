# Stick above methods into class.
# May want to also inherit from cclib? Not sure.

import fileinput
import sys
from pathlib import Path

import cclib



class EShandler():
    """
    Basic methods for dealing with Gamess & Molden file IO for ePolyScat.

    26/08/20 v1 Quick hack from existing functions - needs some more sophistication for file handling. Should have utils for this...

    Dev work currently in [Bemo] http://localhost:8888/notebooks/ePS/N2O/N2O_electronic_structure_proc_tests_250820.ipynb

    """

    def __init__(self, fileName = None, fileBase = None):

        # Set fileBase and fileName - for now no error checking here
        if fileBase is None:
            self.fileBase = Path.cwd()
        else:
            self.fileBase = Path(fileBase)

        if fileName is None:
            print('TODO - implement dir scan here')
        else:
            self.fileName = Path(fileName)

        self.fullPath = (self.fileBase/self.fileName)
#         print(self.fullPath)

        self.readGamessLog()


    def readGamessLog(self):
        self.data = cclib.io.ccread(self.fullPath.as_posix())
        print(f"Read file {self.fullPath}")
        print("Read %i atoms and %i MOs" % (self.data.natom, self.data.nmo))


    def writeMoldenFile(self):
        # Convert to Molden format
        f = 'molden'  # Set output format
        self.moldenFile = self.fullPath.with_suffix('.' + f)
        cclib.io.ccwrite(self.data, terse=True, outputtype=f, outputdest=self.moldenFile.as_posix())  # From data

        print(f"Written Molden format file {self.moldenFile}")
        self.reformatMoldenFile()


    def reformatMoldenFile(self):
        """
        Reformat atom details & coords in Molden file to match ePS IO.

        """

        # Get lines for reformat using standard function
        startPhrase="[Atoms]"
        endPhrase="[GTO]"   # None  #

        (lines, dumpSegs) = fileParse(self.moldenFile, startPhrase, endPhrase, verbose=False)  # Why is this not returning any lines...????


        # Context manager version of inplace file replace
        # From https://stackoverflow.com/a/58217364
        # Thanks Akif!

        with fileinput.input(outFile, inplace=True) as f:
            for line in f:
        #         new_line = line.replace(search_text, new_text)
        #         print(new_line, end='')
                if fileinput.filelineno() in lineList:
                #         print('{:>3} {:>5} {:>5} {:>20} {:>20} {:>20}'.format(*testLine.split()), end='') # Works, although single line outout
                        line = '{:>2} {:>4} {:>4} {:>16} {:>19} {:>19} \n'.format(*line.split())

        #         sys.stdout.write(line)  # No output in file?
                print(line, end='')  # end='' to avoid adding extra newline chars and double spacing! Do need to manually add above however.

        print(f"*** Molden file {self.moldenFile} reformatted for ePS.")


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
