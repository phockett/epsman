"""
Class for basic handling of Gamess jobs using pyGamess and RDKit as backend.

26/02/21

Libraries:

- `pygamess <https://github.com/kzfm/pygamess>`_ (also `on pypi <https://pypi.org/project/pygamess/>`_)
- `RDKit <https://rdkit.org/docs/index.html>`_
- `PubChemPy <https://pypi.org/project/PubChemPy/>`_
- `py3Dmol <https://pypi.org/project/py3Dmol/>`_

Aims here:

- Wrap pygamess functionality with Fabric for client-host architecture.
   - UPDATE: actually, this is now written to run on local host, and assumed to be wrapped by Fabric at a higher level. This allows for all files & routines in pyGamess to run locally.
   - Might change this in future...? Possibly with remote calls to this routine?
   - Additional file parsing, e.g. "***** EQUILIBRIUM GEOMETRY LOCATED *****", "EXECUTION OF GAMESS TERMINATED NORMALLY" etc. (Check existing pyGamess methods first.)
- Enable full ePS job pipeline, starting with a Gamess calculation.
- Provide methods for generating ePS jobs with multiple inputs, e.g. bond length scans.

28/11/23 updates

- Added setCoords() dispatcher, and methods _setCoordsPD() and _setCoordsDict().
- Added genXYZ() for XYZ string creation.
- Added molFromXYZ() for XYZ molecule generation.

"""

from pygamess import Gamess
import numpy as np
import re
import io
from copy import deepcopy

from pathlib import Path
import os

import logging

from epsman._util import isnotebook, CustomStreamHandler

# TODO: remember how to handle this elegantly/selectively - would still like to create empty class.
try:
    from rdkit import Chem
    from rdkit.Chem import rdDetermineBonds  # For XYZ mol creation routines.
    from rdkit.Chem import AllChem  # Larger import, generally won't need all this functionality...?

    # Quick module check for py3Dmol, required for rdkit 3D plotting routines.
    # From https://stackoverflow.com/a/14050282
    import importlib
    spec = importlib.util.find_spec("py3Dmol")   #("spam")
    found = spec is not None
    if not found:
        print("*** py3Dmol not available, 3D plots with RDkit will not be available.")

except ImportError:
    print("*** RDkit not available, molecule generation functions will not be available.")
    # rdkFlag = False

try:
    import pubchempy as pcp

    # For PUGREST errors.
    from pubchempy import NotFoundError
    from urllib.error import HTTPError

except ImportError:
    print("*** PubChemPy not available, molecule download functions will not be available.")

pdFlag=False
try:
    import pandas as pd
    pdFlag=True
except ImportError:
    print("*** Pandas not available, fancy tabulated data display will not be available.")


class ESgamess():
    """
    Class to wrap pygamess + epsman functionality.
    
    Demo: https://epsman.readthedocs.io/en/latest/demos/ESgamess_class_demo_300321.html

    Basic Gamess job setup and handling from `pygamess docs <https://github.com/kzfm/pygamess#basic-usage>`_, with `RDKit <https://rdkit.org/docs/index.html>`_ on the backend.

    Currently wraps:

    - molFromSmiles(), molFromFile(), for core RDkit molecule creation
    - molFromPubChem(), for PubChemPy molecule downloader
    - molFromXYZ(), for XYZ string or file molecule definition (requires RDkit > 2022.3)


    TODO:

    - More RDkit functionality, see https://www.rdkit.org/docs/source/rdkit.Chem.rdchem.html#rdkit.Chem.rdchem.RWMol
    
    Note on params:
    
    - After initGamess(), Gamess config set in self.params.
    - Modify with dict syntax by  input section group (see https://www.msg.chem.iastate.edu/gamess/GAMESS_Manual/input.pdf)
          E.g. for maxit=40, set self.params['contrl']['maxit'] = 40
    - TODO: wrap this? Existing methods in Pygamess?

    """

    from epsman._util import setAttribute, checkLocalFiles

    __notebook__ = isnotebook()


    def __init__(self, searchName = None, smiles = None, molFile = None, xyz = None,
                    addH = False, molOverride = None,
                    job = None, sym = 'C1', atomList = None, verbose = 1,
                    precision = 6,
                    buildES = False, fileOut = None):

        self.verbose = verbose

        # Setup molecule
        self.setAttribute('name', searchName)
        self.setAttribute('smiles', smiles)
        self.setAttribute('molFile', molFile)   # Path(molFile))  # Don't force to Path here, errors if None.
        self.setAttribute('xyz',xyz, printFlag=False)  # Skip printing in this case!

        # molOverride is set as a dictionary of atoms, e.g. {0:{'name':'H', 'Z': 1, 'coords':[0.0, 0.0, 1.0]}, 1:{'name':'C', 'Z': 16, 'coords':[0.0, 0.0, 4.0]}}.
        # This will be used at Gamess input file write INSTEAD of self.mol if set.
        # Note Z must be an int here currently - Gamess writer appends '.0' in current codebase.
        self.setAttribute('molOverride', molOverride)

        # Try to setup molecule from input
        self.molFromFile()
        self.molFromPubChem()
        self.molFromSmiles(addH = addH)
        self.molFromXYZ()


        # Additional vars for Gamess job
        # Set default to None to allow easy overwrite later... or set to 'Default' and 'C1' for always running config?
        # Issue is as usual - when should these be set to defaults, and should they always be overwritten by new input by default?
        self.setAttribute('job', job)
        self.setAttribute('sym', sym)
        self.setAttribute('atomList', atomList)
        self.setAttribute('precision', precision)  # Added 08/12/23, used for roundCoords() only so far.

        # Display some output unless mol is empty
        if hasattr(self, 'mol'):
            
            # Add atomsDict, refDict and atomsHist
            for item in ['atomsDict', 'refDict', 'atomsHist']:
                self.setAttribute(item, {})
            
            # Round coords and fix -ve 0 issues & update system
            # Added 08/12/23, also run self.setTable and self.getAtoms to create required pdTable.
            if self.precision is not None:
                self.getAtoms()
#                 self.pdTable = self.setTable(self.atomsDict)
                self.setTable()
                self.roundCoords(decimals = self.precision, updateCoords = True, useRef = False, 
                                 force = True, printTable = False)
        
            try:
                if self.__notebook__:
                    display(self.mol)  # If notebook, use display to push plot.
                else:
                    # return hv.Curve(d0)  # Otherwise return hv object.
                    pass
            except:
                pass

            # self.printCoords()
            self.printTable()

            # Automatic Gamess pipeline execution
            if buildES:
                self.buildES(fileOut)
                
        # Set pyGamess basis dict for reference
        self.listBasis()


#***** BASIC MOLECULE SETUP ROUTINES

    def molFromSmiles(self, addH = False, canonicalise=True, runOpt=True):
        """
        Generate molecule from smiles following `pygamess docs <https://github.com/kzfm/pygamess#basic-usage>`_.

        See also `RDkit docs <https://www.rdkit.org/docs/source/rdkit.Chem.rdmolfiles.html?highlight=molfromsmiles#rdkit.Chem.rdmolfiles.MolFromSmiles>`_.

        Parameters
        ----------
        addH : bool, default = False
            Add hydrogens?

        canonicalise : bool, default = True
            Canonicalise?
            This runs :py:func:`rdkit.Chem.rdMolTransforms.CanonicalizeConformer` (see `RDkit docs <https://rdkit.org/docs/source/rdkit.Chem.rdMolTransforms.html#rdkit.Chem.rdMolTransforms.CanonicalizeConformer>`__.)

        runOpt : bool, default = True

        """

        if self.smiles is not None:

            self.mol = Chem.MolFromSmiles(self.smiles)

            if addH:
                self.mol = Chem.AddHs(self.mol)

            # self.mol_with_atom_index()
            AllChem.EmbedMolecule(self.mol)   # This creates a conformer idx=0, with (arb?) coords

            if runOpt:
                # Basic geom routine to set some positions
                AllChem.UFFOptimizeMolecule(self.mol,maxIters=200)  # Try basic opt

            # Canonicalise? This sets x-axis as highest sym axis, see https://rdkit.org/docs/source/rdkit.Chem.rdMolTransforms.html#module-rdkit.Chem.rdMolTransforms
            if canonicalise:
                AllChem.CanonicalizeConformer(self.mol.GetConformer())

        else:
            pass


    def molFromFile(self):
        """
        Get molecule from Mol/SDF file.

        Currently assumes only one molecule per file, but can use SDMolSupplier for muliple molecule case.

        See

        - https://www.rdkit.org/docs/GettingStartedInPython.html#reading-single-molecules
        - https://www.rdkit.org/docs/GettingStartedInPython.html#reading-sets-of-molecules

        """

        if self.molFile is not None:

            self.mol = Chem.MolFromMolFile(Path(self.molFile).as_posix())



        # Display...


    def molFromPubChem(self, searchTerm = None, searchType = 'name', fileName = None, fileType = 'SDF', recordType = '3d', overwrite = False):
        """
        Download data from PubChem using PubChemPy wrapper.

        Details:

        - Searching: https://pubchempy.readthedocs.io/en/latest/guide/searching.html
        - Downloading: https://pubchempy.readthedocs.io/en/latest/guide/download.html
        - Full options list (PubChem REST API): https://pubchemdocs.ncbi.nlm.nih.gov/pug-rest

        fileTypes: XML, ASNT/B, JSON, SDF, CSV, PNG, TXT

        searchType: As per `pcp.get_compounds <https://pubchempy.readthedocs.io/en/latest/api.html#search-functions>`_
                "The identifier type, one of cid, name, smiles, sdf, inchi, inchikey or formula."


        Set recordType = '3d' to ensure 3D coords returned.

        """
        # TODO: check ESclass for existing Gamess file handling.
        # If a filename is set, use it with new suffix
        # if (self.molFile is not None) and (fileName is None):
        #     fileName = (self.molFile).with_suffix(fileType)
        #
        # elif fileName is None:
        #     fileName = Path(Path.cwd(), searchTerm, fileType)

        # Set to master, then just use this
        self.setAttribute('molFile', fileName)
        self.setAttribute('name', searchTerm)

        # Search & download result(s) if searchTerm/name is set
        readFlag = False
        if self.name is not None:
            if self.molFile is None:
                self.molFile = Path(Path.cwd(), self.name).with_suffix('.' + fileType)

            try:
                pcp.download(fileType, self.molFile, self.name, searchType, record_type=recordType)
                readFlag = True

            # Very basic error checking, may want to more carefully parse PUGrest errors?
            except (HTTPError, NotFoundError) as err:
            # except HTTPError as err:
                print("*** Bad response from PubChem URL request, try running self.molFromPubChem(recordType='2d')")
                print(err)

            except IOError as err:
                print(f'*** File {self.molFile} already exists; existing file will be used. Pass overwrite=True to overwrite.')
                readFlag = True

        # TODO: print or return something here...
        # print()

        if readFlag:
            self.molFromFile()  # Try reading file


    def molFromXYZ(self):
        """
        Basic wrapper for Chem.MolFromXYZBlock() and Chem.MolFromXYZFile().
        
        Molecule creation from basic XYZ format (see https://en.wikipedia.org/wiki/XYZ_file_format):
        
        ```
        [no. atoms]
        [comment line, can be blank]
        [Atom 0] [x] [y] [z]
        [Atom 1] [x] [y] [z]
        ...
        
        ```
        
        To generate from an existing structure, use self.genXYZ().
        
        """
        
        if self.xyz is not None:
            if hasattr(Chem, 'MolFromXYZBlock'):
                
                molXYZ = False
                
                # Crude string check - if from string will have newlines.
                if '\n' in self.xyz:
                    molXYZ = Chem.MolFromXYZBlock(self.xyz)
                    
                else: 
                    fileCheck = self.checkLocalFiles([self.xyz])[0]  # Explicitly support only single file here.
                    
                    if fileCheck:
                        molXYZ = Chem.MolFromXYZFile(self.xyz)  # May want Path().as_posix() and file checks here.
                    else:
                        print(f"*** File {self.xyz} not found.")
                
                # Proceed to tidy-up if molXYZ has now been set.
                if molXYZ:
                    # Tidy up, per https://mattermodeling.stackexchange.com/questions/10561/unexpected-atoms-while-working-with-xyz-files-in-rdkit
                    # And https://github.com/rdkit/UGM_2022/blob/main/Notebooks/Landrum_WhatsNew.ipynb
                    # Without this can get multiple separate molecules with H added
                    conn_mol = Chem.Mol(molXYZ)
                    Chem.rdDetermineBonds.DetermineConnectivity(conn_mol)
                    Chem.rdDetermineBonds.DetermineConnectivity

                    # Set output
                    self.mol = conn_mol
                else:
                    print("Failed to set molecule from XYZ format, check `self.xyz` has valid input (XYZ string or filename).")
                
            else:
                print("Failed to set molecule from XYZ format, `Chem.MolFromXYZ` methods missing. RDkit may need updating (v>2022.3).")
            
        else:
            pass
            
            
            

    def mol_with_atom_index(self):
        """
        Display molecule including atom indexes.

        Adapted from the RDKit cookbook: https://www.rdkit.org/docs/Cookbook.html
        """

        for atom in self.mol.GetAtoms():
            atom.SetAtomMapNum(atom.GetIdx())
        # return mol

        # TODO: add disply checking functionality.
        # Alternatively, just return mol object
        if self.__notebook__:
            display(self.mol)

    def plot2D(self, atomIndex=True):
        """2D plot using RDkit functionality, with optional atom index labels"""

        if self.__notebook__:
            if atomIndex:
                display(self.mol_with_atom_index())
            else:
                display(self.mol)


    def plot3D(self, style='stick'):
        """
        Thin wrapper for RDkit AllChem.Draw.IPythonConsole.drawMol3D(self.mol), needs py3Dmol library.

        Style is one of 'stick' (default), 'sphere', 'line', 'cross', 'cartoon'.
        See the `3Dmol docs for details <https://3dmol.csb.pitt.edu/doc/index.html>`__

        """

        if self.__notebook__:
            AllChem.Draw.IPythonConsole.drawMol3D(self.mol,drawAs=style)


#***** MOLECULE MODIFICATION ROUTINES

    def setCoords(self, coords = None, refKey = None, useRef = True, 
                  force = False, printTable = True):
        """
        Dispatcher for setCoords methods. Pass new coords as dictionary or Pandas DataFrame.
        New coords will be applied to the system, and updated in self.mol and self.pdTable.
        
        Parameters
        ----------
        coords : Pandas DataFrame or dictionary of new coordinates.
            If DataFrame, this will be compared to the reference case to ensure atom label consistency. Format should match self.pdTable, as generated by the self.printTable() method. Pass refKey and/or useRef args for more control (see below).
            If dictionary, format is `{atomLabel:[x,y,z]}`, e.g. pass coordList = {1:[0,0,0]} to set atom 1 to [0,0,0].
            Note that the dictionary case currently does not check for atom consistency.
            
        refKey : str, optional, default = None
            Key for reference data in self.refDict[refKey].
            If None, and useRef=True, the default case will be used (refKey='ref').
            If None, and useRef=False, use self.pdTable for consistency checks.
            (Applies only to Pandas DataFrame case.)
            
        useRef : bool, optional, default = True
            Use reference case to confirm atoms?
            If False, use self.pdTable for atom label checks. 
            (Applies only to Pandas DataFrame case.)
            
        force : bool, optional, default = False
            For Pandas table case only, if True skip any checks vs. existing table.
        
        printTable : bool, optional, default = True
            If True, and self.verbose, show output table.
            
        """
        
        # Dispatch to methods according to data type.
        if pdFlag:
            if type(coords) is pd.core.frame.DataFrame:
                print("*** Updating coords (Pandas version).")
                self._setCoordsPD(coords, refKey = refKey, useRef = useRef, 
                                  force = force, printTable = printTable)
                
        elif type(coords) is dict:
            print("*** Updating coords (dictionary version).")
            self._setCoordsDict(coords)
            
        else:
            print(f"*** Failed to set new coords from datatype {type(coords)}, please pass dictionary or Pandas DataFrame.")
        
 

    # setCoords testing - use Pandas table to confirm some properties...
    # See also runGeomScan for higher-level wrapper (although no checks there currently)
    def _setCoordsPD(self, newTable, refKey = None, useRef = True, 
                     force = False, printTable = True):
        """
        Use new DataFrame to set coords. If self.verbose !=0 updated coord tables will be displayed.
        
        On the backend, uses self._setCoordsDict() and RDkit conformer.SetAtomPosition() to update coord table.
        
        Parameters
        ----------
        coords : Pandas DataFrame of new coordinates.
            This will be compared to the reference case to ensure atom label consistency. Format should match self.pdTable, as generated by the self.printTable() method. Pass refKey and/or useRef args for more control (see below).
            
        refKey : str, optional, default = None
            Key for reference data in self.refDict[refKey].
            If None, and useRef=True, the default case will be used (refKey='ref').
            If None, and useRef=False, use self.pdTable for consistency checks.
            (Applies only to Pandas DataFrame case.)
            
        useRef : bool, optional, default = True
            Use reference case to confirm atoms?
            If False, use self.pdTable for atom label checks. 
            (Applies only to Pandas DataFrame case.)
            
        force : bool, optional, default = False
            If True skip any checks vs. existing table.
            
        printTable : bool, optional, default = True
            If True, and self.verbose, show output table.
            
        """

#         print("*** Updating coords (Pandas version).")

        # Set reference from existing coords or refKey
        if refKey is None:
            if useRef:
                if self.verbose:
                    print("Reference coords:")
                    
                self.setRef()
                refKey = 'ref'  # Default case
                refTable = self.refDict[refKey]['pd']

            else:
                refTable = self.pdTable

        else:
            refTable = self.refDict[refKey]['pd']

        if not force:
            # Compare newTable with refTable
            # This should allow for a quick check on veracity, i.e. if any atoms don't match the ref structure, and force indexing to be consistent.
            dfNew =  pd.merge(refTable, newTable, on=['Species','Atomic Num.'], suffixes=('_orig','_new'))

            # For cases with multiples of same species, this may result in additional entries - check and fix
            # NOTE this may have issues if Inds unaligned/broken? TBC.
            if dfNew.shape[0] != refTable.shape[0]:
                print(f"*** Warning, found duplicate entries when attempting to merge DataFrames, attempting to fix. Check self.coordDebug for details, or use dictionary methods to bypass.")
                display(dfNew)
                self.coordDebug = {'dfNewDupes':dfNew,
                                   'refTable':refTable,
                                   'newTable':newTable
                                  }   # Set for debugging!

                # This may result in duplicate coords for Ind_orig != Ind_new cases
    #             dfNew = dfNew.iloc[dfNew['Ind_orig'].unique()]

                # This works, but assumes Inds match (?)
                dfNew =  pd.merge(refTable, newTable, on=['Ind','Species','Atomic Num.'], suffixes=('_orig','_new'))
                dfNew.rename(columns={'Ind':'Ind_orig'},inplace=True)
                self.coordDebug['dfNewFixed'] = dfNew


            # Display comparison table
            if self.__notebook__ and self.verbose:
                display(dfNew)

            # Set new, consistent, table
            print("*** Setting coords from '_new' columns.")

            dfNewFinal = dfNew[['Ind_orig','Species','Atomic Num.','x_new','y_new','z_new']]
            # dfNew2.rename(columns = ['Ind','Species','Atomic Num.','x','y','z'])
            dfNewFinal.set_axis(['Ind','Species','Atomic Num.','x','y','z'], axis=1, inplace=True)
        
        # FORCE case - just use new table as passed
        else:
            dfNewFinal = newTable

        # Push new table to self.setCoords() to update RDkit molecule
        geomTemp = dfNewFinal.to_dict()
        positionsDict = {k:[geomTemp['x'][k], geomTemp['y'][k], geomTemp['z'][k]] for k in geomTemp['Ind'].keys()}
        self._setCoordsDict(coordList = positionsDict, printTable = printTable)

        
    def _setCoordsDict(self, coordList = None, printTable = True):
        """
        Basic wrapper for RDkit conformer.SetAtomPosition() to update coord table.

        Pass dictionary with items giving atom index and [x,y,z] position to set.
        E.g. coordList = {1:[0,0,0]}

        TODO:
        - Add passing as a table or array for brevity, e.g. input list or np.array in format [[atom ID, X, Y, Z], ...]
        - Coord table parsing & conversion from file or Gamess outputs (see pyGamess)
        
        28/11/23: now wrapped by self.setCoords, use this also for Pandas DataFrame case which includes atom label checks.

        """

        # Quick attempt: this requires a bit of thought, since types get rejected for numpy, and passing 1D or 2D lists is a bit of a pain.
        # Use dict for now, since the structure is at least clear.
        # if isinstance(coordList, list):
        #     coordList = np.array(coordList,ndmin=2)  # For to 2D array.
        #
        # conf = self.mol.GetConformer()
        #
        # if coordList is not None:
        #     for row in coordList:
        #         conf.SetAtomPosition(row[0], row[1:])

        # Dict version
        conf = self.mol.GetConformer()

        if coordList is not None:
            for k, coords in coordList.items():
                conf.SetAtomPosition(k, coords)

        if self.verbose and printTable:
            print("*** Set atom positions, new coord table:")
            self.printTable()


    def setAxis(self, axis = {'x':0.0}):
        """
        Basic wrapper for RDkit conformer.SetAtomPosition() to update coord table for a given AXIS.


        TODO:
        - integrate with setCoords() as general function.
        - More flexible input format? Currently OK for an axis or two.

        """

        conf = self.mol.GetConformer(0)

        if axis is not None:
            for atom in self.mol.GetAtoms():
                pos = conf.GetAtomPosition(atom.GetIdx())

                for k, v in axis.items():
                    setattr(pos, k, v)  # Dictionary style, set attribute by named axis to specified value.

                conf.SetAtomPosition(atom.GetIdx(), pos)  # Update molecule with new value.

            if self.verbose:
                print("*** Set atom positions, new coord table:")
                self.printTable()

        else:
            pass


    def setBondLength(self, bonds = None):
        """
        Basic wrapper for AllChem.SetBondLength

        Pass dictionary with items giving atom1, atom2 and the bond length to set.
        E.g. bonds = {'CCBond':{'a1':0, 'a2':1, 'l':10}}

        TODO: Add passing as a table or array for brevity, format [a1, a2, l; ....]

        """

        if bonds is not None:
            for k, bond in bonds.items():
                AllChem.SetBondLength(self.mol.GetConformer(),bond['a1'],bond['a2'],bond['l'])

        if self.verbose:
            print("*** Set bonds, new coord table:")
            self.printTable()


    def rotateFrame(self, rotations = {'y':np.pi/2}, canonicalise=True, 
                    roundCoords = True, decimals = None):
        """
        Rotate molecule to reference frame, using rotation matricies + AllChem.TransformConformer() functionality.

        CODE ADAPTED FROM `Github user iwatobipen's example notebook <https://nbviewer.jupyter.org/github/iwatobipen/playground/blob/master/rotation_mol.ipynb>`__
        Thanks to `iwatobipen <https://github.com/iwatobipen>`__ and the `RDkit list <https://sourceforge.net/p/rdkit/mailman/message/36598250/>`__


        Parameters
        ----------
        rotations : dict, default = {'y':np.pi/2}
            Supply rotations as a dict, with rotations about labelled axes.
            Rotations will be applied sequentially.
            E.g. {'x':np.pi/2, 'y':np.pi/2} will rotate by pi/2 about x-axis then pi/2 about (new) y-axis.

        canonicalise : bool, default = True
            Canonicalise before transform?
            This runs :py:func:`rdkit.Chem.rdMolTransforms.CanonicalizeConformer` (see `RDkit docs <https://rdkit.org/docs/source/rdkit.Chem.rdMolTransforms.html#rdkit.Chem.rdMolTransforms.CanonicalizeConformer>`__.)

        All transforms are applied to self.mol.
        
        roundCoords : bool, optional, default = True
            If True, run `self.roundCoords()` on new frame to tidy up.
            This uses `self.precision` to define rounding, or pass an integer to `decimals` to override.
            
        decimals : int, optional, default = None
            If roundCoords is True, use this value for rounding precision instead of `self.precision`.
            If None, use `self.precision`.

        Notes
        -----
        Default case sets then rotates "canonical" form by pi/2 about y

        - Canoncial form sets x-axis as highest sym axis, see https://rdkit.org/docs/source/rdkit.Chem.rdMolTransforms.html#module-rdkit.Chem.rdMolTransforms
        - Then rotate x > z axis, to match Gamess/comp chem conventions.

        """

        # Canonicalise? This sets x-axis as highest sym axis, see https://rdkit.org/docs/source/rdkit.Chem.rdMolTransforms.html#module-rdkit.Chem.rdMolTransforms
        if canonicalise:
            AllChem.CanonicalizeConformer(self.mol.GetConformer())

        # Define rotations
        def rot_ar_x(radi):
            return  np.array([[1, 0, 0, 0],
                              [0, np.cos(radi), -np.sin(radi), 0],
                              [0, np.sin(radi), np.cos(radi), 0],
                             [0, 0, 0, 1]], dtype=np.double)

        def rot_ar_y(radi):
            return  np.array([[np.cos(radi), 0, np.sin(radi), 0],
                              [0, 1, 0, 0],
                              [-np.sin(radi), 0, np.cos(radi), 0],
                             [0, 0, 0, 1]], dtype=np.double)

        def rot_ar_z(radi):
            return  np.array([[np.cos(radi), -np.sin(radi), 0, 0],
                              [np.sin(radi), np.cos(radi), 0, 0],
                              [0, 0, 1, 0],
                             [0, 0, 0, 1]], dtype=np.double)
        # tforms = {0: rot_ar_x, 1: rot_ar_y, 2: rot_ar_z}
        tforms = {'x': rot_ar_x, 'y': rot_ar_y, 'z': rot_ar_z}

        # Loop over defined rotations
        for k,v in rotations.items():
            AllChem.TransformConformer(self.mol.GetConformer(), tforms[k](v))

        # Tidy-up
        self.setTable()
        if roundCoords is True:
            if decimals is None:
                decimals = self.precision
                
            # Round coords & update coords without checks or printing
            self.roundCoords(decimals = decimals, updateCoords = True, 
                             force = True, printTable = False, useRef = False)
            
        if self.verbose:
            print("*** Set frame rotations, new coord table:")
            self.printTable()

            
            
#*** Molecule info routines

    def getAtoms(self, conf = None):
        """
        Generate list of atoms from RDkit molecule.
        Format [atom.GetIdx(), atom.GetSymbol(), atom.GetAtomicNum(), pos.x, pos.y, pos.z]
        And set to self.atomsDict.
        (NOTE: self.atomList currently reserved for Gamess input format, and just lists atoms to use for Gamess calc - see gamessInput.atom_section().)

        """

        if conf is None:
            conf = self.mol.GetConformer(0)

        atomList = []
        coordDict = {}  # Also set dict format for use with setCoords
        for atom in self.mol.GetAtoms():
            pos = conf.GetAtomPosition(atom.GetIdx())

            atomList.append([atom.GetIdx(), atom.GetSymbol(), atom.GetAtomicNum(), pos.x, pos.y, pos.z])
            coordDict[atom.GetIdx()] = {'x':pos.x, 'y':pos.y, 'z':pos.z}

        # Dict form - currently will break Gamess func definitions!
        # self.atomList = {'table':atomList,
        #                  'items':['Ind','Species','Atomic Num.','x','y','z']}
        # self.atomList = atomList

        # Update current & history
        currDict = self.atomsDict.copy()
        self.atomsDict = {'table':atomList,
                         'items':['Ind','Species','Atomic Num.','x','y','z'],
                         'coordDict':coordDict}

        if currDict != self.atomsDict:
            self.updateAtomsHist(currDict)


    def updateAtomsHist(self, atomDict):
        """Log atomDict history"""

        # Check last item - assumes unordered dict with int sequence keys
        currInd = -1
        if self.atomsHist:
            # np.array([k for k,v in dataIn.items() if isinstance(k,int)]).max()  # Allows for non-int cases
            currInd = np.array(list(self.atomsHist.keys())).max()

        # Ignore cases where blank dict is passed
        if atomDict:
            self.atomsHist[currInd+1] = atomDict.copy()


    def setRef(self, atomDict = None, refKey = None, histKey = None):
        """
        Set reference coords (as atom dictionary)

        Either:

        - Pass nothing to use self.atomsDict
        - Pass atomDict directly to set directly.
        - Pass histKey to use item from self.atomsHist.

        """

        if refKey is None:
            refKey = 'ref'

        note = f"Set reference coords key '{refKey}' from passed dict."

        if atomDict is None:
            atomDict = self.atomsDict.copy()
            note = f"Set reference coords key '{refKey}' from self.atomsDict."

        if histKey is not None:
            atomDict = self.atomsHist[histKey]
            note = f"Set reference coords key '{refKey}' from self.atomsHist['{histKey}']"

        self.refDict[refKey] = atomDict
        
        self.printTable(refKey = refKey)  # Set and display Pandas version.

        if self.verbose:
            print(note)


    def setTable(self, atomsDict = None, refKey = None, returnTable = False):
        """
        Set PD table from atomsDict.
        
        If atomsDict = None, set using self.getAtoms()
        
        12/12/23 - extended for ref case and optional return.
        May duplicate code elsewhere now.
        """
    
        if atomsDict is None:
            if refKey is None:
                self.getAtoms()
                atomsDict = self.atomsDict
            else:
                atomsDict = self.refDict[refKey]
    
        pdTable = pd.DataFrame(atomsDict['table'], columns=atomsDict['items'])
        
        if returnTable:
            return pdTable
        else:
            if refKey is None:
                self.pdTable = pdTable
            else:
                self.refDict[refKey]['pd'] = pdTable
    
            
    def printTable(self, refKey = None):
        """
        Show pretty table using Pandas (use printCoords() for simple version), and also set to `self.pdTable`.

        Code is very similar to printCoords(), based on pyGamess routines (atom_section, https://github.com/kzfm/pygamess/blob/master/pygamess/gamess.py)

        TODO: amalgamate these!
        
        If refKey is passed, use `self.refDict[refKey]` instead of `self.getAtoms()` for structure, and output to `self.refDict[refKey]['pd']`
        
        NOTE: if self.verbose=0 table will be set but not displayed.
        
        """

        # conf = self.mol.GetConformer(0)
        # atomList = []
        # for atom in self.mol.GetAtoms():
        #     pos = conf.GetAtomPosition(atom.GetIdx())
        #
        #     atomList.append([atom.GetIdx(), atom.GetSymbol(), atom.GetAtomicNum(), pos.x, pos.y, pos.z])
#         self.getAtoms()

        # TODO: change to check pd is loaded instead of try/except - miss other errors here.
#         try:
#             # self.pdTable = pd.DataFrame(atomList, columns=['Ind','Species','Atomic Num.','x','y','z'])
#             # self.pdTable = pd.DataFrame(self.atomDict['table'], columns=self.atomDict['items'])
#             self.pdTable = pd.DataFrame(self.atomsDict['table'], columns=self.atomsDict['items'])  # Nov 2023 debugged, now "atomsDict"

#             if self.__notebook__:
#                 display(self.pdTable)

#         except AttributeError or NameError:
#             self.printCoords()  # Fallback if Pandas is not available.
            
        # 27/11/23 - quick mod to allow use of refKey
        if refKey is None:
            self.getAtoms()
            atomsDict = self.atomsDict
        else:
            atomsDict = self.refDict[refKey]
    
        
        # 20/11/23 - if/else version instead of try/except above.
        # Note pdFlag now set at module load.
        if pdFlag:
#             pdTable = pd.DataFrame(atomsDict['table'], columns=atomsDict['items'])  # Nov 2023 debugged, now "atomsDict"
            pdTable = self.setTable(atomsDict, returnTable=True)

            if self.__notebook__ and self.verbose:
                display(pdTable)
                
            if refKey is None:
                self.pdTable = pdTable
            else:
                self.refDict[refKey]['pd'] = pdTable
                
        else:
            self.printCoords()  # Fallback if Pandas is not available.
            


    def printCoords(self):
        """
        Get coords, as per pyGamess routines (atom_section, https://github.com/kzfm/pygamess/blob/master/pygamess/gamess.py)

        NOTE: currently assumes that mol.GetConformer(0) is all that is required.

        """

        conf = self.mol.GetConformer(0)
        section = ""
        for atom in self.mol.GetAtoms():
            pos = conf.GetAtomPosition(atom.GetIdx())
        #     print(pos)
            section += "{:<3} {:>4}.0   {:> 15.10f} {:> 15.10f} {: 15.10f} \n".format(atom.GetSymbol(), atom.GetAtomicNum(), pos.x, pos.y, pos.z)

        print(section)


#*** Additional conversion routines

    def genXYZ(self, refKey=None, printXYZ = True):
        """
        Generate XYZ string representation from self.pdTable or self.refDict[refKey]['pd'] if refKey!=None
        
        Results are printed if self.verbose and printXYZ (default=True)
        
        TODO: add some error checking etc. here, very basic.
        
        """
        
        # Generate XYZ representation from self.pdTable or ref table.
        if refKey is None:
            pdMol = self.pdTable
        else:
            pdMol = self.refDict[refKey]['pd']
            
        xyzStr = pdMol.to_string(columns=['Species','x','y','z'], index=False, header=False)
        xyzStr = f"{pdMol.shape[0]}\n\n" + xyzStr

        if refKey is None:
            self.xyzStr = xyzStr
        else:
            self.refDict[refKey]['xyzStr'] = xyzStr
        
        if self.verbose and printXYZ:
            print("Generated XYZ string repr:\n")
            print(xyzStr)
            print(f"\nData set to {'self.xyzStr' if refKey is None else f'self.refDict[{refKey}]'}")
        

    def setPDfromGamess(self, refKey = None, newCoords = None, 
                        updateMol = True, printXYZ = False):
        """
        Generate Pandas table from Gamess coord output.
        
        Parameters
        ----------
        refKey : str, default = None
            Key for self.refDict, use for object storage if set, otherwise use defaults.
            
        newCoods : str or None, default = None
            Pass newCoords as a string set from a Gamess output file.
            Use self.mol.newCoords[0][-1] if None.
            
            Format is rows with 
            'ATOM   CHARGE       X              Y              Z'
            E.g. :
            `' O           8.0   0.0000000000  -0.0000000054  -1.2374766478\n O           8.0  -0.0000000000  -0.0000000054   1.2374766478\n C           6.0   0.0000000000   0.0000000108  -0.0000000130'`
            
            This is parsed using pd.read_csv(), so exact column spacing doesn't matter.
  
        updateMol: bool, default = True
            Push updated mol object to self.mol if true (uses self.molFromXYZ()).
            Otherwise new coords are only set to self.pdTable or self.refDict[refKey]['pd']
        

        """
        
        # Use string IO for pd.read_csv
        output = io.StringIO(self.mol.newCoords[0][-1])
        # pd.read_fwf(output,widths = [2,7,7,20,20,20], header=None)
        readCSVtable = pd.read_csv(output, header=None, names = ['Species','Atomic Num.','x','y','z'], delim_whitespace=True)    #delimiter = '\t')
        readCSVtable['Atomic Num.'] = readCSVtable['Atomic Num.'].astype('int64')  # Fix float > int.
        readCSVtable.insert(0, 'Ind', readCSVtable.index)  # Add index column
        
        # Round coords and fix -ve 0 issues
        newCoords = self.roundCoords(pdTable = readCSVtable,  decimals = 4, updateCoords = False)
        
        if refKey is None:
            self.pdTable = newCoords
        else:
            if refKey in self.refDict.keys():
                self.refDict[refKey]['pd'] = newCoords
            else:
                self.refDict[refKey] = {'pd':newCoords,
                                        'str':output}
        
        # Update main system/mol object?
        # If so, generate XYZ representation then overwrite.
        # This should be robust even if atom ordering changes.
        # (Which is not the case for setCoords() )
        if updateMol:
            if self.verbose:
                print(f"Updating with new coords, output set to {'self.mol' if refKey is None else f'self.refDict[{refKey}]'}")
                      
            self.genXYZ(refKey=refKey, printXYZ = printXYZ)
            
            # TODO: set molFromXYZ() to accept key, currently have to bypass here
            if refKey is not None:
                self.refDict[refKey]['previousMol'] = deepcopy(self.mol)  # Backup existing mol object for reference
                self.xyz = self.refDict[refKey]['xyzStr']
                
            else:
                self.previousMol = deepcopy(self.mol)  # Backup existing mol object for reference
                self.xyz = self.xyzStr
                
            self.molFromXYZ()
            self.printTable()
            
 
    def roundCoords(self, pdTable = None, decimals = 4, updateCoords = False, **kwargs):
        """
        Round PD table of coords to specified d.p. and tidy up (-0.00 cases).
        
        Pass pdTable, or None to use self.pdTable.
        Pass updateCoods = True to run self.setCoords(coords = newCoords,**kwargs)
        """

        # Round coords
        if pdTable is None:
            newCoords = self.pdTable.round(decimals = decimals)
        else:
            newCoords = pdTable.round(decimals = decimals)

        # Fix -0.0 within tolerance
        newCoords[['x','y','z']] = newCoords[['x','y','z']].where(newCoords[['x','y','z']].abs() > 1e1**(-1*decimals), 0.0)

        if updateCoords:
            # Update main coord set
            self.setCoords(coords = newCoords,**kwargs)
            
        else:
            return newCoords

        
#***** GAMESS SETUP ROUTINES

        
    def initGamess(self, gamess_path = '/opt/gamess', **kwargs):
        """
        Init Gamess object & build (default) input card.

        All kwargs are passed to pyGamess init.

        This minimally requires `gamess_path`, which defaults to '/opt/gamess'

        """

        # Init pyGames object
        self.g = gamessInput(job = self.job, sym = self.sym, gamess_path = gamess_path, **kwargs)

        # Set pointer to options
        self.params = self.g.options

        # Set for molOverride too...
        self.g.molOverride = self.molOverride

        print("*** Init pyGamess job.")

        # Show current Gamess input
        print("Default Gamess input card set (use self.params to modify options dictionary, self.setGamess() to test):\n")
        print(self.g.input(self.mol))

        # self.gCard = {}
        # self.gCard['default'] = self.g.input(self.mol)
        #
        # print("*** Gamess input card set to self.gCard['default']")
        # print(self.gCard['default'])
        
        #***** Check Gamess executable exists - note this does not set anything currently, just reproduces pyGamess check.
        # Method as used in pygamess.py_rungms
        # See https://github.com/kzfm/pygamess/blob/d6c14da805945c5a6c1175900699f77fd20eee96/pygamess/gamess.py#L420
        gamesses = [f for f in os.listdir(gamess_path) if f.startswith('gamess') and f.endswith('.x')]
        if len(gamesses) < 1:
#             raise IOError("gamess.*.x not found")
            print(f"*** Executable gamess.*.x not found on path {gamess_path}. Gamess runs from Python not available.")
    
        else:
            gamess = os.path.join(gamess_path, gamesses[0])
            print(f"*** Found Gamess executable: {gamess}")
            
        # Set Gamess help script here too?
        # Found at /opt/gamess/tools/gmshelp
        # And just parses /opt/gamess/INPUT.DOC
        # So maybe just write python equivalent?
        


    def setGamess(self, job = None, note = None, sym = None, atomList = None):
        """
        Set up a new Gamess input card.

        Parameters
        ----------
        job : str, default = None
            Name for input card, defaults to self.name

        note : str, default = None
            Note to push to input card, defaults to `job, basis`

        sym : str, default = 'C1'
            Set symmetry for job.

        """

        if job is None:
            # job = f'{self.name}, {self.g.options['basis']['gbasis']}'
            job = self.name

        if note is None:
            note = f"{job}, {self.g.options['basis']['gbasis']}"

        if sym is None:
            sym = self.sym   # Force sym here to, so that setExtras(overwriteFlag = True) always works. Ugh - NEED BETTER LOGIC HERE.

        if atomList is None:
            atomList = self.atomList  # And again.

        # Set all inputs - THIS MIGHT work, but relies on knowing pyGamess input structure - may be better to wrap key params instead?
        # self.g.setAttributesFromDict(**kwargs, overwriteFlag = True)

        # self.gCard[job] = self.g.input(self.mol, job = note, sym = sym)
        #
        # print(f"*** Gamess input card set to self.gCard['{job}']")
        # print(self.gCard[job])

        # Set extras
        self.g.setExtras(note, sym, atomList, overwriteFlag = True)

        if self.verbose:
            self.printGamessInput()


    def printGamessInput(self):
        """Show current Gamess input card."""
        # print("*** Set Gamess job, use self.params to modify options.\n")
        print("*** Gamess input card:")
        print(self.g.input(self.mol))  #, job = note, sym = sym))

    # def runOpt(self, fileOut = None):
    #     """Run Gamess optimization with pyGamess"""
    #
    #     self.g.run_type('optimize')
    #     self.mol = self.g.run(self.mol)
    #
    #     print("*** Optimized self.mol")
    #     print(self.mol.GetProp("total_energy"))
    #     self.printTable()
    #
    #
    # def runE(self, fileOut = None):
    #     """Energy only run with pyGamess"""
    #
    #     self.g.run_type('energy')
    #     self.mol = self.g.run(self.mol)
    #
    #     print(self.mol.GetProp("total_energy"))



#***** PYGAMESS ADDITIONAL CONFIG WRAPPERS

    def listBasis(self):
        """
        List PyGamess supported basis sets.
        
        Reproducted from PyGamess, 23/11/23 (this list may change)
        See pygamess config at https://github.com/kzfm/pygamess/blob/d6c14da805945c5a6c1175900699f77fd20eee96/pygamess/gamess.py#L291
        See the Gamess manual for more options, https://www.msg.chem.iastate.edu/gamess/GAMESS_Manual/docs-input.txt.
        
        """
        
        basisDict = {}
        
        for basis_type in ["STO3G", "STO-3G"]:
            basisDict[basis_type] = {'gbasis': 'sto', 'ngauss': '3'}
        
        for basis_type in ["321G", "3-21G"]:
            basisDict[basis_type] = {'gbasis': 'N21', 'ngauss': '3'}
            
        for basis_type in ["631G", "6-31G"]:
            basisDict[basis_type] = {'gbasis': 'N31', 'ngauss': '6'}
        
        for basis_type in ["6311G", "6-311G"]:
            basisDict[basis_type] = {'gbasis': 'N311', 'ngauss': '6'}
            
        for basis_type in ["631G*", "6-31G*", "6-31G(D)", "631G(D)"]:
            basisDict[basis_type] = {'gbasis': 'N31', 'ngauss': '6', 'ndfunc': '1'}
            
        for basis_type in ["631G**", "6-31G**", "631GDP", "6-31G(D,P)", "631G(D,P)"]:
            basisDict[basis_type] = {'gbasis': 'N31', 'ngauss': '6', 'ndfunc': '1', 'npfunc': '1'}
            
        for basis_type in ["631+G**", "6-31+G**", "631+GDP", "6-31+G(D,P)", "631+G(D,P)"]:
            basisDict[basis_type] = {'gbasis': 'n31', 'ngauss': '6', 'ndfunc': '1', 'npfunc': '1', 'diffsp': '.true.', }
            
        for basis_type in ["AM1"]:
            basisDict[basis_type] = {'gbasis': 'am1'}
            
        for basis_type in ["PM3"]:
            basisDict[basis_type] = {'gbasis': 'pm3'}
            
        for basis_type in ["MNDO"]:
            basisDict[basis_type] = {'gbasis': 'mndo'}
            
        basisDict['note']="PyGamess supported basis sets as of Nov. 2023, see pygamess config at https://github.com/kzfm/pygamess/blob/d6c14da805945c5a6c1175900699f77fd20eee96/pygamess/gamess.py#L291 for updates. See the Gamess manual for more options, https://www.msg.chem.iastate.edu/gamess/GAMESS_Manual/docs-input.txt."
        
        basisDict['basisList'] = list(basisDict.keys())
        
        self.basisDict = basisDict
        
        
    def basis(self):
        """List pyGamess supported basis sets."""
        print('PyGamess supported basis sets:')
        print(self.basisDict['basisList'])
        

    def setBasis(self, basis):
        """ 
        Thin wrapper for self.g.basis_set 
        
        Parameters
        ----------
        
        basis : string definition of basis set.
            For pygamess supported config, see self.basis().
            For unsupported basis sets, set manually using self.setParam()
        
        """
        

        
        # For basis, logger.ERROR gives message if basis not available.
        # Grab log and handle if necessary here
        # NOTE this isn't caught with try/except, since it doesn't raise an error.
        
        # Logger code adapted from https://stackoverflow.com/questions/59345532/error-log-count-and-error-log-messages-as-list-from-logger
        # CustomStreamHandler set in ._util.py
        handler = CustomStreamHandler()
        pygLog = logging.getLogger('pygamess.gamess')
        pygLog.addHandler(handler)
        
#         try:
#             self.g.basis_set(basis)
            
#         except:
            
        self.g.basis_set(basis)
        
        if handler.error_logs and handler.error_logs[-1].message == 'basis type not found':
            print(f"*** Basis configuration {basis} not supported by PyGamess.")
            print(f"To set manually, pass Gamess basis params as a dictionary to self.setParam().")
            print("E.g. for 'ACCD' configure with self.setParam(inputGroup='basis',inputDict={'gbasis':'ACCD'}), \
                  \nAny other required params can also be set, e.g. self.setParam(inputGroup='contrl',inputDict={'ISPHER':'1'}).")
            print("See the Gamess manual for settings, https://www.msg.chem.iastate.edu/gamess/GAMESS_Manual/docs-input.txt.")
            
        else:
            print(f"Set basis to specification {basis}.")
            print(f"self.params['basis']: {self.params['basis']}")
        
        
    def setParam(self, inputGroup='contrl', inputDict={}, resetGroup=False):
        """ 
        Set Gamess input card options from dictionary of items.
        
        Options are set as 
        - For a new group, `self.param[inputGroup] = inputDict`
        - For an existing group, `self.param[inputGroup].update(inputDict)` unless `resetGroup=True` is passed/
        
        For Gamess options, see the manual https://www.msg.chem.iastate.edu/gamess/GAMESS_Manual/input.pdf
        or https://www.msg.chem.iastate.edu/gamess/GAMESS_Manual/docs-input.txt
        
        Parameters
        ----------
        
        inputGroup : str, default='contrl'
            Gamess input group to write to.
            
        inputDict : dictionary, default = {}
            Configuration settings dictionary.
            Note all options are keyword:value pairs.
            
        resetGroup : bool, default = False
            If True, overwrite any existing entries for the group.
            If False, add new entries to any existing entries for the group.
        
        """
        
        if inputGroup in self.params.keys():
            if not resetGroup:
                print(f"Updating existing group '{inputGroup}'. (To replace group, pass 'resetGroup=True')")
                self.params[inputGroup].update(inputDict)
            else:
                print(f"Replacing existing group '{inputGroup}'.")
                self.params[inputGroup]=inputDict
                
            
        else:
            print(f"Setting new group '{inputGroup}'.")
            self.params[inputGroup] = inputDict
            
        print(f"Updated group '{inputGroup}': {self.params[inputGroup]}")
            

    
#***** GAMESS RUNNERS & OUTPUTS

    # def runGamess(self, job = 'Default', sym = 'C1', **kwargs):
    def runGamess(self, fileOut = None, runType = 'energy', **kwargs):
        """ Wrapper for pyGamess.run(), using self.mol and additional input options. """

        # # Additional vars for Gamess job - set using self.setGamess()
        # self.setAttribute('job', job)
        # self.setAttribute('sym', sym)
        # self.setGamess(**kwargs)

        # TODO: write decorator for this! For now just call runGamess as main function.
        # def setGamessFiles(self, fileOut = None):
        #     """Copy temp Gamess output file to specified location"""
        #

        # Set job type & update input
        self.g.run_type(runType)
#         self.g.input(self.mol)
        
        if fileOut is not None:
            self.g.debug = True

        # Run
        self.mol = self.g.run(self.mol, **kwargs)

        try:
            self.E = self.mol.GetProp('total_energy')

# 30/11/23: added additional warnings info, now moved to parse_gamout() method
#             try:
#                 warnings = self.mol.GetProp('Warnings')
#                 print(f"*** Gamess {runType} completed with warnings.")
                
#             except KeyError:
#                 print(f"*** Gamess {runType} completed OK.")

            
#             warnings = self.mol.GetProp('Warnings')
        
#             if warnings:
#                 print(f"*** Gamess {runType} completed with warnings.")
                
#             else:
#                 print(f"*** Gamess {runType} completed OK.")
                

            if self.verbose > 0:
                print(f"E = {self.E}")

            if self.verbose > 1:
                if runType == 'optimize':
                    self.printTable()

        except KeyError:
            self.E = None
            print("*** Warning: result does not include 'total_energy', this likely indicates Gamess run failed.")
            
        # 08/12/23 - fixing issues if atom ordering has changed.
        # In default g.parse_gamout this is set as (https://github.com/kzfm/pygamess/blob/d6c14da805945c5a6c1175900699f77fd20eee96/pygamess/gamess.py#L177C1-L178C41):
        #
        #         for i, cds in enumerate(result.coordinates):
        #             conf.SetAtomPosition(i, cds)
        #
        # THIS FAILS IF atom ordering has changed in Gamess output - this can happen in symmetrized (and other?) cases.
        #
        
        # Check for optimized runs only?
        if runType == 'optimize':
#             newCoords = io.StringIO(testDL.mol.newCoords[0][-1])  # Get final coords passed from modified parse_gamout() routine
#             self.xyz = self.mol.newCoords[0][-1]  # Using this directly fails, format is not correct
#             self.molFromXYZ()

            print("*** Gamess optimization run - reseting self.mol with updated coords.")
            print("Note that atom ordering may change depending on Gamess output.")

            # Properties to propagate...
            prop = ['errorDict','newCoords']
        
            # Set via method.
            # NOTE - this resets self.mol from self.mol.newCoords[0][-1]
            # TODO: more logging/put these coords elsewhere for ref.
            self.setPDfromGamess()
    
            # Propagate attrs for debug
            for attr in prop:
                setattr(self.mol, attr, getattr(self.previousMol, attr))
                
            # Propagate errors - this just duplicates code in parse_gamout() wrapper below.
            for k,item in self.mol.errorDict.items():
                self.mol.SetProp(k, item['matches'])
                    
    
            # Push self.E back to new mol object.
            if self.E is not None:
                self.mol.SetProp('total_energy',self.E)
            

        # Tidy up
        if fileOut is not None:
            Path(self.g.gamout).rename(fileOut)  # Rename output
            Path(self.g.gamin).unlink()          # Tidy input
            self.gout = fileOut
            print(f"*** Gamess output file moved to {fileOut}")
            
        else:
            # Just set tmp file name for consistency, although will be empty in this case.
            self.gout = self.g.gamout


    def printGamess(self):
        """Print full Gamess output."""

        try:
            with open(self.gout, 'r') as f:
                print(f.read())

        except FileNotFoundError as err:
            print(f"Error: Missing file {self.gout}")


    def buildES(self, fileOut = None):
        """Basic job automation to build electronic structure with defaults."""

        print("*** Running default Gamess job.")

        self.rotateFrame()

        # Init the pyGamess job.
        # This minimally needs a gamess_path set, which defaults to '/opt/gamess'
        self.initGamess() # Using defaults

        self.runGamess(fileOut)

        self.printTable()



# Set basic decorator for file handling
# TODO


# Try subclassing pyGamess routine for extra control over input...
class gamessInput(Gamess):
    """
    Build on `pygamess <https://github.com/kzfm/pygamess>`_ Gamess class to modify input card writing functionlity

    TODO: better error checking (if not already in pygamess...?)

    E.g. parse ddkick outputs at end of Gamess output file:
        ddikick.x: application process 0 quit unexpectedly.
        ddikick.x: Sending kill signal to DDI processes.
        ddikick.x: Execution terminated due to error(s).

    """

    from epsman._util import setAttribute, setAttributesFromDict

    def __init__(self, job = None, sym = None, atomList = None, **kwargs):

        super().__init__(**kwargs)
        # self.debug = True  # Set this to keep files
        self.verbose = None

        self.setExtras(job, sym, atomList)

    def input(self, mol):   #, job = None, sym = None, overwriteFlag = False):
        """Extend pyGamess.gamess.input() writer for additional parameters"""

        # self.setExtras(job,sym, overwriteFlag)
        # Note, for sym != C1 need an extra line break, as set here.
        sym = self.sym
        if sym not in ['C1', None]:
            sym = sym + '\n'

        return "{0} $DATA\n{1}\n{2}\n{3} $END\n".format(self.print_header(),
                                                        self.job, sym,
                                                        self.atom_section(mol))


    def atom_section(self, mol):   #, atomList = None):
        """
        Extend pyGames.gamess.atom_section() for symmetrized cases.

        Pass list of atom indicies to sub-select, default to all atoms (as per original version).

        TODO: better routine here, this is fully manual.
        May want to try pymatgen/spglib combo: https://pymatgen.org/pymatgen.symmetry.analyzer.html

        14/06/21: added quick hack for manual structure override. Handy for problematic cases.

        """

        # Default to all atoms
        atomList = self.atomList
        if atomList is None:
            atomList = list(range(0, mol.GetNumAtoms()))

        section = ""  # Set stub for writing

        # Allow manual override for RDkit mol object - handy for custom coord cases
        # This assumes self.molOverride is set as a dictionary of atoms, e.g. {0:{'name':'H', 'Z': 1, 'coords':[0.0, 0.0, 1.0]}, 1:{'name':'C', 'Z': 16, 'coords':[0.0, 0.0, 4.0]}}
        if self.molOverride is not None:
            for N, atom in self.molOverride.items():
                if N in atomList:
                    section += "{:<3} {:>4}.0   {:> 15.10f} {:> 15.10f} {: 15.10f} \n".format(atom['name'], atom['Z'], *atom['coords'])


        else:
            # self.contrl['icharg'] = mol.GetFormalCharge()
            conf = mol.GetConformer(0)
            for atom in mol.GetAtoms():
                N = atom.GetIdx()
                pos = conf.GetAtomPosition(N)

                if N in atomList:
                    section += "{:<3} {:>4}.0   {:> 15.10f} {:> 15.10f} {: 15.10f} \n".format(atom.GetSymbol(), atom.GetAtomicNum(), pos.x, pos.y, pos.z)

        return section


    def setExtras(self, job, sym, atomList, overwriteFlag = False):
        """
        Quick hack for setting extra attribs & also pushing to self.options

        Should use _util function from dict here?
        """

        # Additional vars for Gamess job - may want to push to self.options?
        self.setAttribute('job', job, overwriteFlag)
        self.setAttribute('sym', sym, overwriteFlag)
        self.setAttribute('atomList', atomList, overwriteFlag)
        self.options['extra'] = {'job':self.job, 'sym':self.sym, 'atomList':self.atomList}


    # TODO: overwrite print_header (below) for arb sections?
    # def print_header(self):
    #     """ gamess header"""
    #     header = "{}{}{}".format(self.print_section('contrl'),
    #                              self.print_section('basis'),
    #                              self.print_section('system'))
    #     if self.options['contrl']['runtyp'] == 'optimize':
    #         header += self.print_section('statpt')
    #
    #     if self.options['contrl'].get('citype', None) == 'cis':
    #         header += self.print_section('cis')
    #
    #     return header

    
    
    def parse_gamout(self, gamout, mol):
        """
        Add some additional error-checking to lib routine.
        
        Note this was written for pyGamess v0.5.0 (circa 2020).
        parse_gamout() in v0.6.9 (Nov. 2023) has some additional stuff already.
        
        See https://github.com/kzfm/pygamess/blob/d6c14da805945c5a6c1175900699f77fd20eee96/pygamess/gamess.py#L150
        See also low-level function https://github.com/kzfm/pygamess/blob/master/pygamess/gamout_parser.py
        
        """
        # Run lib parser
        mol = super().parse_gamout(gamout, mol)
        
        # Additional checks
        # Use Re as per parse_gamout(), but some additions and run with findall()
        errorDict = {}
        errorDict['Warnings'] = {'re':re.compile('.*WARNING: .*')}
        errorDict['ddikick'] = {'re':re.compile('.*ddikick.x: .*')}  # Execution terminated due to error(s).*')
        
        # TODO: check and exclude "ddikick.x: exited gracefully." from issues below, but should report?
        
        # Search re
        with open(gamout, "r") as fileIn:
            out_str = fileIn.read()
            
            
            # Check coords - for symmetrized case the ordering may change
            # This follows method in https://github.com/kzfm/pygamess/blob/master/pygamess/gamout_parser.py
            # BUT pass back to main class for coord check and set
            coord_re = re.compile('COORDINATES OF ALL ATOMS ARE (.*?)------------\n(.*?)\n\n', re.DOTALL)
            newCoords = coord_re.findall(out_str)
            mol.newCoords = newCoords
            
            
            # Iterate over warnings
            warnFlag = 0
            for k,item in errorDict.items():
                matches = item['re'].findall(out_str)
                
                if matches:
                    # Set as mol property? This follows current parse_gamout style
                    # mol.SetProp(k, matches)
                    mol.SetProp(k, '\n'.join(matches))

                    if k != 'ddikick':
                        print(f"*** Warning: found errors in Gamess output, type: {k}")
                        warnFlag = 1

                    if k == 'ddikick':
                        if len(matches) == 1:
                            print(f"*** ddikick exit status OK: {matches[0]}")
                        else:
                            print(f"*** Warning: found errors in Gamess output, type: {k}")
                            warnFlag = 1


                    if self.verbose:
                        print(mol.GetProp(k))
                    else:
                        # Check warnFlag to skip case for single ddikick normal exit message.
                        if warnFlag:
                            print(f"*** Check self.mol.GetProp('{k}') for details.")
                
                    # Also set errorDict
                    errorDict[k]['matches'] = '\n'.join(matches)
                    errorDict[k]['warnFlag'] = warnFlag
                
                else:
                    # Set empty if not present, this avoids errors rolling in from previous calculations.
                    mol.SetProp(k,'') 
                    
                    # Also set errorDict
                    errorDict[k]['matches'] = ''
                    errorDict[k]['warnFlag'] = 0

#                     # Raise further? This is in main parse_gamout, but not for these types of error
#     #                 if len(err_message) > 0:
#     #                     raise GamessError(err_message)
#     #                 else:
#     #                     return nmol
                
                    
        if warnFlag:
            print(f"*** Gamess run completed with warnings.")
        else:
            print(f"*** Gamess run completed OK.")
        
        # Set error output to propagate.
        mol.errorDict = errorDict
        
        return mol