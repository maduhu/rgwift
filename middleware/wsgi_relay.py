import wsgiproxy.app
import wsgiproxy.exactproxy
import sys

from swift.common.swob import Request, Response
from swift.proxy.controllers.base import _set_info_cache

def druk(s):
    with open('/tmp/zupa', 'a') as f:
        f.write(s + "\n")

class Application(object):
    def __init__(self, conf):
        self.recheck_container_existence = \
            int(conf.get('recheck_container_existence', 60))
        self.recheck_account_existence = \
            int(conf.get('recheck_account_existence', 60))
        return

    def clean_acls(self, req):
        if 'swift.clean_acl' in req.environ:
            for header in ('x-container-read', 'x-container-write'):
                if header in req.headers:
                    try:
                        req.headers[header] = \
                            req.environ['swift.clean_acl'](header,
                                                           req.headers[header])
                    except ValueError as err:
                        return HTTPBadRequest(request=req, body=str(err))
        return None

    def cache_getorhead_resp(self, resp):
        pass

    def __call__(self, env, start_response):
        new_env = env.copy()
        req = Request(env)

        try:
            (version, account, container, obj) = req.split_path(2, 4, True)
        except ValueError:
            return self.app


        def relay_start_response(status, resp_headers, exc_info=None):
            resp = Response(status = status, headers = resp_headers,
                    request = req)
            _set_info_cache(self, env, account, container, resp)
            start_response(status, resp_headers, exc_info)

        resp_handler = start_response
        if req.method in ('GET', 'HEAD'):
            resp_handler = relay_start_response

        if 'swift.authorize' in req.environ:
            # We call authorize before the handler, always. If authorized,
            # we remove the swift.authorize hook so isn't ever called
            # again. If not authorized, we return the denial unless the
            # controller's method indicates it'd like to gather more
            # information and try again later.
            resp = req.environ['swift.authorize'](req)
            if not resp and not req.headers.get('X-Copy-From-Account') \
                    and not req.headers.get('Destination-Account'):
                pass
                # No resp means authorized, no delayed recheck required.
            else:
                # Response indicates denial, but we might delay the denial
                # and recheck later. If not delayed, return the error now.
                if container and req.method in ('GET', 'HEAD'):
                    pass
                else:
                    return resp(env, resp_handler)

        new_env['wsgi.url_scheme'] = 'http'
        new_env['SERVER_PORT'] = 8000
        new_env['PATH_INFO'] = '/swift' + env['PATH_INFO']

        error_response = None
        if req.method in ('PUT', 'POST'):
            error_response = self.clean_acls(req)

        new_req = Request(new_env)
        resp = new_req.get_response(wsgiproxy.exactproxy.proxy_exact_request)
        if container and req.method in ('GET', 'HEAD') and 'swift.authorize' in req.environ:
            if not obj:
                req.acl = resp.headers.get('x-container-read')
            else:
                req.acl = '.r:*'
            error_response = req.environ['swift.authorize'](req)

        return (error_response or resp)(new_env, resp_handler)
 

def app_factory(global_conf, **local_conf):
    conf = global_conf.copy()
    return Application(conf)
