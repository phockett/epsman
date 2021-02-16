"""
ePSman paths
--------------------------------

Default paths etc. set here.

30/12/19    v1  Moved defns. from __init__.py and _epsJobGen.py

"""

from pathlib import Path
import pprint  # For dict printing
import inspect  # For module path

def setScripts(self):
    """Set list of utility scripts & templates."""
    # Set dictionary of Shell scripts for .inp file generation.
    # Now also includes notebook templates... needs a tidy up!
    self.scrDefn = {'basic':'ePS_input_write_template_basic.sh',
                    'wf-sph':'ePS_input_write_template_wf_sph.sh',
                    'nb-tpl-JR-v1':'ePSproc_epsman_template_dev_051119_JR-single.ipynb',
                    'nb-tpl-JR-v2':'ePSproc_epsman_template_dev_051219_JR-single.ipynb',
                    'nb-tpl-JR-v3':'ePSproc_epsman_template_tidy_100120_JR-single.ipynb',
                    'nb-tpl-JR-v4':'ePSproc_epsman_template_tidy_120120_JR-single.ipynb',
                    'nb-tpl-JR-v5':'ePSproc_epsman_template_tidy_300320_JR-single.ipynb',
                    'nb-tpl-JR-v4-EC':'ePSproc_epsman_template_tidy_300320_JR-E-chunck.ipynb',
                    'nb-sh-JR':'jr_epsProc_nb.sh'
                    }

    # Python scripts for repo processing & packaging, currently in /repo directory.
    self.scpDefnRepo = {'nb-post-doi':'nbHeaderPost.py',
                    'pkg':'pkgFiles.py',
                    'pkgNohup':'pkgRemoteNohup.sh',
                    'jobJSON':'jobJSON.py',
                    'upload':'remoteUpload.py',
                    'uploadNohup':'remoteUploadNohup.sh'
                    }

    # Scripts for web deploy, in /web
    self.scpDefnWeb = {'buildIndex':'buildSphinxHTML.py',
                    'buildHTML':'buildHTML.sh'
                    }


def setPaths(self):
    """Set default paths."""
    # TODO: finish this... should add looping over necessary paths, functionalised and with more searching. Sigh.
    # FOR NOW - set know paths based on above.
    # For epsman on remote, should set for github or python subdirs?
    
    # self.hostDefn[self.host]['scpdir'] = Path(self.hostDefn[self.host]['wrkdir'], 'scripts2019')  # Local files
    self.hostDefn[self.host]['scpdir'] = Path(self.hostDefn[self.host]['home'], 'python/epsman/shell')  # Scripts from epsman repo
    self.hostDefn[self.host]['jobPath'] = Path(self.hostDefn[self.host]['wrkdir'], 'jobs')
    self.hostDefn[self.host]['jobComplete'] = Path(self.hostDefn[self.host]['jobPath'], 'completed')

    # Set ePS default path - may be machine dependent however!
    # TODO: add check and test routine here.
    self.hostDefn[self.host]['ePSpath'] = Path('/opt/ePolyScat.E3/bin/ePolyScat')

    # Paths for epsproc and epsman...? May not be required... should test for these on host?
    # Path(inspect.getfile(em))

    # Anaconda path, used for remote env setting.
    self.hostDefn[self.host]['condaPath'] = Path(self.hostDefn[self.host]['home'], 'anaconda3/bin/activate')
    self.hostDefn[self.host]['condaEnv'] = 'base'

    # Set additional path for repo scripts - this should be moved somewhere more sensible!
    self.hostDefn[self.host]['repoScpPath'] = Path(self.hostDefn[self.host]['home'], 'python/epsman/repo')
    self.hostDefn['localhost']['localSettings'] = Path(self.hostDefn['localhost']['home'], 'python/epsman/localSettings')  # Local settings required on localhost only...?
                                                                                                                          # So far just used for access tokens and such.
    # self.hostDefn[self.host]['localSettings'] = self.hostDefn['localhost']['localSettings']

    # Set web paths
    self.hostDefn[self.host]['webScpPath'] = Path(self.hostDefn[self.host]['home'], 'python/epsman/web')
    self.hostDefn[self.host]['webDir'] = Path(self.hostDefn[self.host]['home'], 'github/ePSdata')

    # Print
    print('\n***Default paths set')
    pprint.pprint(self.hostDefn[self.host])

    print('\n***Checking bin dirs')
    # Check ePS exists
    if self.checkFiles(self.hostDefn[self.host]['ePSpath'].as_posix())[0]:
        print('ePolyScat bin OK')
    else:
        print('***ePolyScat bin not found')

    # Check Conda
    if self.checkFiles(self.hostDefn[self.host]['condaPath'].as_posix())[0]:
        print('Anaconda bin OK')
    else:
        print('***Anaconda bin not found')
