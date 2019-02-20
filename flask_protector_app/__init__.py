try:
    from http.cookies import BaseCookie
except ImportError:
    from Cookie import BaseCookie

from functools import partial
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
from jinja2 import FileSystemLoader, ChoiceLoader, TemplateNotFound


template_dir = os.path.abspath(os.path.join(__file__, '..', 'templates'))

class FlaskProtectorApp(Flask):
    session_cookie_name = 'flaskprotectorappsession'

    def __init__(self, wrapped_app, *args, **kwargs):
        Flask.__init__(self, *args, **kwargs)
        self.wrapped_app = wrapped_app
        self.config['SESSION_COOKIE_SECURE'] = False
        self.jinja_loader = ChoiceLoader([
            self.jinja_loader,
            FileSystemLoader([
                template_dir
            ])
        )

    def verify_login(self, username, password, session=None):
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

        session = ctx.session
        inner_ctx = ctx
        should_proxy = self.get_logged_in(session) 

        environ['flask_protector_app.verify_login'] = partial(self.verify_login, session=session)
        environ['flask_protector_app.set_logged_in'] = partial(self.set_logged_in, session)
        environ['flask_protector_app.get_logged_in'] = partial(self.get_logged_in, session)
        environ['flask_protector_app.get_logged_in_as'] = partial(self.get_logged_in_as, session)

        new_environ = environ.copy()

        if should_proxy:
            if 'HTTP_COOKIE' in new_environ:
                # Scrub the environment of any trace of the protector's cookie,
                # because otherwise the inner app will see it and probably try
                # to send Set-Cookie headers to refresh the session, effectively undoing
                # any changes the protector wants to make to it.
                
                parsed_cookie = BaseCookie()
                parsed_cookie.load(environ['HTTP_COOKIE']) # TODO encoding?
                del parsed_cookie[self.session_cookie_name]
                stringified_cookie = str(parsed_cookie).partition('Set-Cookie: ')[2]
                if stringified_cookie:
                    new_environ['HTTP_COOKIE'] = stringified_cookie
                else:
                    del new_environ['HTTP_COOKIE']

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

def setup_routes(app):
    @app.context_processor
    def inject_app_name():
        return {
            'app_name': app.config.get('APP_NAME', None)
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
