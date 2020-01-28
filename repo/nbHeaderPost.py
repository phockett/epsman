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
import os
from pathlib import Path
from datetime import datetime

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
# Note on badges: these appear centered in Jupyter viewer, so put at head and tail of page only.
# Left aligned in HTML via nbSphinx.
# Don't include in nbSphine header at HTML gen time, since this is missing DOI info.
def constructHeader(jobInfo, fileIn, title, doi = None):

    # Ensure fileIn is Path object
    fileIn = Path(fileIn)

    # Set webroot assuming molecule/notebook format for both fileIn and web.
    webURL = f"https://phockett.github.io/ePSdata/{fileIn.parts[-2]}/{fileIn.stem}.html"
    # Format for Zenodo, e.g. doi 10.5281/zenodo.3600654 corresponds to https://zenodo.org/record/3600654
    if doi is not None:
        zenodoURL = f"https://zenodo.org/record/{doi.split('.')[-1]}"
        zenodoBadge = f"[![DOI](https://zenodo.org/badge/doi/{doi}.svg)](http://dx.doi.org/{doi})"
    else:
        zenodoURL = ''
        zenodoBadge = ''

    # Creative Commons licensing
    # Raw HTML - doesn't pass through nbSphinx
    # ccText = 'Licensed under <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">Creative Commons Attribution-NonCommercial-ShareAlike 4.0 (CC BY-NC-SA 4.0)</a>'
    # ccBadge = '<img src="https://i.creativecommons.org/l/by-nc-sa/4.0/88x31.png" alt="Creative Commons Attribution-NonCommercial-ShareAlike 4.0 (CC BY-NC-SA 4.0)">'
    # MD version...
    ccText = 'Licensed under [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 (CC BY-NC-SA 4.0)](https://creativecommons.org/licenses/by-nc-sa/4.0/)'
    ccBadge = '[![Creative Commons Attribution-NonCommercial-ShareAlike 4.0 (CC BY-NC-SA 4.0)](https://i.creativecommons.org/l/by-nc-sa/4.0/88x31.png)](https://creativecommons.org/licenses/by-nc-sa/4.0/)'

    # Construct new header with file info + DOI.
    # Note formatting for Markdown - \n\n or <br> to ensure newline, but need \n after headings, and \n\n or <br> for bodytext.
    # sourceText = ("\n".join(['# ePSproc: ' + jobInfo[1].split(',')[0],
    #                             "<br>".join([
    #                                 '*electronic structure input*: ' + Path(jobInfo[-1].split()[-1]).name[0:-1], # Grab name, -1 to drop ''
    #                                 '*ePS output file*: ' + fileIn.stem + '.inp.out',
    #                                 f"*Web version*: {webURL}",
    #                                 f"Dataset: "
    #                                 f"DOI (dataset): [{doi}](http://dx.doi.org/{doi})",
    #                                 '[Citation details](#Cite-this-dataset)']),
    #                             '',
    #                             '## Job details',
    #                              "<br>".join(jobInfo[0:4])]))
    # NOTE: <br> case doesn't propagate through nbsphinx... use \n and list formatting instead.
    sourceText = ("\n".join([f"{zenodoBadge}  {ccBadge}", '\n# ePSproc: ' + title,
    # sourceText = ("\n".join([f"{zenodoBadge}  {ccBadge}", '\n# ' + title,   # For web case, may want to remove 'ePSproc'...?
                                "\n- ".join(['\n- '
                                    '*electronic structure input*: ' + Path(jobInfo[-1].split()[-1]).name[0:-1], # Grab name, -1 to drop ''
                                    '*ePS output file*: ' + fileIn.stem + '.inp.out',
                                    f"*Web version*: {webURL}",
                                    f"Dataset: {zenodoURL}",
                                    f"DOI (dataset): [{doi}](http://dx.doi.org/{doi})",  # Plain text
                                    # f"DOI (dataset): {zenodoBadge}",   # Badge version.
                                    ccText,
                                    '[Citation details](#Cite-this-dataset)']),
                                '',
                                '## Job details',
                                 # "\n- ".join(jobInfo[0:4])]))
                                 "".join(map('\n- {}'.format, jobInfo[0:4]))]))  #With map to allow prefix on all lines.


    # TODO: DOI badge to add, format [![DOI](https://zenodo.org/badge/doi/10.5281/zenodo.18914.svg)](http://dx.doi.org/10.5281/zenodo.18914)

    return sourceText


# Define footer info
# TODO: add citation info here
def constructFooter(jobInfo, fileIn, datasetName, doi = None):

    #Job details
    # TODO: fix this for old jobs or add override.
    title = 'ePSproc: ' + datasetName

    # Set webroot assuming molecule/notebook format for both fileIn and web.
    webURL = f"https://phockett.github.io/ePSdata/{fileIn.parts[-2]}/{fileIn.stem}.html"

    # year = datetime.now().year  # Set as current year
    year = jobInfo[3].split()[-1] # Set as ePS job year

    sourceText = f"""
## Cite this dataset

Hockett, Paul ({year}). *{title}*. Dataset on Zenodo. DOI: {doi}. URL: {webURL}

*Bibtex*:
```bibtex
@data{{{datasetName},
    title = {{{title}}}
    author = {{Hockett, Paul}},
    doi = {{{doi}}},
    publisher = {{Zenodo}},
    year = {{{year}}},
    url = {{{webURL}}}
  }}
```

See [citation notes on ePSdata](https://phockett.github.io/ePSdata/cite.html) for further details.

[![DOI](https://zenodo.org/badge/doi/{doi}.svg)](http://dx.doi.org/{doi})  [![Creative Commons Attribution-NonCommercial-ShareAlike 4.0 (CC BY-NC-SA 4.0)](https://i.creativecommons.org/l/by-nc-sa/4.0/88x31.png)](https://creativecommons.org/licenses/by-nc-sa/4.0/)

"""

    return sourceText



# Routine to grab relevant electronic structure files and copy to job dir for packaging.
# def getEstructureFiles(fileIn, fileInfo):
#     """Copy electronic structure files to job output file structure"""
#
#  *** THIS IS NOW SET IN _repo.py, cpESFiles()


# Write header info and save notebook
def writeHeader(inputNB, sourceText):

    # Replace header cell and save.
    # inputNB['cells'][0] = nbformat.v4.new_markdown_cell(source = ['doi: ', doi])
    inputNB['cells'][0] = nbformat.v4.new_markdown_cell(source = sourceText)
    nbformat.write(inputNB, fileIn.as_posix(), version = 4)

# Write header info and save notebook
def writeFooter(inputNB, sourceText):
    # Replace header cell and save.
    # inputNB['cells'][0] = nbformat.v4.new_markdown_cell(source = ['doi: ', doi])
    # inputNB['cells'].append(nbformat.v4.new_markdown_cell(source = sourceText))
    inputNB['cells'][-1] = nbformat.v4.new_markdown_cell(source = sourceText)
    nbformat.write(inputNB, fileIn.as_posix(), version = 4)


# Write markdown readme file to include with job
def writeReadme(sourceTextHead, sourceTextFoot):

    # Set files
    textFile = fileIn.with_suffix('.md')
    readmeFile = Path(fileIn.parent, 'readme.txt')

    # Format and write summary file, markdown format
    sourceText = f"""
# ePSdata dataset

See [about ePSdata](https://phockett.github.io/ePSdata/about.html) for details.

{sourceTextHead}

{sourceTextFoot}

    """

    with open(textFile, 'w') as f:
        f.write(sourceText)

    print(f"***Written md summary file: {textFile}")


    # Format and write generic readme
    sourceText = f"""
ePSdata dataset general readme

This dataset contains files:
- readme.txt    This file.
- <file>.md     Markdown (text) file summarising the dataset, including dataset-specific links and citation information.
- <file>.ipynb  Jupyter notebook file with basic post-processing (for an HTML version, see https://phockett.github.io/ePSdata).
- <file>.zip    Archive of source files, may be in a multipart zip format due to repository file-size limits.*
- <file>.json   Full job details in JSON format, including archive file list.

For more details, see:
https://phockett.github.io/ePSdata/about.html
https://github.com/phockett/ePSdata/

Licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 (CC BY-NC-SA 4.0) https://creativecommons.org/licenses/by-nc-sa/4.0/

* To rebuild a multipart zip (Linux):
$ zip -s 0 multipart.zip --out output.zip

    """

    with open(readmeFile, 'w') as f:
        f.write(sourceText)

    print(f"***Written readme file: {readmeFile}")



# If running as main, take passed args and run functions.
if __name__ == "__main__":
    # Passed args
    fileIn = Path(sys.argv[1])

    if len(sys.argv)>2:
        doi = sys.argv[2]
    else:
        doi = None

    if len(sys.argv)>3:
        title = sys.argv[3]
    else:
        title = None


    # Read notebook
    print(f'\n***Reading notebook: {fileIn}')
    inputNB = nbformat.read(fileIn.as_posix(), as_version = nbVersion)

    # Get job info from file
    jobInfo = getInfo(inputNB)

    # Set file info if doi is passed
    # If passed at command line this may be a string
    if ((doi is not None) and (doi!='None')) and (jobInfo is not None):

        if title is None:
            title = jobInfo[1].split(',')[0]  # Default job name if not overridden

        # Generate header from jobInfo
        sourceTextHead = constructHeader(jobInfo, fileIn, doi, title)
        writeHeader(inputNB, sourceTextHead)
        print(f'\n***Written notebook header: {fileIn}, job name: {title}')

        sourceTextFoot = constructFooter(jobInfo, fileIn, doi, title)
        writeFooter(inputNB, sourceTextFoot)
        print(f'\n***Written notebook footer: {fileIn}, job name: {title}')

        writeReadme(sourceTextHead, sourceTextFoot)

    else:
        pass


# return Path(jobInfo[-1].split()[-1]).name[0:-1]
