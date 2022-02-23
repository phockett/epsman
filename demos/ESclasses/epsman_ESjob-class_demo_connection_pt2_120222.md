---
jupytext:
  formats: ipynb,md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.13.6
kernelspec:
  display_name: Python [conda env:.conda-epsman-demo]
  language: python
  name: conda-env-.conda-epsman-demo-py
---

# ESjob class - pt. 2 ePS job creation & run jobs
12/02/22

2nd demo for ESjob class, including host connection and job writing.

For basic electronic structure file IO and creation of ePS jobs based on inputs (pt 1) see epsman_ESjob-class_demo_120222.ipynb. 

- Currently tested for Gamess and Molden IO only.
- Uses [CCLIB on the backend](http://cclib.github.io/), so should be easily extendable to other CCLIB-supported cases.

```{code-cell} ipython3

```

## Imports

```{code-cell} ipython3
# Import main package
# import epsman as em

# For ePS job creation with electronic structure handling, use elecStructure.ESjob
from epsman.elecStructure.ESjob import ESjob
```

```{code-cell} ipython3
# For testing, set the module path and test file.
import inspect
from pathlib import Path

modDir = Path(inspect.getfile(ESjob)).parent
testFilePath = modDir/'fileTest'  # Default module test files, these are included with Github repo.
```

## Class creation with host

Minimally this needs an IP, which can be a host name for known hosts. The user will be prompted for any other missing info when trying to connect.

Note that the host machine *can be the same as the local machine*. Simply pass `host=<somename>` along with `IP = 'localhost'` in this case (a different hostname is required in this case since the local machine already sets `localhost` as a key name - this might change in future).

TODO: update script and related  paths to repo?

```{code-cell} ipython3
# For ESjob class basic file handling for Gamess Log files is implemented.
job = ESjob(fileName = 'xe_SPKrATZP_rel.log', fileBase = testFilePath,
            IP = 'ePS-VM')
#             host = 'ePS-VM', IP = 'ePS-VM')
```

```{code-cell} ipython3
# Connect to host
job.initConnection()
```

```{code-cell} ipython3
# All host definitions are set in job.hostDefn
job.hostDefn
```

```{code-cell} ipython3
# The host name is set in self.host
job.host
```

```{code-cell} ipython3
# All settings can be overwritten by passing a Path
from pathlib import Path

# Change script dir from default
job.hostDefn[job.host]['scpdir'] = Path('~/github/epsman/shell')
```

### Notes on paths

Currently a bit of a mess... 

#### Default/base paths

The default paths are set as follows:

On local machine in `epsJob.__init__`:

```
self.hostDefn = {
    'localhost':{'host':socket.gethostname(),
        'IP':'127.0.0.1',
        'home':Path.home(),
        'wrkdir':Path.cwd(),
        'webDir':Path(Path.home(), 'github/ePSdata')}
    }

```

Hence local files default to the current working directory.

On remote, at connection, in `epsJob.initConnection()`:

```
# Build dir list if not already set
if 'home' not in self.hostDefn[self.host].keys():
    print('\n\nSetting host dir tree.')

    if home is None:
        self.hostDefn[self.host]['home'] = Path(self.c.run('echo ~', hide = True).stdout.strip())
    else:
        self.hostDefn[self.host]['home'] = Path(home)

    # testwrkdir = self.c.run('ls -d eP*', hide = True).stdout.split()
    testwrkdir = self.c.run(f'cd {home}; ls -d eP*', hide = True, warn = True).stdout.split()

    if len(testwrkdir) > 1:
        print('Found multiple ePS directories, please select working dir:')
        # print(testwrkdir)
        for n, item in enumerate(testwrkdir):
            print(f'{n}: {item}')

        N = int(input('List item #: '))
        self.hostDefn[self.host]['wrkdir'] = Path(self.hostDefn[self.host]['home'], testwrkdir[N])
    elif testwrkdir:
        self.hostDefn[self.host]['wrkdir'] = Path(self.hostDefn[self.host]['home'], testwrkdir[0])
    else:
        print('No ePS* subdirs found, setting work dir as home dir.')
        self.hostDefn[self.host]['wrkdir'] = Path(self.hostDefn[self.host]['home'])

    print('Set remote wrkdir: ' + self.hostDefn[self.host]['wrkdir'].as_posix())

    # Set additional default paths for host.
    self.setPaths()
    
```

This will set `self.hostDefn[self.host]['wrkdir']` to an `ePS` directory if found, or to the user home directory. Or, pass `home='homeDir'` when running `initConnection()` to override.

To reset the `wrkdir` and propage, after connection, use `self.setWrkDir(wrkdir='newWorkingDir')`.

Other default paths are set by `self.setPaths()`, building from the currently set `wrkdir`.

TODO:

- Update `self.setPaths()`, has some redundant stuff currently (23/02/22).
- Propagation from `self.setWrkDir` not complete?


#### Job paths

These cannot be set until a job has been initalised via `self.setJob()`. From this, `self.setJobPaths()` builds a set of job-specific dirs building from `self.hostDefn[host]['wrkdir']`.

This uses the following schema:

```
self.hostDefn[host]['systemDir'] = Path(self.hostDefn[host]['wrkdir'], self.mol)
self.hostDefn[host]['elecDir'] = Path(self.hostDefn[host]['systemDir'], 'electronic_structure')
self.hostDefn[host]['genDir'] = Path(self.hostDefn[host]['systemDir'], 'generators')
self.hostDefn[host]['genFile'] = Path(self.hostDefn[host]['genDir'], self.genFile)
# self.hostDefn[host]['jobRoot'] = Path(self.hostDefn[host]['systemDir'], self.genFile.stem)
if self.genFile is not None:
    # self.hostDefn[host]['jobRoot'] = Path(self.hostDefn[host]['systemDir'], Path(self.genFile.stem).stem) # This form will work for X.Y.conf and X.conf styles.
    self.hostDefn[host]['jobRoot'] = Path(self.hostDefn[host]['systemDir'], self.batch) # Just use mol/batch/orb to match dir tree creation?

# self.hostDefn[host]['jobRoot'] = Path(self.hostDefn[host]['systemDir'], self.batch)  # Use job type (batch) here
self.hostDefn[host]['jobDir'] = Path(self.hostDefn[host]['jobRoot'], self.orb)  # Definition here to match shell script. Possibly a bit redundant, but allows for multiple orbs per base job settings.

self.hostDefn[host]['webSystemDir'] = Path(self.hostDefn[host]['webDir'], 'source', self.mol)

```

Hence 

- `<wrkdir>/mol` is the base job directory, `systemDir`.
- Generator files use `systemDir/generators`.
- Electronic structure files `systemDir/electronic_structure`
- subdirs per job as `systemDir/batch/orbital`.

Note that `self.setJobPaths()` can be run directly, and is also called by `self.setGenFile()`.

+++

## Build ePS job

With a host set, the full ePolyScat build process should complete.

```{code-cell} ipython3
job.buildePSjob(channel = 18)
```

### Fix missing shell scripts

+++

If the script fails at `self.writeInp()` this is likely due to the shell scripts for job-writing missing on the host. This currently needs to be fixed manually.

Example failure:

```
E = 1.0:1.0:1.0, 1 points total, 1/1 = 1 job files will be written.
Writing input files on remote...


*** Failed to build job at self.writeInp.
Encountered a bad command exit code!

Command: '~/github/epsman/shell/ePS_input_write_template_basic_noDefaults.sh 1.0 1.0 1 /home/eps/ePS/test/generators/test.orb18_A2U.conf'

Exit code: 127

Stdout: already printed

Stderr: already printed

```

+++

**TODO: setup VM with scripts**

Could push from local repo automatically?

TODO: check/fix permissions on script.

```{code-cell} ipython3
# Fix missing shell script

# Set local path to package dir
job.hostDefn['localhost']['scpdir'] = modDir.parent/'shell'

# Ser remote path
# job.hostDefn[job.host]['scpdir'] = Path('~/ePS/shell')
job.hostDefn[job.host]['scpdir'] = Path('/home/eps/ePS/shell')
```

```{code-cell} ipython3
# Available scripts can be listed
job.scrDefn
```

```{code-cell} ipython3
# Set dir on host if missing
# Note this currently uses the low-level Fabric object, should be wrapped!
# UPDATE - should now be cleaner with dir creation on pushFile() below if necessary
# job.c.run('mkdir -p ' + job.hostDefn[job.host]['scpdir'].as_posix())
```

```{code-cell} ipython3
# job.pushFile(job.hostDefn['localhost']['scpdir']/job.scrDefn['basicNoDefaults'], job.hostDefn[job.host]['scpdir'])
job.pushFile(job.hostDefn['localhost']['scpdir']/job.scrDefn['basic'], job.hostDefn[job.host]['scpdir'])
```

```{code-cell} ipython3
job.writeScript
```

```{code-cell} ipython3
# What about sync for this...?
# This should now work (23/02/22), provided 'scpFile' is set on local machine (it's not set by default).
job.syncFilesDict('scpFile')
```

```{code-cell} ipython3
# Run job writer again...

job.writeInp()
```

(Above errors should now be fixed...)

+++

### Job configuration files

The end-point of the build routine is the creation of a job configuration file & execution of a shell script on the host machine to create ePS input files. This is currently slightly convoluted, but basically aims to:

- Provide a method for a minimal job definition in the .conf file, which is then used to generate multiple ePS input files for different energies. 
- Make the conf file (somewhat) portable, hence also includes all necessary paths on the host.
- Ensure minimal file IO between local and host machine.

(In future the shell scripts should be replaced by a python method and better templating.)

```{code-cell} ipython3
# The .conf file is also stored locally (defaults to current working dir), and the full string in self.jobSettings
print(f"Configuration (generation) file: {job.genFile}")
print("\n*******")
print(job.jobSettings)
```

### Modifying jobs

To update & rewrite the configuration file, make changes to any of the data structures and propagate...

The current build routine implements:

1. `self.esData.setChannel(channel)`: Set ionization channel for job
1. `self.setJob()`: setup basic defaults, including name and paths, for job.
2. `self.esData.setePSinputs()`: Set parameter dictionaries self.ePSglobals and self.ePSrecords from inputs, the latter is defined mainly from the electronic structure file (and channel setting).
3. `self.esData.writeInputConf()`:  Dictionaries > strings for job template
4. `self.setJobInputConfig()`: Settings string > template file string
5. `self.writeGenFile()`: Template file string > conf file format (adds paths etc.)
6. `self.createJobDirTree()`: Creates job tree on host, and pushes generator (conf) file.
7. `self.Elist = em.multiEChunck(Estart = Estart, Estop = Estop, dE = dE, EJob = EJob, precision = precision)`: Set energies for input file generation on host.
8. `self.writeInp(scrType = scrType, wLog = writeInpLog)`: Write ePS jobs on host, making use of .conf file and shell script as given by `scrType`.

Any step can be updated/run independently.

TODO: streamline this!

```{code-cell} ipython3
# Change something via a method

# For symmetries currently need to run both gen and set functions
# job.esData.genSymList(Ssym = 'SG')  # Set for a single scattering symmetry only - NOTE this sets self.symList, but doesn't propagate
# job.esData.setePSinputs(Ssym = 'SG')  # Set self.ePSglobals and self.ePSrecords from inputs - NOTE this may reset other params too!
                                      # NOTE - need to add some flags here to overwrite!

# TODO: "update" setting for setePSinputs() and/or chain functions more carefully.

# Update 23/02/22: now automatic sym overwrite
job.esData.setePSinputs(Ssym = 'SG')
```

```{code-cell} ipython3
job.esData.symList
```

```{code-cell} ipython3
# Change something in job settings manually
job.esData.ePSrecords['IP']=50.0
```

```{code-cell} ipython3
# Propagate - TODO: tidy this up!
job.esData.writeInputConf()  # Dictionaries > strings for job template
job.setJobInputConfig()  # Settings string > template file string

# Print
print(job.jobSettings)
```

```{code-cell} ipython3
# Rewrite config to disk (local copy)
job.writeGenFile()

# For remote either push manually, or run job.createJobDirTree()

# TODO: update main build routine with an "update" option!
```

```{code-cell} ipython3
# Run job writer again to generate .inp files with new settings.

job.writeInp()
```

## Energies & job chuncking

This is currently handled by:

- `self.Elist`, 2D numpy array defining energies per file.
- `self.writeInp()`, method to write ePS input files per set of energies.

The Elist can be set manually, or via the `multiEChunck` method.
`self.multiEChunck(Estart = Estart, Estop = Estop, dE = dE, EJob = EJob, EJobRange = None, precision = precision)` set energies for input file generation on host.

```{code-cell} ipython3
# Currently set list - default is a single point at 1 eV
job.Elist
```

```{code-cell} ipython3
# Demo some settings
Estart = 10
Estop = 45
dE = 5

job.multiEChunck(Estart = Estart, Estop = Estop, dE = dE)
job.Elist
```

```{code-cell} ipython3
# Force multiple files if required
job.multiEChunck(Estart = Estart, Estop = Estop, dE = dE, EJob = 5)
job.Elist
```

```{code-cell} ipython3
# Large E sets should chunck automatically
# The points per file will default to the greatest common divisor within EJobRange, np.gcd(Elist.size, np.arange(EJobRange[0],EJobRange[1])).max()
# (with some wiggle room).
Estop = 200
job.multiEChunck(Estart = Estart, Estop = Estop, dE = dE)
job.Elist
```

## More about ePS input files

In the current implementation, the .conf file is used as the base for writing ePolyScat job files, using one of the shell scripts. This is a bit messy, but allows for easy creation & management of job files on the host only.

Note - this may/should be changed to an all-python templating method in future!

For more general details on ePolyScat input files and options, see the [ePolyScat manual](https://epolyscat.droppages.com/); there's also a [brief tutorial in the ePSproc docs](https://epsproc.readthedocs.io/en/latest/ePS_ePSproc_tutorial/ePS_tutorial_080520.html) (which follows `test12.inp` from the ePS manual).

+++

### Available scripts

A list of current scripts is given in `job.scrDefn`. Note this currently includes scripts for various purposes.

TODO: change to nested dict by type & including notes!

```{code-cell} ipython3
job.scrDefn
```

```{code-cell} ipython3
# Commands executed by self.writeInp() are collected in self.writeLog
job.writeLog
```

```{code-cell} ipython3
# Note these are objects returned by Fabric, so the output can be displayed too
print(job.writeLog[0].stdout)
```

```{code-cell} ipython3
# And outputs in the log file
job.logFile
```

```{code-cell} ipython3
!more {job.logFile}
```

### Files & details

Currently manual - TODO: wrap to methods.

```{code-cell} ipython3
# Job path
job.hostDefn[job.host]['jobDir']
```

```{code-cell} ipython3
# Get list of .inp files
fileList = job.getFileList(job.hostDefn[job.host]['jobDir'], fileType='.inp')
```

```{code-cell} ipython3
# To view a sample input file, it can be pulled to the local machine directly, 

# TODO: update pullFile with pushFile remote fixes!
# job.pullFile(Path('testInp'), Path(fileList[0]))

# or piped from the host
# job.c.run('more ' + fileList[1])  # Full file, note this might be quite large
nFile = 1
job.c.run('head -60 ' + fileList[nFile])

# TODO: view function for this?
```

### Job file breakdown

The job inputs basically follow the simple photoionization examples from the [ePolyScat manual](https://epolyscat.droppages.com/), so may NOT be suitable in all cases (and may not be the best way to do some things). 

The current scripts set commands for ePS to compute photoionization matrix elements for each symmetry and energy, with `PhIon`, `GetCro` and `DumpIdy` commands (see the [ePSproc advanced tutorial for a brief intro](https://epsproc.readthedocs.io/en/latest/ePS_ePSproc_tutorial/ePS_adv_tutorial_080520.html)).

Essentially, there are 3 main segments:

1. Init job & global settings, including the electronic structure file and list of energies.

```{code-cell} ipython3
job.c.run('head -42 ' + fileList[nFile]);
```

2. A repeated set of `scat` runs (via `PhIon`), for each symmetry pair, and cross-section outputs (via `GetCro`).

```{code-cell} ipython3
job.c.run("sed -n '43,70p' " + fileList[nFile]);
```

3. Dumping all matrix elements to file (per energy).

```{code-cell} ipython3
job.c.run("tail -n 20 " + fileList[nFile]);
```

## Versions

```{code-cell} ipython3
import scooby
scooby.Report(additional=['epsman', 'fabric', 'cclib'])
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
!git ls-remote --heads git://github.com/phockett/epsman
```

```{code-cell} ipython3

```

```{code-cell} ipython3

```
