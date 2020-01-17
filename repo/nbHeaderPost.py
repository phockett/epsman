"""
epsman

Local python script for Notebook header read & write.

Can be called from Fabric for remote run case, only requires standard libs + nbformat for notebook IO.

May be a better way to do this?

16/12/19    v1

TO DO:
- Loop over list of local files? Currently need to call per file.

"""

import nbformat
import sys
from pathlib import Path

# Settings
nbVersion = 4  # May not be required?

# Get info from notebook file.
def getInfo(inputNB):

    # Grab job details - template specific, this grabs lines from cell with job summary output.
    # Basic try/except functionality here for cases with bad/missing data - likley indicates an aborted eps job.
    # TODO: add search routine here.
    # TODO: add additional job info - currently commented out since it needs to be correctly propagated.
    try:
        # jobInfo = inputNB['cells'][6]['outputs'][0]['text'].split('\n')[2:6]  # Job info output
        jobInfo = inputNB['cells'][9]['outputs'][0]['text'].split('\n')[2:8]  # Job summary output
        # jobInfo.extend(inputNB['cells'][7]['outputs'][0]['text'].split('\n')[16:])  #ePSproc file read info
        print(*jobInfo, sep='\n')  # Print info to terminal, can also use to pass info via Fabric connection object when run remotely.

    except KeyError:
        jobInfo = None
        print('***Missing jobInfo')



    return jobInfo


# Define header info
def constructHeader(jobInfo, fileIn, doi = None):

    # Ensure fileIn is Path object
    fileIn = Path(fileIn)

    # Construct new header with file info + DOI.
    # Note formatting for Markdown - \n\n or <br> to ensure newline, but need \n after headings, and \n\n or <br> for bodytext.
    sourceText = ("\n".join(['# ePSproc: ' + jobInfo[1].split(',')[0],
                                "<br>".join([
                                    '*electronic structure input*: ' + Path(jobInfo[-1].split()[-1]).name[0:-1], # Grab name, -1 to drop ''
                                    '*ePS output file*: ' + fileIn.stem + '.inp.out',
                                    f"*Web version*: http://github.pages/{fileIn.stem}",
                                    f"DOI (dataset): [http://dx.doi.org/{doi}]({doi})"]),
                                '',
                                '## Job details',
                                 "<br>".join(jobInfo[0:4])]))

    return sourceText


# Define footer info
# TODO: add citation info here
def constructFooter(jobInfo, fileIn, doi = None):

    return None

    # Ensure fileIn is Path object
    # fileIn = Path(fileIn)
    #
    # # Construct new header with file info + DOI.
    # # Note formatting for Markdown - \n\n or <br> to ensure newline, but need \n after headings, and \n\n or <br> for bodytext.
    # sourceText = ("\n".join(['# Cite this: ' + jobInfo[1].split(',')[0],
    #                             "<br>".join([
    #                                 '*electronic structure input*: ' + Path(jobInfo[-1].split()[-1]).name[0:-1], # Grab name, -1 to drop ''
    #                                 '*ePS output file*: ' + fileIn.stem + '.inp.out',
    #                                 f"*Web version*: http://github.pages/{fileIn.stem}",
    #                                 f"DOI (dataset): [http://dx.doi.org/{doi}]({doi})"]),
    #                             '',
    #                             '## Job details',
    #                              "<br>".join(jobInfo[0:4])]))
    #
    # return sourceText



# Routine to grab relevant electronic structure files and copy to job dir for packaging.
# def getEstructureFiles(fileIn, fileInfo):
#     """Copy electronic structure files to job output file structure"""
#
#  *** THIS IS NOW SET IN _repo.py, cpESFiles()


# Write header info and save notebook
def writeHeader(inputNB, jobInfo):

    # Replace header cell and save.
    # inputNB['cells'][0] = nbformat.v4.new_markdown_cell(source = ['doi: ', doi])
    inputNB['cells'][0] = nbformat.v4.new_markdown_cell(source = sourceText)
    nbformat.write(inputNB, fileIn.as_posix(), version = 4)

# Write header info and save notebook
def writeFooter(inputNB):
    # Replace header cell and save.
    # inputNB['cells'][0] = nbformat.v4.new_markdown_cell(source = ['doi: ', doi])
    inputNB['cells'].append(nbformat.v4.new_markdown_cell(source = sourceText))
    nbformat.write(inputNB, fileIn.as_posix(), version = 4)

# If running as main, take passed args and run functions.
if __name__ == "__main__":
    # Passed args
    fileIn = Path(sys.argv[1])

    if len(sys.argv)>2:
        doi = sys.argv[2]
    else:
        doi = None

    # Read notebook
    print(f'\n***Reading notebook: {fileIn}')
    inputNB = nbformat.read(fileIn.as_posix(), as_version = nbVersion)

    # Get job info from file
    jobInfo = getInfo(inputNB)

    # Set file info if doi is passed
    # If passed at command line this may be a string
    if ((doi is not None) and (doi!='None')) and (jobInfo is not None):
        # Generate header from jobInfo
        sourceText = constructHeader(jobInfo, fileIn, doi)
        writeHeader(inputNB, sourceText)
        # sourceText = constructFooter(jobInfo, fileIn, doi)
        # writeFooter(inputNB, sourceText)
        print(f'\n***Written notebook header: {fileIn}')

    else:
        pass


# return Path(jobInfo[-1].split()[-1]).name[0:-1]
