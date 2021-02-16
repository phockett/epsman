# Testing Zenodo API


#*** REST API
# Code from https://developers.zenodo.org/#introduction

import requests

r = requests.get("https://zenodo.org/api/deposit/depositions")
r.status_code
r.json()
