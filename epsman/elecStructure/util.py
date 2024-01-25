"""
ePSman electronic structure utility functions
--------------------------------

Utility functions for use with ePSman.

24/01/24   v1

See also ../_util.py for general utility functions

"""

from epsman._util import fileParse
import pandas as pd


def readMoldenGeoms(fileName, keyWord='[Atoms]', 
                    skiprowsOffset = 0, nrowType='auto',
                    widths = [2,7,7,20,20,20],
                    names= ['Ind','Species','Atomic Num.','x','y','z'],
                    verbose = 0):
    """
    Read geometry/ies in Molden format.
    
    Parameters
    ----------
    fileName : str or Path object
        File to read.
        
    keyWord : str, default = '[Atoms]'
        Keyword to search for in file.
        Default case flags Molden geometry sections.
        If multiple sections are found they will all be read in.
        
    skiprowsOffset : int, default = 0
        Additional header rows to skip.
        Default case 
    
    nrowType : str or int, default = 'auto'
        If 'auto' tries to read all lines until next section.
        If an int, read this number of lines after keyWord.
        
    widths : list, default = [2,7,7,20,20,20]
        Column widths, passed to pd.read_fwf() for reading sections.
        Default case for normal Molden format.
    
    names : list, default = ['Ind','Species','Atomic Num.','x','y','z']
        Columns names.
        Default case matches epsman.elecStructure.gamess.getAtoms()  
        
    Returns
    -------
    dict
        Contains geometries keyed by integer, as Pandas DataFrames.
        Also key 'details' for metadata.
        
        
    Notes
    -----
    
    - RDkit doesn't read Molden format.
    - RDkit does support a range of other file types, [x,y,z] might be sufficient? https://www.rdkit.org/docs/source/rdkit.Chem.rdmolfiles.html#rdkit.Chem.rdmolfiles.MolFromXYZFile
    - RDkit does support Pandas, but only for table of molecules output? E.g. https://xinhaoli74.github.io/blog/rdkit/2021/01/06/rdkit.html#PandasTools, http://rdkit.org/docs/source/rdkit.Chem.PandasTools.html
    - CCLIB writes, but doesn't read, Molden format. Could still be used for conversion to SDF for RDkit...?
        
    """

    print(f"*** Reading geometries from file {fileName}...")
    
    # lineNumbers, fileSegs = IO.fileParse(fileName, startPhrase=keyWord, verbose=1)  # With no endPhrase, this gets correct line-list, but pulls everything as a single segment
    lineNumbers, fileSegs = fileParse(fileName, startPhrase=keyWord, endPhrase=keyWord, verbose=verbose)  # With endPhrase this gets correct line-list, but segments are blank.
    
    # Read with pandas?
    geomDict = {}
    
    for n,item in enumerate(lineNumbers[0]):

        if verbose > 1:
            print(f"Reading {n}, lines: {item}")
        
        if nrowType == 'auto':
            try:
                nrows = (lineNumbers[0][n+1]-3+skiprowsOffset) - (lineNumbers[0][n]-1+skiprowsOffset)

            except IndexError:
                nrows = None  # For final item set None to read to end of file.
        else:
            nrows = nrowType
            
        
        geomDict[n] = {'pd':pd.read_fwf(fileName, skiprows=lineNumbers[0][n] + skiprowsOffset, nrows=nrows, 
                                  header=None, names= ['Species','Ind','Atomic Num.','x','y','z'],  # Col names to match  epsman.elecStructure.gamess.getAtoms()       # ['index','mass','x','y','z'], 
                                  widths = [2,7,7,20,20,20])  #, index_col=0)  # Set index col if required
                      }

#         geomDict[n]['pd'].index.rename('atom',inplace=True)

        # Redored index?
        geomDict[n]['pd'] = geomDict[n]['pd'].iloc[:, [1, 0, 2, 3, 4, 5]]
        
        # Reindex to 0-offset if required
        if geomDict[n]['pd']['Ind'].min() == 1:
            geomDict[n]['pd']['Ind'] = geomDict[n]['pd']['Ind'] -1
    
        # Set positions-only dictionary form for use with existing `setCoords()` method
        geomTemp = geomDict[n]['pd'].to_dict()
        geomDict[n]['positionsDict'] = {k:[geomTemp['x'][k], geomTemp['y'][k], geomTemp['z'][k]] for k in geomTemp['Ind'].keys()}
        
    
    geomDict['details'] = { 'file': fileName,
                            'lineNumbers': lineNumbers,
                            'key word matches': len(lineNumbers[0]),
                            'geoms':len(geomDict)
                          }
    
    print(f"Read {geomDict['details']['geoms']} geometries.")
    
    return geomDict