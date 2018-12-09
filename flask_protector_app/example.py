from flask import (
    Flask,
    Blueprint,
    request,
    redirect,
)
import os
from __init__ import FlaskProtectorApp, setup_routes

###################################
# Set up protected (main) app
###################################

class MyProtectedApp(Flask):
    pass

protected_app = MyProtectedApp('HelloWorldApp')

@protected_app.route('/logout', methods=['GET', 'POST'])
def logout():
    response = redirect('/login')
    set_logged_in = request.environ['flask_protector_app.set_logged_in']
    set_logged_in(False, response, None)
    return response

@protected_app.route('/')
def foo():
    get_logged_in_as = request.environ['flask_protector_app.get_logged_in_as']
    username = get_logged_in_as()
    return '''
        Welcome to the protected application. Your logged in username is %s.
        <div>
            Perhaps you would like to <a href="/logout">log out</a>?
        </div>
    ''' % username

dirpath = os.path.dirname(os.path.abspath(__file__))

###################################
# Set up protector (wrapper) app
###################################

class MyFlaskProtectorApp(FlaskProtectorApp):
    def verify_login(self, username, password, session=None):
        return password == 'pw'

protector_app = MyFlaskProtectorApp(
    protected_app, # the app we want to wrap
    'example'
)

protector_app.config['SECRET_KEY'] = 'the wise will change this'
protector_app.config['SESSION_COOKIE_PATH'] = '/'
#protector_app.config['SESSION_COOKIE_DOMAIN'] = 'yourdomain.com'

protector_app.config['APP_NAME'] = 'My Passport' # For display in the title

# Cookie settings
protector_app.config['LOGIN_STATUS_COOKIE_NAME'] = 'passport_sso_logged_in'
protector_app.config['LOGIN_USERNAME_COOKIE_NAME'] = 'passport_sso_logged_in_as'

setup_routes(protector_app)

print('running app')
protector_app.run(port=3000, debug=True, host='0.0.0.0')
