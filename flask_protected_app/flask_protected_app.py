from flask import (
    Flask,
    Blueprint,
    render_template,
    abort,
    request,
    Response,
    redirect,
    session,
    url_for
)
import os
import sys
from flask.globals import _request_ctx_stack
from jinja2 import TemplateNotFound

class StarrySsoFlask(Flask):
    def __init__(self, wrapped_app, *args, **kwargs):
        Flask.__init__(self, *args, **kwargs)
        self.wrapped_app = wrapped_app

    def handle_exception(self, e):
        return self.wrapped_app.handle_exception(e)

    def should_ignore_error(self, error):
        return False
    
    def prepare_proxy(self, req_context):
        req = req_context.request

        session = self.session_interface.open_session(self, req)
        if session is None:
            return False

        return session.get(self.config['LOGIN_STATUS_COOKIE_NAME'], False)

    def wsgi_app(self, environ, start_response):
        ctx = self.request_context(environ)
        error = None
        should_proxy = False

        try:
            response = None
            try:
                ctx.push()
                should_proxy = self.prepare_proxy(ctx)
                if not should_proxy:
                    response = self.full_dispatch_request()
            except Exception as e:
                error = e
                response = self.handle_exception(e)
            except:
                error = sys.exc_info()[1]
                raise
            if response is not None:
                return response(environ, start_response)
        finally:
            if should_proxy:
                return self.wrapped_app.wsgi_app(environ, start_response)
            else:
                if self.should_ignore_error(error):
                    error = None
                ctx.auto_pop(error)
        
        response = self.full_dispatch_request()

class MyProtectedApp(Flask):
    pass

protected_app = MyProtectedApp('Protie')
@protected_app.route('/', defaults={'path': ''})
@protected_app.route('/<path:path>')
def hello(**kwargs):
    return 'hello werld : ) yer in'

@protected_app.route('/foo')
def foo():
    return 'BAR.'

dirpath = os.path.dirname(os.path.abspath(__file__))

app = StarrySsoFlask(protected_app, __name__)
app.config.from_pyfile(os.path.join(dirpath, 'config.py'))

@app.context_processor
def inject_app_name():
    return {
        'app_name': app.config['APP_NAME']
    }

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session[app.config['LOGIN_STATUS_COOKIE_NAME']] = True
        session.permanent = True
        response = Response(render_template('redirect.html'))
        app.save_session(session, response)

        return response
    else:
        return render_template('login.html')

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def login_redirect(**kwargs):
    return redirect(url_for('login'))

app.run(port=3000, debug=True, host='0.0.0.0')
