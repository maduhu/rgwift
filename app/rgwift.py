from swift.common.swob import Request, Response, wsgify
from swift.common.utils import split_path, public
from swift.proxy.controllers.base import _set_info_cache

from wsgiproxy.exactproxy import proxy_exact_request as wsgi_proxy


class BaseController(object):
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
        new_env = req.environ.copy()
        new_env['wsgi.url_scheme'] = 'http'
        new_env['SERVER_PORT'] = 8000
        new_env['PATH_INFO'] = '/swift' + req.environ['PATH_INFO']
        return Request(new_env).get_response(wsgi_proxy)

    @public
    def GET(self, req):
        return self.try_deny(req) or self.forward_request(req)

    @public
    def HEAD(self, req):
        return self.try_deny(req) or self.forward_request(req)

    @public
    def POST(self, req):
        return self.try_deny(req) or self.forward_request(req)

    @public
    def PUT(self, req):
        return self.try_deny(req) or self.forward_request(req)

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
    pass


class ContainerController(BaseController):
    pass


class ObjectController(BaseController):
    pass


class RgwiftApp(object):
    def __init__(self, conf):
        self.recheck_container_existence = \
            int(conf.get('recheck_container_existence', 60))
        self.recheck_account_existence = \
            int(conf.get('recheck_account_existence', 60))
        return

    def get_controller(self, path):
        version, account, container, obj = split_path(path, 1, 4, True)

        if obj:
            return ObjectController()
        elif container:
            return ContainerController()
        elif account:
            return AccountController()
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
