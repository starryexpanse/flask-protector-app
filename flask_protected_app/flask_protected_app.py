from functools import partial
#from http.cookies import BaseCookie
from Cookie import BaseCookie
from werkzeug.http import parse_cookie
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
from flask.ctx import RequestContext
import os
import sys
from flask.globals import _request_ctx_stack
from jinja2 import TemplateNotFound

class ProtectorRequestContext(RequestContext):
    def __init__(self, protector_app, app, environ):
        RequestContext.__init__(self, app, environ)

class FlaskProtectorApp(Flask):
    session_cookie_name = 'flaskprotectorappsession'

    def __init__(self, wrapped_app, *args, **kwargs):
        Flask.__init__(self, *args, **kwargs)
        self.wrapped_app = wrapped_app

    def verify_login(self, username, password, session=None):
        return password == 'pw'
        raise NotImplementedError('verify_login not defined')

    def set_logged_in(self, session, logged_in, response, username=None):
        session[self.config['LOGIN_STATUS_COOKIE_NAME']] = logged_in
        session[self.config['LOGIN_USERNAME_COOKIE_NAME']] = username
        session.permanent = True
        self.session_interface.save_session(self, session, response)
    
    def get_logged_in(self, session):
        return session.get(self.config['LOGIN_STATUS_COOKIE_NAME'], False)
    
    def get_logged_in_as(self, session):
        return session.get(self.config['LOGIN_USERNAME_COOKIE_NAME'], None)

    def handle_exception(self, e):
        return self.wrapped_app.handle_exception(e)

    def should_ignore_error(self, error):
        return False

    def wsgi_app(self, environ, start_response):
        ctx = self.request_context(environ)
        ctx.push()

        req = ctx.request
        charset = req.charset

        session = ctx.session # self.session_interface.open_session(self, req)
        # ctx.session = session
        inner_ctx = ctx
        should_proxy = self.get_logged_in(session) 

        environ['flask_protector_app.verify_login'] = partial(self.verify_login, session=session)
        environ['flask_protector_app.set_logged_in'] = partial(self.set_logged_in, session)
        environ['flask_protector_app.get_logged_in'] = partial(self.get_logged_in, session)
        environ['flask_protector_app.get_logged_in_as'] = partial(self.get_logged_in_as, session)

        new_environ = environ.copy()

        if should_proxy:
            if 'HTTP_COOKIE' in new_environ:
                parsed_cookie = BaseCookie()
                parsed_cookie.load(environ['HTTP_COOKIE']) # TODO encoding?
                del parsed_cookie['flaskprotectorappsession']
                new_environ['HTTP_COOKIE'] = str(parsed_cookie).partition('Set-Cookie: ')[2]

            inner_ctx = type(ctx)(
                self.wrapped_app,
                environ=new_environ,
                request=self.wrapped_app.request_class(new_environ)
            )
        
        error = None
        try:
            response = None
            try:
                if should_proxy:
                   inner_ctx.push()
                if not should_proxy:
                    response = self.full_dispatch_request()
            except Exception as e:
                error = e
                response = self.handle_exception(e)
            except:
                error = sys.exc_info()[1]
                raise
            if response is not None:
                return response(new_environ, start_response)
        finally:
            if self.should_ignore_error(error):
                error = None
            if should_proxy:
                result = self.wrapped_app.wsgi_app(new_environ, start_response)
                inner_ctx.auto_pop(error)
                return result
            ctx.auto_pop(error)

class MyProtectedApp(Flask):
    pass


protected_app = MyProtectedApp('Protie')

@protected_app.route('/logout', methods=['GET', 'POST'])
def logout():
    response = redirect('/login')
    set_logged_in = request.environ['flask_protector_app.set_logged_in']
    set_logged_in(False, response, None)
    return response

@protected_app.route('/', defaults={'path': ''})
@protected_app.route('/<path:path>')
def hello(**kwargs):
    get_logged_in_as = request.environ['flask_protector_app.get_logged_in_as']
    username = get_logged_in_as()
    return 'hello werld : ) yer in, %s' % username

@protected_app.route('/foo')
def foo():
    return 'BAR.'

dirpath = os.path.dirname(os.path.abspath(__file__))

app = FlaskProtectorApp(protected_app, __name__)
app.config.from_pyfile(os.path.join(dirpath, 'config.py'))

@app.context_processor
def inject_app_name():
    return {
        'app_name': app.config['APP_NAME']
    }

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        verify_login = request.environ['flask_protector_app.verify_login']
        get_logged_in_as = request.environ['flask_protector_app.get_logged_in_as']
        set_logged_in = request.environ['flask_protector_app.set_logged_in']

        username = request.form["username"]
        password = request.form["password"]

        if (verify_login(username, password)):
            response = Response(render_template('redirect.html'))
            set_logged_in(True, response, username)
            return response

        return render_template('login.html') # TODO failed message
    else:
        return render_template('login.html')



@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def login_redirect(**kwargs):
    return redirect(url_for('login'))

app.run(port=3000, debug=True, host='0.0.0.0')
