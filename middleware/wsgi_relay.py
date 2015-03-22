import wsgiproxy.app
import wsgiproxy.exactproxy
import sys

def druk(s):
    with open('/tmp/zupa', 'a') as f:
        f.write(s + "\n")

class Application(object):
    def __init__(self, conf):
        pass
 
    def __call__(self, env, start_response):
        env['SERVER_PORT'] = 8000
        env['PATH_INFO'] = '/swift' + env['PATH_INFO']
        return wsgiproxy.exactproxy.proxy_exact_request(env, start_response)
 

def app_factory(global_conf, **local_conf):
    conf = global_conf.copy()
    return Application(conf)
