from . import html
import trac.util.html

for item in dir(html):
    if item.startswith("__") or not item.endswith("__"):
        continue
    setattr(trac.util.html, item, getattr(html, item))

from . import api
import trac.web.api
trac.web.api.ITemplateStreamFilter = api.ITemplateStreamFilter

from . import chrome
import trac.web.chrome
trac.web.chrome.Chrome = chrome.Chrome

from . import main
import trac.web.main
trac.web.main.Chrome = chrome.Chrome
trac.web.main.RequestDispatcher = main.RequestDispatcher

import trac.web.auth
trac.web.auth.tag = html.tag

import trac.util.translation
trac.util.translation.tag = html.tag
