# Testing code from https://docs.figshare.com
# 10/12/19

# See https://stackoverflow.com/questions/50597854/problems-with-future-and-swagger-client-in-python
# For additional notes & Swagger_client instructions
# To generate, paste https://docs.figshare.com/swagger.json to https://editor.swagger.io
# This gives some errors...
# Also, keywords seem to be changed now to _, not camelHump, format.

# Add Swagger module full path for testing
import sys
sys.path.append(r'E:\code\epsman\repo\figshare_swagger')

# from __future__ import print_statement  # Unnecessary
import time
import swagger_client
from swagger_client.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = swagger_client.ArticlesApi()
page = 5 # Long | Page number. Used for pagination with page_size (optional)
pageSize = 10 # Long | The number of results included on a page. Used for pagination with page (optional) (default to 10)
limit = 789 # Long | Number of results included on a page. Used for pagination with query (optional)
offset = 789 # Long | Where to start the listing(the offset of the first result). Used for pagination with limit (optional)
order = 'published_date' # String | The field by which to order. Default varies by endpoint/resource. (optional) (default to published_date)
orderDirection = 'desc' # String |  (optional) (default to desc)
institution = 789 # Long | only return articles from this institution (optional)
publishedSince = '2019-11-15' # String | Filter by article publishing date. Will only return articles published after the date. date(ISO 8601) YYYY-MM-DD (optional)
modifiedSince = '2000-01-01' # String | Filter by article modified date. Will only return articles published after the date. date(ISO 8601) YYYY-MM-DD (optional)
group = 789 # Long | only return articles from this group (optional)
resourceDoi = None # String | only return articles with this resource_doi (optional)
itemType = 789 # Long | Only return articles with the respective type. Mapping for item_type is: 1 - Figure, 2 - Media, 3 - Dataset, 5 - Poster, 6 - Journal contribution, 7 - Presentation, 8 - Thesis, 9 - Software, 11 - Online resource, 12 - Preprint, 13 - Book, 14 - Conference contribution, 15 - Chapter, 16 - Peer review, 17 - Educational resource, 18 - Report, 19 - Standard, 20 - Composition, 21 - Funding, 22 - Physical object, 23 - Data management plan, 24 - Workflow, 25 - Monograph, 26 - Performance, 27 - Event, 28 - Service, 29 - Model (optional)
doi = None # String | only return articles with this doi (optional)
handle = None # String | only return articles with this handle (optional)

# This runs... but throws issues with some keywords.
# Problem with API defn?
# Runs OK via https://editor.swagger.io, via Curl or http, e.g.
#   curl -X GET "https://api.figshare.com/v2/articles?page_size=10&order=published_date&order_direction=desc&published_since=2019-11-11" -H "accept: application/json"
#   https://api.figshare.com/v2/articles?page_size=10&order=published_date&order_direction=desc&published_since=2019-11-11

try:
    # Public Articles
    # Original code from https://docs.figshare.com - issue with conflicting args, and nonexistent args - should be _ notation it seems.
    # api_response = api_instance.articles_list(page=page, pageSize=pageSize, limit=limit, offset=offset, order=order, orderDirection=orderDirection, institution=institution, publishedSince=publishedSince, modifiedSince=modifiedSince, group=group, resourceDoi=resourceDoi, itemType=itemType, doi=doi, handle=handle)
    api_response = api_instance.articles_list(page=page, published_since=publishedSince, order=order)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ArticlesApi->articlesList: %s\n" % e)
