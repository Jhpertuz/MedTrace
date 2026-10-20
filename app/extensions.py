from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

#! Estas extensiones se crean sin una aplicación y se conectan en create_app().
db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
