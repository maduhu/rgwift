import wsgiproxy.app
import wsgiproxy.exactproxy
import sys

from swift.common.swob import Request, Response, wsgify
from swift.common.utils import public
from swift.proxy.controllers.base import _set_info_cache


class BaseController(object):
    pass


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
            return ObjectController
        else if container:
            return ContainerController
        else if account:
            return AccountController
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
            # We need to return wsgi callable which will be called
            # in wsgify decorator. It should handle HTTPException's
            # as well.
            return wsgi_handler


def app_factory(global_conf, **local_conf):
    conf = global_conf.copy()
    return Application(conf)
