import io
import sys
import traceback

from functools import partial
from pprint import pprint

from trac.core import TracError
from trac.resource import ResourceNotFound
from trac.web.api import HTTPBadRequest, HTTPForbidden, \
                         HTTPInternalServerError, HTTPNotFound, \
                         RequestDone, TracNotImplementedError, \
                         is_valid_default_handler, parse_header
from trac.web.main import RequestDispatcher as RequestDispatcherOrigin
from trac.util import arity
from trac.util.text import (exception_to_unicode, to_unicode, unicode_quote)
from trac.util.translation import _
from .chrome import Chrome


class RequestDispatcher(RequestDispatcherOrigin):

    def dispatch(self, req):
        """Find a registered handler that matches the request and let
        it process it.

        In addition, this method initializes the data dictionary
        passed to the the template and adds the web site chrome.
        """
        self.log.debug('Dispatching %r', req)
        chrome = Chrome(self.env)

        try:
            # Select the component that should handle the request
            chosen_handler = None
            for handler in self._request_handlers.values():
                if handler.match_request(req):
                    chosen_handler = handler
                    break
            if not chosen_handler and req.path_info in ('', '/'):
                chosen_handler = self._get_valid_default_handler(req)
            # pre-process any incoming request, whether a handler
            # was found or not
            self.log.debug("Chosen handler is %s", chosen_handler)
            chosen_handler = self._pre_process_request(req, chosen_handler)
            if not chosen_handler:
                if req.path_info.endswith('/'):
                    # Strip trailing / and redirect
                    target = unicode_quote(req.path_info.rstrip('/'))
                    if req.query_string:
                        target += '?' + req.query_string
                    req.redirect(req.href + target, permanent=True)
                raise HTTPNotFound('No handler matched request to %s',
                                   req.path_info)

            req.callbacks['chrome'] = partial(chrome.prepare_request,
                                              handler=chosen_handler)

            # Protect against CSRF attacks: we validate the form token
            # for all POST requests with a content-type corresponding
            # to form submissions
            if req.method == 'POST':
                ctype = req.get_header('Content-Type')
                if ctype:
                    ctype, options = parse_header(ctype)
                if ctype in ('application/x-www-form-urlencoded',
                             'multipart/form-data') and \
                        req.args.get('__FORM_TOKEN') != req.form_token:
                    if self.env.secure_cookies and req.scheme == 'http':
                        msg = _('Secure cookies are enabled, you must '
                                'use https to submit forms.')
                    else:
                        msg = _('Do you have cookies enabled?')
                    raise HTTPBadRequest(_('Missing or invalid form token.'
                                           ' %(msg)s', msg=msg))

            # Process the request and render the template
            resp = chosen_handler.process_request(req)
            if resp:
                resp = self._post_process_request(req, *resp)
                template, data, metadata, method = resp
                if 'hdfdump' in req.args:
                    req.perm.require('TRAC_ADMIN')
                    # debugging helper - no need to render first
                    with io.TextIOWrapper(io.BytesIO(), encoding='utf-8',
                                          newline='\n',
                                          write_through=True) as out:
                        pprint({'template': template,
                                'metadata': metadata,
                                'data': data}, out)
                        out = out.buffer.getvalue()
                    req.send(out, 'text/plain')
                self.log.debug("Rendering response with template %s", template)
                iterable = chrome.use_chunked_encoding
                if isinstance(metadata, dict):
                    iterable = metadata.setdefault('iterable', iterable)
                    content_type = metadata.get('content_type')
                else:
                    content_type = metadata
                output = chrome.render_template(req, template, data, metadata,
                                                iterable=iterable,
                                                method=method)
                # TODO (1.5.1) remove iterable and method parameters
                req.send(output, content_type or 'text/html')
            else:
                self.log.debug("Empty or no response from handler. "
                               "Entering post_process_request.")
                self._post_process_request(req)
        except RequestDone:
            raise
        except Exception as e:
            # post-process the request in case of errors
            err = sys.exc_info()
            try:
                self._post_process_request(req)
            except RequestDone:
                raise
            except TracError as e2:
                self.log.warning("Exception caught while post-processing"
                                 " request: %s", exception_to_unicode(e2))
            except Exception as e2:
                if not (type(e) is type(e2) and e.args == e2.args):
                    self.log.error("Exception caught while post-processing"
                                   " request: %s",
                                   exception_to_unicode(e2, traceback=True))
            if isinstance(e, PermissionError):
                raise HTTPForbidden(e) from e
            if isinstance(e, ResourceNotFound):
                raise HTTPNotFound(e) from e
            if isinstance(e, NotImplementedError):
                tb = traceback.extract_tb(err[2])[-1]
                self.log.warning("%s caught from %s:%d in %s: %s",
                                 e.__class__.__name__, tb[0], tb[1], tb[2],
                                 to_unicode(e) or "(no message)")
                raise HTTPInternalServerError(TracNotImplementedError(e)) \
                      from e
            if isinstance(e, TracError):
                raise HTTPInternalServerError(e) from e
            raise e

    def _post_process_request(self, req, *args):
        # `metadata` and the backward compatibility `method` are
        # optional in IRequestHandler's response. If not specified,
        # the default value is appended to response.
        metadata = {}
        resp = args
        method = None
        if len(args) == 3:
            metadata = args[2]
            resp += (None,)
        elif len(args) == 2:
            resp += (metadata, None)
        elif len(args) == 0:
            resp = (None,) * 3
        elif len(args) == 4:
            metadata = resp[2]
            method = resp[3]
        if method and isinstance(metadata, dict):
            metadata['method'] = method
        nbargs = len(resp)
        for f in reversed(self.filters):
            # As the arity of `post_process_request` has changed since
            # Trac 0.10, only filters with same arity gets passed real values.
            # Errors will call all filters with None arguments,
            # and results will not be not saved.
            extra_arg_count = arity(f.post_process_request) - 1
            if extra_arg_count == nbargs:
                resp = f.post_process_request(req, *resp)
            elif extra_arg_count == nbargs - 1:
                # IRequestFilters may modify the `method`, but the `method`
                # is forwarded when not accepted by the IRequestFilter.
                method = resp[-1]
                resp = f.post_process_request(req, *resp[:-1])
                resp += (method,)
            elif nbargs == 0:
                f.post_process_request(req, *(None,) * extra_arg_count)
        return resp
