from flask import Flask
from .config import Config
from .extensions import csrf, db, migrate


def create_app(config_object=None):
    app = Flask(__name__)
    app.config.from_object(config_object or Config)
    db.init_app(app); migrate.init_app(app, db); csrf.init_app(app)
    from .routes import bp
    app.register_blueprint(bp)
    @app.cli.command("seed")
    def seed():
        from .services import seed_app
        seed_app(app)
    return app
