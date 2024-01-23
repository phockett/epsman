---
jupytext:
  formats: ipynb,md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.13.6
kernelspec:
  display_name: Python [conda env:epsman-dev-shared-310122]
  language: python
  name: conda-env-epsman-dev-shared-310122-py
---

# ESgamess: molecule and Gamess job handling class (basic demo)
30/03/21

This class handles Gamess jobs (full pipeline) on a local machine only.

Core functionality is provided by the following libraries:

- [PubChemPy](https://pypi.org/project/PubChemPy/)
   - Interface with [PubChem](https://pubchem.ncbi.nlm.nih.gov).
- [RDKit](https://rdkit.org/docs/index.html)
   - Molecule class/handling routines.
   - Transformations.
   - Figures (2D natively, uses [py3Dmol on the backend](https://pypi.org/project/py3Dmol/) for 3D rendering).
- [pygamess](https://github.com/kzfm/pygamess)
   - Setup Gamess input cards.
   - Run Gamess calculations (local machine only).

This class creates a pipeline with these tools, and implements a few extra helper routines, with the general aim to make this part of the process as painless as possible.

Minimal method for pipeline to ePolyScat jobs:

PubChem download > Fix reference frame (symmetry axis to Z) > Run Gamess > Export/convert.

This is [implemented directly](#Minimal-job-pipeline-to-generate-electronic-structure-&-input-files-for-ePolyScat).

22/11/23, 23/01/24 (debug & tidy)

Updated some methods and finished notes.

- Better setCoords() handling, including Pandas method.
- Support for XYZ files for molecule creation (RDkit version > 2022.03 required).

+++

## Imports

```{code-cell} ipython3
# Import class
from epsman.elecStructure.gamess import ESgamess
```

## Molecule creation routines

Currently wraps routines from RDkit + PubChemPy for rapid setup from existing sources. Shows 2D structure and coord tabe on execution.

Notes:

- Atom sequence and labelling may change with method.
- Similarly, atomic charges, bonding and display may change with method.
- In general, this doesn't matter if coords are passed to another electronic structure routine, but may be important in some cases.

TODO: add support for manual molecule creation. This can be done via a file at the moment, or via RDkit backend (see, for example, [the RDkit docs](https://www.rdkit.org/docs/GettingStartedInPython.html#reading-and-writing-molecules)).

+++

### Easy methods

```{code-cell} ipython3
# Molecule from PubChem
testDL = ESgamess(searchName = 'N2O')
```

```{code-cell} ipython3
# Molecule from SMILES
testSmiles = ESgamess(smiles = '[N-]=[N+]=O')
```

```{code-cell} ipython3
# From file, e.g. SDF file downloaded from PubChem above.
# This uses RDkit Chem.MolFromMolFile() on the backend, 
# For details of files supported see https://www.rdkit.org/docs/RDKit_Book.html#mol-sdf-support-and-extensions 
# and https://www.rdkit.org/docs/source/rdkit.Chem.rdmolfiles.html

testFile = ESgamess(molFile = 'N2O.SDF')
```

### Manual or from XYZ file

Since RDKit 2022.03 XYZ file support is included, which is also suitable for manual molecule creation from a list of atoms and coordinates.

Full details can be found in https://github.com/rdkit/UGM_2022/blob/main/Notebooks/Landrum_WhatsNew.ipynb

The method can be used to init a system from a file or string representation. The basic format is:

```
[no. atoms]

[Atom 0] [x] [y] [z]
[Atom 1] [x] [y] [z]
...

```

```{code-cell} ipython3
# Generate XYZ representation from existing case above
testDL.genXYZ()
```

```{code-cell} ipython3
# Use the string representation to define a new system

testXYZstr = ESgamess(xyz = testDL.xyzStr)
```

```{code-cell} ipython3
# Note that this routine can accept a string, or filename.

testXYZfile = ESgamess(xyz = 'N2O.xyz')
```

### Additional info

+++

If `Pandas` is available, a fancy print is available with `printTable()`.

```{code-cell} ipython3
testDL.printTable()
```

If `py3Dmol` is available, interactive 3D plots are available in notebooks with `plot3D()`.

```{code-cell} ipython3
testDL.plot3D()
```

The molecule is stored as an RDkit object, `self.mol`, and [RDkit methods are also available](https://www.rdkit.org/docs/GettingStartedInPython.html).

```{code-cell} ipython3
type(testDL.mol)
```

```{code-cell} ipython3
# Calling the object will render it
testDL.mol
```

```{code-cell} ipython3
# RDkit method example
testDL.mol.GetNumAtoms()
```

## pyGamess wrapper

+++

### Setup Gamess job

```{code-cell} ipython3
# Init the pyGamess job.
# This minimally needs a gamess_path set, which defaults to '/opt/gamess'
testDL.initGamess() # Using defaults
```

This creates a `pyGamess` object, accessible at `self.g`, and properties can be inspected.

```{code-cell} ipython3
print(type(testDL.g))
print(testDL.g.gamess_path)
```

All Gamess job parameters are stored in a dictionary, at `self.params` (also `self.g.options`), and can be set there directly using `self.setParam()` or dictionary methods. (For more details, see the [pyGamess docs for more info](https://github.com/kzfm/pygamess), and the [Gamess manual Input section for details of the available options](https://www.msg.chem.iastate.edu/gamess/GAMESS_Manual/input.pdf).)

`pyGamess` doesn't support symmetry or job annotation (uses 'C1' only), this can be added via a class wrapper here, and can be set via `self.setGamess` (this is also run automatically at class init). This adds an `extras` item to the params dictionary, with additional job details including symmetry.

**Note that is symmetry is set to anything other than 'C1', coordinate transforms may be required.** [See notes below.](#Symmetry-&-frame-transformations)

```{code-cell} ipython3
# Show all params
testDL.params
```

```{code-cell} ipython3
# Params can be modified or added using the setParams method...
testDL.setParam(inputGroup='contrl',inputDict={'maxit':30})
```

```{code-cell} ipython3
# Pass resetGroup = True to replace all existing group settings with the passed dict (otherwise settings will be added)...
testDL.setParam(inputGroup='contrl',inputDict={'scftyp': 'rhf'}, resetGroup = True)
```

```{code-cell} ipython3
# Params can also be modified or added using dictionary syntax
testDL.params['contrl']['runtyp']='energy'
testDL.params['contrl']['maxit'] = 60  # Add a control param. See https://www.msg.chem.iastate.edu/gamess/GAMESS_Manual/input.pdf
testDL.params
```

The current Gamess input card can always be checked via `self.printGamessInput()`

```{code-cell} ipython3
testDL.printGamessInput()
```

### Run Gamess

+++

#### Basic energy run

If a valid `gamess_path` is set, then this is simple, and the basic results are returned to `self.mol`, along with some diagnostic information.

```{code-cell} ipython3
# Run as per input card
testDL.runGamess()
```

```{code-cell} ipython3
# Energy
testDL.E
```

#### Run geometry optimization

Note this may fail in some cases for geometries not aligned in the preferred Gamess manner (major symmetry axis == z-axis), but in this case diagnostic info should be printed to screen.

```{code-cell} ipython3
# Run optimization, in this case the updated coord table is also shown if self.verbose > 1
# testDL.verbose = 2
testDL.runGamess(runType = 'optimize')
```

#### Troubleshooting Gamess errors

In case of issues, the current outputs can be inspected (or maybe printed directly if `self.verbose > 1`).

```{code-cell} ipython3
# Check errors if present
print(testDL.mol.GetProp('Warnings'))
print(testDL.mol.GetProp('ddikick'))
```

For geometry optimizations, the issue is typically the orientation of the coordinate system. A quick fix is to run the rotateFrame() method, which will try and orient the canonical RDkit alignment (symmetry axis == x-axis) to the canonical Gamess alignment (symmetry axis == z-axis), see [below for more details](#Symmetry-&-frame-transformations). Note that basic energy runs usually work without this fix, but it is required for geometry optimization or use of symmetry.

```{code-cell} ipython3
# A quick fix is to run the rotateFrame() method
testDL.rotateFrame()
testDL.verbose = 2   # If self.verbose > 1, runGamess will also print new (optimized) geom
testDL.runGamess(runType = 'optimize')
```

#### Gamess full output and log files

In the default case the tmp files are not kept. To keep the full Gamess output, supply a filename (full path).

The current output file path is set in `self.gout`.

```{code-cell} ipython3
# Check for tmp file. This will always be set, but may have been deleted.
print(testDL.gout)

!cat {testDL.gout}
```

```{code-cell} ipython3
# runGamess wrapper will take a path and move the output file.
testDL.runGamess(fileOut = '/tmp/test.out')
```

```{code-cell} ipython3
:tags: []

# In this case the complete output file is retained, and can also be printed
print(testDL.gout)
testDL.printGamess()
```

```{code-cell} ipython3
# For quick checks, there are also head and tail functions
testDL.tail()
```

## Symmetry & frame transformations

To use symmetry in the Gamess calculations, the system must be oriented such that the Z-axis is the highest symmetry axis. In tests both PubChem and RDkit seem to use the X-axis as the symmetry axis, so the frame needs to be rotated in general.

**For more details, see [the symmetry-focussed docs](ESgamess_class_demo_symmetry_011223-tidy.html).**

From the [Gamess manual](https://www.msg.chem.iastate.edu/gamess/GAMESS_Manual/docs-input.txt):

```
    The 'master frame' is just a standard orientation for
the molecule.  By default, the 'master frame' assumes that
    1.   z is the principal rotation axis (if any),
    2.   x is a perpendicular two-fold axis (if any),
    3.  xz is the sigma-v plane (if any), and
    4.  xy is the sigma-h plane (if any).
Use the lowest number rule that applies to your molecule.

        Some examples of these rules:
Ammonia (C3v): the unique H lies in the XZ plane (R1,R3).
Ethane (D3d): the unique H lies in the YZ plane (R1,R2).
Methane (Td): the H lies in the XYZ direction (R2).  Since
         there is more than one 3-fold, R1 does not apply.
HP=O (Cs): the mirror plane is the XY plane (R4).

In general, it is a poor idea to try to reorient the
molecule.  Certain sections of the program, such as the
orbital symmetry assignment, do not know how to deal with
cases where the 'master frame' has been changed.

Linear molecules (C4v or D4h) must lie along the z axis,
so do not try to reorient linear molecules.
```

This is set with `self.rotateFrame()`, which can set arbitrary rotations, but defaults to X > Z axis transformation. This uses the RDkit canoicalise and transformation functions, with rotation matrices, as per [Github user iwatobipen's example notebook](https://nbviewer.jupyter.org/github/iwatobipen/playground/blob/master/rotation_mol.ipynb). (Thanks to [iwatobipen](https://github.com/iwatobipen) and the [RDkit list](https://sourceforge.net/p/rdkit/mailman/message/36598250/).)

```{code-cell} ipython3
# Rotate the frame - default should align to Z-axis
testDL.rotateFrame()
```

Symmetry groups supported (from the [Gamess manual](https://www.msg.chem.iastate.edu/gamess/GAMESS_Manual/docs-input.txt)):

```
GROUP is the Schoenflies symbol of the symmetry group,
you may choose from
    C1, Cs, Ci, Cn, S2n, Cnh, Cnv, Dn, Dnh, Dnd,
    T, Th, Td, O, Oh.

NAXIS is the order of the highest rotation axis, and
must be given when the name of the group contains an N.
For example, "Cnv 2" is C2v.  "S2n 3" means S6.  Use of
NAXIS up to 8 is supported in each axial groups.

For linear molecules, choose either Cnv or Dnh, and enter
NAXIS as 4.  Enter atoms as Dnh with NAXIS=2.  If the
electronic state of either is degenerate, check the note
about the effect of symmetry in the electronic state
in the SCF section of REFS.DOC.
```

```{code-cell} ipython3
# Set Gamess input with symmetry
testDL.setGamess(note='N2O sym testing', sym='CNV 8')
```

Finally, it is worth noting that symmetrized jobs require only the unique atoms given on the input card. This is currently accomplished here rather crudely, via a list of atom indices (rows) to the input builder.

For example...

```{code-cell} ipython3
testDL.setGamess(note='N2O sym testing', sym='CNV 8', atomList = [0,2])
```

Where `self.params['extra']['atomList']` gives the sub-selection on which atoms are listed on the input card for symmetrized jobs (TODO: make this better/automated!).

```{code-cell} ipython3
testDL.params['extra']
```

**For more details, see [the symmetry-focussed docs](ESgamess_class_demo_symmetry_011223-tidy.html).**

+++

## Additional Gamess parameters

For the full set of [Gamess input options (inc. basis sets), see the manual](https://www.msg.chem.iastate.edu/gamess/GAMESS_Manual/docs-input.txt).

As per the above input cards, `pyGamess` writes only the minimal set of `$contrl`, `$basis` and `$system` inputs, using the supplied parameters dictionary.

For setting the basis set, a helper method `self.setBasis()` can be used. For general parameter setting, `self.setParam()` can be used, along with the specific Gamess group name for the paramter.

```{code-cell} ipython3
# The setBasis method wraps the PyGamess basis_set() method
testDL.setBasis("6-31G**")
```

```{code-cell} ipython3
# This only has limited support...
testDL.setBasis("ACCD")
```

```{code-cell} ipython3
# ... applying settings manually will always work however
testDL.setParam(inputGroup='basis',inputDict={'gbasis':'ACCD'}, resetGroup=True)  # Pass resetGroup=True to replace existing.
testDL.setParam(inputGroup='contrl',inputDict={'ISPHER':'1'})

# Note that dictionary syntax also works here, e.g. the above can also be set via:
# testDL.params['basis'] = {'gbasis':'ACCD'}
# testDL.params['contrl']['ISPHER']='1'  # For ACCD need this too! 
#
# But dictionary style will NOT work for 'extra' items.
```

```{code-cell} ipython3
# The pyGamess supported basis options are listed by self.basis()
testDL.basis()

# Full configurations can be found in self.basisDict
basis = 'STO3G'
print(f'Settings for {basis}: {testDL.basisDict[basis]}')
```

```{code-cell} ipython3
# Check updated input card
testDL.printGamessInput()
```

```{code-cell} ipython3
# Change some other parameters...
testDL.setParam(inputGroup='statpt', inputDict={'opttol': '0.01', 'nstep': '10'})  # Geom opt settings
testDL.params['system']['mwords']=50  # Memory settings, dict style

# Change atomList
# Note dictionary style will NOT work for 'extra' items, since some other settings are reconfigured in this case
testDL.setParam(inputGroup='extra', inputDict={'atomList':[0,1]})
```

## Additional transformations 

### Bond lengths & angles

These can be addressed using the [RDkit functionality](https://rdkit.org/docs/source/rdkit.Chem.rdMolTransforms.html).

There is also a wrapper for bond lengths at the moment, `self.setBondLength`, which takes a dictionary of bonds to set, in the format `{'Name':{'a1':0,'a2':1,'l':5}}` where 'a1' and 'a2' give the atom indices for atoms defining the bond. This wraps RDkit's [rdkit.Chem.rdMolTransforms.SetBondLength](https://rdkit.org/docs/source/rdkit.Chem.rdMolTransforms.html#rdkit.Chem.rdMolTransforms.SetBondLength).

TODO: clean up input, wrap angle setting functions(?).

+++

Here's a basic bond-length example

```{code-cell} ipython3
testDL.printTable()
```

```{code-cell} ipython3
bonds = {'NO':{'a1':0, 'a2':1, 'l':5}, 'NN':{'a1':1, 'a2':2, 'l':2}}
# testDL.setBondLength(bonds = {'NO':{'a0':0, 'a1':1, 'l':5}})
testDL.setBondLength(bonds)
```

Note that the RDkit routines move all atoms as appropriate for the new settings.

+++

### Manual coords

This is currently a little basic, and just wraps RDkit conformer.SetAtomPosition() routine for each atom. Set & select with a dictionary input, using atom indicies as keys.

```{code-cell} ipython3
# Set coords for specified atoms
coordsRef = {0:[0,0,0], 1:[0.7,0,1.0]}
testDL.setCoords(coordsRef)
```

```{code-cell} ipython3
# Set all atoms on a specified axes with coord
# This can be useful for symmetrized cases, since otherwise atoms may be erroneously duplicated in Gamess run (even for near-zero coords)
testDL.setAxis({'x':0.0, 'y':0.0})
```

## Minimal job pipeline to generate electronic structure & input files for ePolyScat

Possibly not advisable, since errors may go unnoticed, but the whole default pipeline can be executed with `self.buildES()`, which aims to string together the default cases above and produce a Gamess output file that can be used as input for ePolyScat. 

This can be run directly at class creation by passing `buildES=True`. To keep the Gamess output file, pass fileOut.

Todo: fix issues with running for existing class object, may reset some items inconsistently at `initGamess`.

```{code-cell} ipython3
# Set via build=True
# This runs the process from scratch
testBuild = ESgamess(searchName = 'N2O', fileOut = '/tmp/autobuild.out', buildES = True)
```

```{code-cell} ipython3
# Running the function for an existing class object also works
# Note this will use the existing geometry and configuration 
# (although some items MAY BE reset by initGamess() routine - TBD)
testDL.buildES(fileOut = '/tmp/autobuild.out')
```

## Versions

```{code-cell} ipython3
import scooby
scooby.Report(additional=['epsman', 'cclib', 'rdkit'])
```

```{code-cell} ipython3
# Check current Git commit for local ePSproc version
from pathlib import Path
import epsman as em

!git -C {Path(em.__file__).parent} branch
!git -C {Path(em.__file__).parent} log --format="%H" -n 1
```

```{code-cell} ipython3
# Check current remote commits
!git ls-remote --heads https://github.com/phockett/epsman
```
