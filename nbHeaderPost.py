"""
epsman

Local python script for Notebook header writing.

Can be called from Fabric for remote run case.

16/12/19    v1

TO DO:
- Loop over list of local files?
- Set cell template.

"""

import nbformat
import sys
from pathlib import Path

# Passed args
fileIn = Path(sys.argv[1])
doi = sys.argv[2]

# Other settings
nbVersion = 4

# Read notebook
testNB = nbformat.read(fileIn.as_posix(), as_version = 4)

# Grab job details - template specific, this grabs lines from cell with job summary output.
# TODO: add search routine here.
# jobInfo = testNB['cells'][6]['outputs'][0]['text'].split('\n')[2:6]  # Job info output
jobInfo = testNB['cells'][9]['outputs'][0]['text'].split('\n')[2:8]  # Job summary output

# print(*jobInfo, sep='\n')  # Print info to terminal, can also use to pass info via Fabric connection object when run remotely.
print(jobInfo)  # When running with Fabric, get syntax error with above, not sure why.

# Construct new header with file info + DOI.
# Note formatting for Markdown - \n\n or <br> to ensure newline, but need \n after headings, and \n\n or <br> for bodytext.
# sourceTemplate = 'headerText.txt'
sourceText = ("\n".join(['# ePSproc: ' + jobInfo[1].split(',')[0],
                            "<br>".join([
                                '*electronic structure input*: ' + Path(jobInfo[-1].split()[-1]).name[0:-1], # Grab name, -1 to drop ''
                                '*ePS output file*: ' + fileIn.stem + '.inp.out',
                                f"*Web version*: http://github.pages/{fileIn.stem}",
                                f"DOI (dataset): [http://dx.doi.org/{doi}]({doi})"]),
                            '',
                            '## Job details',
                             "<br>".join(jobInfo[0:4])]))
# sourceText = 'Fabric test'

# Replace header cell and save.
# testNB['cells'][0] = nbformat.v4.new_markdown_cell(source = ['doi: ', doi])
testNB['cells'][0] = nbformat.v4.new_markdown_cell(source = sourceText)
nbformat.write(testNB, fileIn.as_posix(), version = 4)

# return Path(jobInfo[-1].split()[-1]).name[0:-1]
