from swift.common.swob import Request, Response, wsgify
from swift.common.utils import split_path, public
# FIXME: Yeap, we are using private method. God, forgive me!
from swift.proxy.controllers.base import _set_info_cache as set_info_cache, \
        clear_info_cache
from swift.proxy.controllers.base import get_container_info, get_object_info

from wsgiproxy.app import WSGIProxyApp


class BaseController(object):
    def __init__(self, app, ver, account = None, container = None, obj = None):
        # The intention behind passing reference to instance of RgwiftApp
        # class is to provide controllers with ability to:
        #   1) access configutation options. Some of them are inspected
        #      by Swift utility functions like set_info_cache();
        #   2) issue further HTTP requests.
        self._app = app

        self.ver = ver
        self.account = account
        self.container = container
        self.obj = obj
        return

    def clean_acls(self, req):
        if 'swift.clean_acl' not in req.environ:
            return None
        for header in ('x-container-read', 'x-container-write'):
            if header in req.headers:
                try:
                    req.headers[header] = \
                        req.environ['swift.clean_acl'](header,
                                                       req.headers[header])
                except ValueError as err:
                    return HTTPBadRequest(request=req, body=str(err))
        return None

    def try_deny(self, req):
        if 'swift.authorize' in req.environ:
            aresp = req.environ['swift.authorize'](req)
            del req.environ['swift.authorize']
        else:
            # None means authorized.
            aresp = None
        return aresp

    def forward_request(self, req):
        """
        Forward the request using wsgi_proxy to real Swift backend
        """
        if 'REMOTE_ADDR' not in req.environ:
            req.environ['REMOTE_ADDR'] = '127.0.0.1'
        return req.get_response(
                WSGIProxyApp(href='http://127.0.0.1:8000/swift'))

    def GETorHEAD(self, req):
        return self.try_deny(req) or self.forward_request(req)

    @public
    def GET(self, req):
        return self.GETorHEAD(req)

    @public
    def HEAD(self, req):
        return self.GETorHEAD(req)

    @public
    def POST(self, req):
        return self.try_deny(req) or self.clean_acls(req) or \
               self.forward_request(req)

    @public
    def PUT(self, req):
        return self.try_deny(req) or self.clean_acls(req) or \
               self.forward_request(req)

    @public
    def COPY(self, req):
        return self.try_deny(req) or self.forward_request(req)

    @public
    def DELETE(self, req):
        return self.try_deny(req) or self.forward_request(req)

    @public
    def OPTIONS(self, req):
        return self.forward_request(req)


class AccountController(BaseController):
    def GETorHEAD(self, req):
        resp = self.forward_request(req)
        set_info_cache(self._app, req.environ, self.account,
                self.container, resp)
        return self.try_deny(req) or resp

    @public
    def POST(self, req):
        clear_info_cache(self._app, req.environ, self.account)
        return self.try_deny(req) or self.clean_acls(req) or \
               self.forward_request(req)

    @public
    def PUT(self, req):
        clear_info_cache(self._app, req.environ, self.account)
        return self.try_deny(req) or self.clean_acls(req) or \
               self.forward_request(req)

    @public
    def DELETE(self, req):
        clear_info_cache(self._app, req.environ, self.account)
        return self.try_deny(req) or self.forward_request(req)

class ContainerController(BaseController):
    def GETorHEAD(self, req):
        resp = self.forward_request(req)
        set_info_cache(self._app, req.environ, self.account,
                self.container, resp)

        # Enchance the request with ACL-related stuff before trying to deny.
        req.acl = resp.headers.get('x-container-read')
        return self.try_deny(req) or resp

    @public
    def POST(self, req):
        clear_info_cache(self._app, req.environ, self.account, self.container)
        return self.try_deny(req) or self.clean_acls(req) or \
               self.forward_request(req)

    @public
    def PUT(self, req):
        clear_info_cache(self._app, req.environ, self.account, self.container)
        return self.try_deny(req) or self.clean_acls(req) or \
               self.forward_request(req)

    @public
    def DELETE(self, req):
        clear_info_cache(self._app, req.environ, self.account, self.container)
        return self.try_deny(req) or self.forward_request(req)


class ObjectController(BaseController):
    def GETorHEAD(self, req):
        resp = self.forward_request(req)
        # Enchance the request with ACL-related stuff before trying to deny.
        container_info = get_container_info(req.environ, self._app)
        try:
            req.acl = container_info['x-container-read']
        except (KeyError):
            pass
        return self.try_deny(req) or resp


class RgwiftApp(object):
    def __init__(self, conf):
        self.recheck_container_existence = \
            int(conf.get('recheck_container_existence', 60))
        self.recheck_account_existence = \
            int(conf.get('recheck_account_existence', 60))
        return

    def get_controller(self, path):
        path_elems = split_path(path, 1, 4, True)
        version, account, container, obj = path_elems

        if obj:
            return ObjectController(self, path_elems)
        elif container:
            return ContainerController(self, path_elems)
        elif account:
            return AccountController(self, path_elems)
        return None

    def get_handler(self, controller, req):
        try:
            handler = getattr(controller, req.method)
            getattr(handler, 'publicly_accessible')
        except AttributeError:
            allowed_methods = getattr(controller, 'allowed_methods', set())
            return HTTPMethodNotAllowed(
                request=req,
                headers={'Allow': ', '.join(allowed_methods)})
        else:
            return handler(req)

    @wsgify
    def __call__(self, req):
        try:
            controller = self.get_controller(req.path)
            wsgi_handler = self.get_handler(controller, req)
        except:
            raise
        else:
            # We need to return a WSGI callable which will be called
            # by wsgify decorator. It should handle HTTPExceptions
            # as well.
            return wsgi_handler


def app_factory(global_conf, **local_conf):
    conf = global_conf.copy()
    return RgwiftApp(conf)
