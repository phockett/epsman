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


"""

from pygamess import Gamess
import numpy as np

from pathlib import Path

from epsman._util import isnotebook

# TODO: remember how to handle this elegantly/selectively - would still like to create empty class.
try:
    from rdkit import Chem
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

try:
    import pandas as pd
except ImportError:
    print("*** Pandas not available, fancy tabulated data display will not be available.")


class ESgamess():
    """
    Class to wrap pygamess + epsman functionality.

    Basic Gamess job setup and handling from `pygamess docs <https://github.com/kzfm/pygamess#basic-usage>`_, with `RDKit <https://rdkit.org/docs/index.html>`_ on the backend.

    Currently wraps:

    - molFromSmiles(), molFromFile(), for core RDkit molecule creation
    - molFromPubChem(), for PubChemPy molecule downloader


    TODO:

    - More RDkit functionality, see https://www.rdkit.org/docs/source/rdkit.Chem.rdchem.html#rdkit.Chem.rdchem.RWMol

    """

    from epsman._util import setAttribute

    __notebook__ = isnotebook()


    def __init__(self, searchName = None, smiles = None, molFile = None, addH = False, molOverride = None,
                    job = None, sym = 'C1', atomList = None, verbose = 1,
                    buildES = False, fileOut = None):

        self.verbose = verbose

        # Setup molecule
        self.setAttribute('name', searchName)
        self.setAttribute('smiles', smiles)
        self.setAttribute('molFile', molFile)   # Path(molFile))  # Don't force to Path here, errors if None.

        # molOverride is set as a dictionary of atoms, e.g. {0:{'name':'H', 'Z': 1, 'coords':[0.0, 0.0, 1.0]}, 1:{'name':'C', 'Z': 16, 'coords':[0.0, 0.0, 4.0]}}.
        # This will be used at Gamess input file write INSTEAD of self.mol if set.
        # Note Z must be an int here currently - Gamess writer appends '.0' in current codebase.
        self.setAttribute('molOverride', molOverride)

        # Try to setup molecule from input
        self.molFromFile()
        self.molFromPubChem()
        self.molFromSmiles(addH = addH)


        # Additional vars for Gamess job
        # Set default to None to allow easy overwrite later... or set to 'Default' and 'C1' for always running config?
        # Issue is as usual - when should these be set to defaults, and should they always be overwritten by new input by default?
        self.setAttribute('job', job)
        self.setAttribute('sym', sym)
        self.setAttribute('atomList', atomList)

        # Display some output unless mol is empty
        if hasattr(self, 'mol'):
            try:
                if self.__notebook__:
                    display(self.mol)  # If notebook, use display to push plot.
                else:
                    # return hv.Curve(d0)  # Otherwise return hv object.
                    pass
            except:
                pass

            # Add atomsDict, refDict and atomsHist
            for item in ['atomsDict', 'refDict', 'atomsHist']:
                self.setAttribute(item, {})

            # self.printCoords()
            self.printTable()

            # Automatic Gamess pipeline execution
            if buildES:
                self.buildES(fileOut)


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

    def setCoords(self, coordList = None):
        """
        Basic wrapper for RDkit conformer.SetAtomPosition() to update coord table.

        Pass dictionary with items giving atom index and [x,y,z] position to set.
        E.g. coordList = {1:[0,0,0]}

        TODO:
        - Add passing as a table or array for brevity, e.g. input list or np.array in format [[atom ID, X, Y, Z], ...]
        - Coord table parsing & conversion from file or Gamess outputs (see pyGamess)

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

        if self.verbose:
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


    def rotateFrame(self, rotations = {'y':np.pi/2}, canonicalise=True):
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

        if self.verbose:
            print("*** Set frame rotations, new coord table:")
            self.printTable()

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

        note = f'Set reference coords key {refKey} from passed dict.'

        if atomDict is None:
            atomDict = self.atomsDict.copy()
            note = f'Set reference coords key {refKey} from self.atomsDict.'

        if histKey is not None:
            atomDict = self.atomsHist[histKey]
            note = f"Set reference coords key {refKey} from self.atomsHist['{histKey}']"

        self.refDict[refKey] = atomDict

        if self.verbose:
            print(note)


    def printTable(self):
        """
        Show pretty table using Pandas (use printCoords() for simple version).

        Code is very similar to printCoords(), based on pyGamess routines (atom_section, https://github.com/kzfm/pygamess/blob/master/pygamess/gamess.py)

        TODO: amalgamate these!
        """

        # conf = self.mol.GetConformer(0)
        # atomList = []
        # for atom in self.mol.GetAtoms():
        #     pos = conf.GetAtomPosition(atom.GetIdx())
        #
        #     atomList.append([atom.GetIdx(), atom.GetSymbol(), atom.GetAtomicNum(), pos.x, pos.y, pos.z])
        self.getAtoms()

        try:
            # self.pdTable = pd.DataFrame(atomList, columns=['Ind','Species','Atomic Num.','x','y','z'])
            # self.pdTable = pd.DataFrame(self.atomDict['table'], columns=self.atomDict['items'])
            self.pdTable = pd.DataFrame(self.atomsDict['table'], columns=self.atomsDict['items'])  # Nov 2023 debugged, now "atomsDict"

            if self.__notebook__:
                display(self.pdTable)

        except AttributeError or NameError:
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

        # Set job type
        self.g.run_type(runType)

        if fileOut is not None:
            self.g.debug = True

        # Run
        self.mol = self.g.run(self.mol, **kwargs)

        try:
            self.E = self.mol.GetProp('total_energy')

            print(f"*** Gamess {runType} completed")

            if self.verbose > 0:
                print(f"E = {self.E}")

            if self.verbose > 1:
                if runType == 'optimize':
                    self.printTable()

        except KeyError:
            print("*** Warning: result does not include 'total_energy', this likely indicates Gamess run failed.")

        # Tidy up
        if fileOut is not None:
            Path(self.g.gamout).rename(fileOut)  # Rename output
            Path(self.g.gamin).unlink()          # Tidy input
            self.gout = fileOut
            print(f"*** Gamess output file moved to {fileOut}")


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
