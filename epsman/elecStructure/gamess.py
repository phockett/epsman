"""
Class for basic handling of Gamess jobs using pyGamess and RDKit as backend.

26/02/21

Libraries:

- `pygamess <https://github.com/kzfm/pygamess>`_ (also `on pypi <https://pypi.org/project/pygamess/>`_)
- `RDKit <https://rdkit.org/docs/index.html>`_
- `PubChemPy <https://pypi.org/project/PubChemPy/>`_

Aims here:

- Wrap pygamess functionality with Fabric for client-host architecture.
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
except ImportError:
    print("*** RDkit not available, molecule generation functions will not be available.")
    # rdkFlag = False

try:
    import pubchempy as pcp
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


    def __init__(self, searchName = None, smiles = None, molFile = None, addH = False, job = None, sym = None, verbose = 1):

        self.verbose = verbose

        # Setup molecule
        self.setAttribute('name', searchName)
        self.setAttribute('smiles', smiles)
        self.setAttribute('molFile', molFile)

        # Try to setup molecule from input
        self.molFromPubChem()
        self.molFromSmiles(addH = addH)
        self.molFromFile()

        # Additional vars for Gamess job
        # Set default to None to allow easy overwrite later... or set to 'Default' and 'C1' for always running config?
        # Issue is as usual - when should these be set to defaults, and should they always be overwritten by new input by default?
        self.setAttribute('job', job)
        self.setAttribute('sym', sym)

        # Display some output

        try:
            if self.__notebook__:
                display(self.mol)  # If notebook, use display to push plot.
            else:
                # return hv.Curve(d0)  # Otherwise return hv object.
                pass
        except:
            pass

        self.printCoords()


    def molFromSmiles(self, addH = False):
        """Generate molecule from smiles following pygames docs examples"""

        if self.smiles is not None:

            self.mol = Chem.MolFromSmiles(self.smiles)

            if addH:
                self.mol = Chem.AddHs(self.mol)

            # self.mol_with_atom_index()

            # Basic geom routine to set some positions
            AllChem.EmbedMolecule(self.mol)   # This creates a conformer idx=0, with (arb?) coords
            AllChem.UFFOptimizeMolecule(self.mol,maxIters=200)  # Try basic opt

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

            self.mol = Chem.MolFromMolFile(self.molFile.as_posix())



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
        if self.name is not None:
            if self.molFile is None:
                self.molFile = Path(Path.cwd(), self.name).with_suffix('.' + fileType)

            try:
                pcp.download(fileType, self.molFile, self.name, searchType, record_type=recordType)

            except IOError as err:
                print(f'*** File {self.molFile} already exists, pass overwrite=True to overwrite')

        # TODO: print or return something here...
        # print()

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
            This runs :py:func:`rdkit.Chem.rdMolTransforms` (see `RDkit docs <https://rdkit.org/docs/source/rdkit.Chem.rdMolTransforms.html#module-rdkit.Chem.rdMolTransforms>`__.)

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


    def printTable(self):
        """
        Show pretty table using Pandas (use printCoords() for simple version).

        Code is very similar to printCoords(), based on pyGamess routines (atom_section, https://github.com/kzfm/pygamess/blob/master/pygamess/gamess.py)

        TODO: amalgamate these!
        """

        conf = self.mol.GetConformer(0)
        atomList = []
        for atom in self.mol.GetAtoms():
            pos = conf.GetAtomPosition(atom.GetIdx())

            atomList.append([atom.GetIdx(), atom.GetSymbol(), atom.GetAtomicNum(), pos.x, pos.y, pos.z])

        self.pdTable = pd.DataFrame(atomList, columns=['Ind','Species','Atomic Num.','x','y','z'])

        if self.__notebook__:
            display(self.pdTable)


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

    def initGamess(self, gamess_path = '/usr/local/gamess', **kwargs):
        """
        Init Gamess object & build (default) input card.

        All kwargs are passed to pyGamess init.

        This minimally requires `gamess_path`, which defaults to '/usr/local/gamess'

        """

        # Init pyGames object
        self.g = gamessInput(job = self.job, sym = self.sym, gamess_path = gamess_path, **kwargs)

        # Set pointer to options
        self.params = self.g.options
        print("*** Init pyGamess job.")

        # Show current Gamess input
        print("Default Gamess input card (use self.params to modify):")
        print(self.g.input(self.mol))

        # self.gCard = {}
        # self.gCard['default'] = self.g.input(self.mol)
        #
        # print("*** Gamess input card set to self.gCard['default']")
        # print(self.gCard['default'])


    def setGamess(self, job = None, note = None, sym = None):
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

        # Set all inputs - THIS MIGHT work, but relies on knowing pyGamess input structure - may be better to wrap key params instead?
        # self.g.setAttributesFromDict(**kwargs, overwriteFlag = True)

        # self.gCard[job] = self.g.input(self.mol, job = note, sym = sym)
        #
        # print(f"*** Gamess input card set to self.gCard['{job}']")
        # print(self.gCard[job])

        # Set extras
        self.g.setExtras(note, sym, overwriteFlag = True)

        # Show current Gamess input
        print("*** Gamess input card:")
        print(self.g.input(self.mol))  #, job = note, sym = sym))

    def runOpt(self, fileOut = None):
        """Run Gamess optimization with pyGamess"""

        self.g.run_type('optimize')
        self.mol = self.g.run(self.mol)

        print("*** Optimized self.mol")
        print(self.mol.GetProp("total_energy"))
        self.printTable()


    def runE(self, fileOut = None):
        """Energy only run with pyGamess"""

        self.g.run_type('energy')
        self.mol = self.g.run(self.mol)

        print(self.mol.GetProp("total_energy"))


    # def runGamess(self, job = 'Default', sym = 'C1', **kwargs):
    def runGamess(self, fileOut = None, **kwargs):
        """ Wrapper for pyGamess.run(), using self.mol and additional input options. """

        # # Additional vars for Gamess job
        # self.setAttribute('job', job)
        # self.setAttribute('sym', sym)
        # self.setGamess(**kwargs)

        # TODO: write decorator for this! For now just call runGamess as main function.
        # def setGamessFiles(self, fileOut = None):
        #     """Copy temp Gamess output file to specified location"""
        #

        if fileOut is not None:
            self.g.debug = True

        self.g.run(self.mol)

        if fileOut is not None:
            Path(self.g.gamout).rename(fileOut)  # Rename output
            Path(self.g.gamin).unlink()          # Tidy input

            print(f"*** Gamess output file moved to {fileOut}")





# Set basic decorator for file handling
# TODO


# Try subclassing pyGamess routine for extra control over input...
class gamessInput(Gamess):
    from epsman._util import setAttribute, setAttributesFromDict

    def __init__(self, job = None, sym = None, **kwargs):

        super().__init__(**kwargs)
        # self.debug = True  # Set this to keep files
        self.verbose = None

        self.setExtras(job,sym)

    def input(self, mol):   #, job = None, sym = None, overwriteFlag = False):
        """Wrap input writer for additional parameters"""

        # self.setExtras(job,sym, overwriteFlag)

        return "{0} $DATA\n{1}\n{2}\n{3} $END\n".format(self.print_header(),
                                                        self.job, self.sym,
                                                        self.atom_section(mol))

    def setExtras(self, job, sym, overwriteFlag = False):
        """Quick hack for setting extra attribs & also pushing to self.options"""

        # Additional vars for Gamess job - may want to push to self.options?
        self.setAttribute('job', job, overwriteFlag)
        self.setAttribute('sym', sym, overwriteFlag)
        self.options['extra'] = {'job':self.job, 'sym':self.sym}
