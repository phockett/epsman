"""
ePSman repo interfacing
-----------------------

10/12/19    Init... plan to test for OSF, Figshare and Zenodo.

"""

# Import from /repo

#*** Functions to package job for repo

# Zenodo API interface

# Package job files for repo

# Processed job file header creation
def nbWriteHeader(self):
    """
    Set header cell for ePSproc Notebooks for repo upload.
    """

    # Check if notebook file list is set, set if missing.
    if not hasattr(self, 'nbFileList'):
        self.getNotebookJobList()

    # Load notebook, write header & save
    # NOTE - this requires doi to be preset.
    for nb in self.nbFileList:
        # Register job with repo

        # Run python script for notebook post-process.
        result = self.c.run('python ' + Path(self.hostDefn[self.host]['scpdir'], self.scrDefn['nb-post-doi']).as_posix() + f' {nb} {doi}')


#*** Repo uploader

# Upload package
