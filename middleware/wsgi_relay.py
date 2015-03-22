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

    def cache_getorhead_resp(self, resp):
        pass

    def __call__(self, env, start_response):
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

        env['SERVER_PORT'] = 8000
        env['PATH_INFO'] = '/swift' + env['PATH_INFO']

        return wsgiproxy.exactproxy.proxy_exact_request(env, resp_handler)
 

def app_factory(global_conf, **local_conf):
    conf = global_conf.copy()
    return Application(conf)
