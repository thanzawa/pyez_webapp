from pyez_flask import app
from jinja2 import Environment
env = Environment(cache_size=0)
app.run(host='0.0.0.0', debug=True, port=5050)
#app.run(host='127.0.0.1', debug=True, port=8080)
