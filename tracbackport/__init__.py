from . import api
from . import chrome
from . import main

import trac.web.chrome
import trac.web.main
import trac.web.api

trac.web.chrome.Chrome = chrome.Chrome
trac.web.main.Chrome = chrome.Chrome
trac.web.main.RequestDispatcher = main.RequestDispatcher
trac.web.api.ITemplateStreamFilter = api.ITemplateStreamFilter
