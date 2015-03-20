class WsgiRelayMiddleware(object):
    def __init__(self, app, conf):
        self.app = app
 
    def __call__(self, env, start_response):
        return self.app(env, start_response)
 

def filter_factory(global_conf, **local_conf):
    conf = global_conf.copy()
    conf.update(local_conf)
 
    def wsgi_relay_filter(app):
        return WsgiRelayMiddleware(app, conf)
    return wsgi_relay_filter
