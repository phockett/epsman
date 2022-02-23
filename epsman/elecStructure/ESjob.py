"""
ESjob clas - combines EShandler electronic structure file functionality + epsJob class functionality.

22/02/21    Basics working for file setting & epsJob functionatliy (including backend method dev)

19/02/21    Started dev.

"""

from pathlib import Path

import epsman as em  # For base class
import epsman.elecStructure.ESclass as ESclass  # Electronic structure methods

# With EShandler as base
# class ESjob(ESclass.EShandler, em.epsJob):

# Without EShandler - run, instead, on a per-host basis
class ESjob(em.epsJob):
    """
    Class to wrap epsJob + EShandler functionality.

    Note this currently assume a SINGLE electronic structure file as the base for a job.

    For multiple jobs with different ES files (e.g. bond-scans), this should be wrapped or subclassed - TBD.


    10/06/21: adding ES file handling & info functions following recent OCS run testing, first version of:

        - setOrbInfoPD, orbInfoSummary (source _orbInfo.py) to pull orbital/molecule info from ES file (part of EShandler class).
        - setChannel, setePSinputs, genSymList, convertSymList, writeInputConf (source _ePSsetup.py) for setting up ePS parameters based on ES file + additional inputs (part of EShandler class). Needs further work, may also move to ESjob class in future...?
        - setJobInputConfig, symTest, setSymsFromFiles (source _ePSsetup), additional ePS job setup routines... need some work!

    19/02/21: now init with epsman.epsJob class as parent, so can implement existing file IO methods.

    """

    from ._ePSsetup import setJobInputConfig, symTest, setSymsFromFiles

    def __init__(self, fileName = None, fileBase = None, outFile = None, master = 'localhost', overwriteFlag = True, **kwargs):

        # Job creation init
        em.epsJob.__init__(self, **kwargs)

        # Set master file only
        self.setMasterESfile(fileName = fileName, fileBase = fileBase, outFile = outFile, master = master, overwriteFlag = overwriteFlag)

        # self.esData.


    def buildePSjob(self, channel=None, mol='mol', batch='batch', note=None,
                    Estart=1.0, Estop = 1.0, dE = 1.0, EJob = None, precision = 2,
                    scrType = 'basicNoDefaults', writeInpLog = True,
                    overwriteFlag = False):
        """
        Master ePS job creation routine for electronic-structe case.
        This tries to run all job creation steps, with useful output.

        Parameters
        ----------
        channel : int
            Ionizing channel (orbital), for `self.esData.setChannel(channel)`

        mol, batch : strings, optional, default = 'mol','batch'
            Job labels, used for `self.setJob(mol = mol, orb = f'orb{job.esData.channel.name}', batch = batch)`
            This defines the job paths & names.

        note : string, optional, default = None
            Used for additional job annotation.
            `job.jobNote = f'{job.mol}, orb {job.esData.channel.name} ionization, batch {batch}, {note}.'`
            This is propagated to generator files & outputs.

        Estart, Estop, dE : floats, optional, default to 1.0
            Energy settings for the job, passed to em.multiEChunck()

        Ejob, precision : int, optional, default to None, 2
            Additional energy settings for the job, passed to em.multiEChunck()

        scrType : string, default = 'basicNoDefaults'
            Template script for job generation.
            Passed to self.writeInp().

        writeInpLog : bool, default = True
            Write log file on job creation if True.
            Passed to self.writeInp().

        overwriteFlag : bool, default = False
            Overwrite any existing settings if True.


        """

        # Set channel
        if channel is not None:
            self.esData.setChannel(channel)

        # TODO: set default case for HOMO here.

        # Init job
        print(f"\n*** Building job {mol}, orb{self.esData.channel.name} ({self.esData.channel.ePS}/{self.esData.PG}), batch: {batch}")

        try:
            # Set symmetries for job label (currently just sets ePS defined syms, may also want to propagate self.esData.channel.syms?)
            orbLabel = f'orb{self.esData.channel.name}_{self.esData.channel.ePS}'
            # Alternative method form - currently missing jobNote
            self.setJob(mol = mol, orb = orbLabel, batch = batch, jobNote = note, overwriteFlag = overwriteFlag) #, jobNote = f'{job.mol}, orb {jobES.channel.name} ionization, sym testing run.')

            if (note is None) and (self.jobNote is None):
                self.jobNote = f'{self.mol}, orb {self.esData.channel.name} ({self.esData.channel.ePS}/{self.esData.PG}) ionization, batch {batch}, {note}.'  # Additional notes, included at inp file head.
            # else:
            #     self.jobNote = note

        # except AttributeError as err:
            # TODO: add more specific checks here!
            # print("*** Failed to build job, no channel set - pass channel=int, or run self.esData.setChannel() to fix.")
            # return False

        except Exception as err:
            print("\n*** Failed to build job, can't run self.setJob.")
            print(err)
            return False

        # Build ePS generator file/configuration inputs
        try:
            # CURRENTLY NEED ALL OF THIS TO SET JOB FROM ES....
            self.esData.setePSinputs()  # Set self.ePSglobals and self.ePSrecords from inputs
            self.esData.writeInputConf()  # Dictionaries > strings for job template
            self.setJobInputConfig()  # Settings string > template file string

        except Exception as err:
            print("\n*** Failed to build job, can't set input configuration.")
            print(err)
            return False

        # Set generators
        try:
            self.writeGenFile()
            self.createJobDirTree()

        except Exception as err:
            print("\n*** Failed to build job, can't write gen file or create job tree - is the host set?")
            print(err)
            return False

        # Push gen file
        # Note - need pushFile even for localhost case, otherwise paths not set correctly.
        # But - should be OK if .createJobDirTree() executed correctly?
        # try:
        #     self.pushFile(self.genFile, self.hostDefn[self.host]['genDir'], overwritePrompt=False)  # OK for file in wrkdir, force overwrite - currently not working!!!
        #
        # except Exception as err:
        #     print(f"\n*** Failed to build job, can't push gen file {self.genFile} to host at {self.hostDefn[self.host]['genDir']}.")
        #     print(err)
        #     return False

        # Set energies & create ePS input files from generator
        try:
            # self.Elist = em.multiEChunck(Estart = Estart, Estop = Estop, dE = dE, EJob = EJob, precision = precision)
            self.multiEChunck(Estart = Estart, Estop = Estop, dE = dE, EJob = EJob, precision = precision)
            self.writeInp(scrType = scrType, wLog = writeInpLog)

        except Exception as err:
            print(f"\n*** Failed to build job at self.writeInp.")
            print(err)
            return False


        # May also need to push electronic structure files...?
        try:
            self.checkLocalESfiles()

        except Exception as err:
            print(f"\n*** Failed to build job at self.checkLocalESfiles() - electronic structure files may be missing on host.")
            print(err)
            return False





    def setMasterESfile(self, fileName = None, fileBase = None, outFile = None, master = 'localhost', overwriteFlag = True):
        """
        Set electronic structure files for master, create object and check file.

        """

        # Set file for master host only, from passed args.
        # This should work even for an uninitialised job (host settings not propagated).
        self.setAttribute('elecStructure', fileName, overwriteFlag = overwriteFlag)

        if fileBase is None:
            try:
                fileBase = self.hostDefn[master]['elecDir']
            except KeyError:
                fileBase = self.hostDefn[master]['wrkdir']  # Fallback to wrkdir if elecDir is not set.


        if fileName is not None:
            self.setHostDefns(elecDir = fileBase, elecFile = fileBase/self.elecStructure, host = master)
            # self.setHostDefns(, host = master)  #, elecFile = self.elecStructure)

            # Set master file object.
            # self.esData = ESclass.EShandler(self.hostDefn[master]['elecFile'], self.hostDefn[master]['elecDir'])

        # Set master file object.
        self.esData = ESclass.EShandler(fileName = fileName, fileBase = fileBase, outFile = outFile, verbose = self.verbose)

        # else:
        #     print("Skipping")


    def setESfiles(self, fileName = None, pushPrompt = True, overwriteFlag = False):  # fileBase = None,
        """
        Set electronic structure files for all self.hostDefn[host] and sync files.

        NOTE: this sets self.elecStructure if passed, then propagates and syncs files.
        This assumes self.hostDefn[host]['elecDir'] is already set on hosts.
        Use setMasterESfile() to update & check local file first, and setJob(), initConenction() or setWrkDir() or setJobPaths() etc. first.
        TODO: fix this!

        """

        # Set values in epsJob class format (if not already set)
        # self.setAttribute('elecDir', fileBase)  # This will set self.elecDir, which is generally not used - need to pass/check to self.hostDefn[host]['elecDir'], or just ignore here.
        self.setAttribute('elecStructure', fileName, overwriteFlag = overwriteFlag)

        # If fileBase not passed, check for currently set paths
        # TODO!

        # Set in master host list
        if self.elecStructure is not None:
            # Set in hostDefn
            # for host in self.hostDefn:
            #
            #     # if hasattr(self.hostDefn[host])
            #     self.hostDefn[host]['elecFile'] = Path(self.hostDefn[host]['elecDir'], self.elecStructure)

            # self.setHostDefns(elecDir = fileBase, elecFile = self.elecStructure) #FUCKING THIASSHIOEHD"FHK:ASDHGJK: DHAS:KG HASDGHKL:AK"JS
            # THIS WON"T WORK FOR CASES WHERE FILEBASE IS PER HOST THIS IS SHIT.
            # ALSO WON"T SET elecFile with correct dir

            # Propagate elecStructure file, assuming 'elecDir' set for host already - ALSO SHIT
            for host in self.hostDefn:
                self.setHostDefns(elecFile = Path(self.hostDefn[host]['elecDir'], self.elecStructure), host = host)

            # # Check file exists (local + host only)
            # if self.verbose:
            #     print(f'Electronic structure file {self.elecStructure} host checks:')
            #
            # fCheckHost = {}
            # for host in [self.host, 'localhost']:
            #     if host == 'localhost':
            #         fCheckHost[host] = self.checkLocalFiles(self.hostDefn[host]['elecFile'])  # use local Path file test.
            #     else:
            #         fCheckHost[host] = self.checkFiles(self.hostDefn[host]['elecFile'])   # Use remote Fabric file test.
            #
            #     if self.verbose:
            #         print(f"\n\t{host}:  \t{self.hostDefn[host]['elecFile']} \t{fCheckHost[host]}")
            #
            # pushFlag = 'n'
            # if (not fCheckHost[self.host]) and (fCheckHost['localhost']):
            #     if pushPrompt:
            #         pushFlag = print(f'Push missing file to {self.host}?  (y/n) ')
            #     else:
            #         pushFlag = 'y'
            #
            # if pushFlag == 'y':
            #     self.pushFileDict('elecFile')

            # Sync files
            self.syncFilesDict('elecFile', pushPrompt = pushPrompt)


    def checkLocalESfiles(self, master = 'localhost', pushPrompt = True):
        """
        Check master ES files, convert to Molden & sync with remote host.

        Note that this will currently only work for a local machine as master, since there is no remote run set here.

        Parameters
        ----------

        master : str, default = 'localhost'
            Set which host to use as master.
            Note that Gamess > Molden conversion will currently only work for a local machine, since there is no remote run set here.



        """

        # With EShandler as parent class
        # EShandler init
        # EShandler.__init__(self, fileName = fileName, fileBase = fileBase, outFile = outFile)

        # Run base init routine for job settings
        # super().__init__(**kwargs)

        # With EShandler per host - CURRENTLY ASSUMED TO BE LOCAL HOST ONLY, set as master
        # NOW SET as passed arg
        # for master in ['localhost']:

        # Set object & read file
        # self.esData = ESclass.EShandler(self.hostDefn[master]['elecFile'], self.hostDefn[master]['elecDir'])

        # If file is not a Molden file, read & convert
        if self.esData.data is not None:
            self.esData.writeMoldenFile2006()

            # # Update master file
            # self.elecStructure = self.esData.moldenFile.name
            #
            # # Update host paths (all hosts)
            # for host in self.hostDefn:
            #     self.hostDefn[host]['elecFileGamess'] = self.hostDefn[host]['elecFile']
            #     self.hostDefn[host]['elecFile'] = self.hostDefn[host]['elecDir'] self.esData.moldenFile  # self.hostDefn[host]['elecFile'].with_name
            #
            # # Sync files
            # self.syncFilesDict('elecFile', pushPrompt = pushPrompt)

            # Preserve Gamess file in new key
            for host in self.hostDefn:
                self.hostDefn[host]['elecFileGamess'] = self.hostDefn[host]['elecFile']

            # Update with existing functionality.
            self.setESfiles(fileName = self.esData.moldenFile.name, overwriteFlag = True, pushPrompt = pushPrompt)
