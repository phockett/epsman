"""
Class for basic handling of Gamess jobs using pyGamess and RDKit as backend.

26/02/21

Libraries:

- `pygamess <https://github.com/kzfm/pygamess>`_ (also `on pypi <https://pypi.org/project/pygamess/>`_)
- `RDKit <https://rdkit.org/docs/index.html>`_

Aims here:

- Wrap pygamess functionality with Fabric for client-host architecture.
- Enable full ePS job pipeline, starting with a Gamess calculation.
- Provide methods for generating ePS jobs with multiple inputs, e.g. bond length scans.

"""

from pygamess import Gamess

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


    def __init__(self, searchName = None, smiles = None, molFile = None, addH = False, verbose = 1):

        self.verbose = verbose

        # Setup molecule
        self.setAttribute('name', searchName)
        self.setAttribute('smiles', smiles)
        self.setAttribute('molFile', molFile)

        # Try to setup molecule from input
        self.molFromPubChem()
        self.molFromSmiles(addH = addH)
        self.molFromFile()

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


    def setBondLength(self, bonds = None):
        """
        Basic wrapper for AllChem.SetBondLength

        Pass dictionary with items giving atom1, atom2 and the bond length to set.
        E.g. bonds = {'CCBond':{'a1':0, 'a2':1, 'l':10}}
        """

        if bonds is not None:
            for bond in bonds.items():
                AllChem.SetBondLength(self.mol.GetConformer(),bond['a1'],bond['a2'],bond['l'])


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
