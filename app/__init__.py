from flask import Flask
from app.routes import main
from settings import config
import os

def create_app(config_class=config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    

    app.register_blueprint(main)
    return app

