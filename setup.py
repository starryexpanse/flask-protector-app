from setuptools import setup

setup(name='flask_protector_app',
      version='1.0.9',
      description='A Flask app to wrap other Flask apps, providing a login layer',
      url='http://github.com/starryexpanse/flask-protector-app',
      author='Philip Peterson',
      author_email='pc.peterso@gmail.com',
      license='MIT',
      packages=['flask_protector_app'],
      include_package_data=True,
      classifiers=(
           'Development Status :: 1 - Planning',
           'Environment :: Web Environment',
           'Framework :: Flask',
           'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
           'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
      ),
      install_requires=[
            'flask>=1.0.2',
            'jinja2'
      ],
      zip_safe=False)
