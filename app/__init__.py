from flask import Flask
from .config import Config
from .extensions import csrf, db, migrate


#! Construye la aplicación Flask, carga la configuración, conecta la base de
#! datos y registra las rutas y el comando de carga de datos iniciales.
def create_app(config_object=None):
    app = Flask(__name__)
    app.config.from_object(config_object or Config)
    db.init_app(app); migrate.init_app(app, db); csrf.init_app(app)
    from .routes import bp
    app.register_blueprint(bp)
    #! Permite ejecutar "flask seed" para crear el usuario y equipos de demo.
    @app.cli.command("seed")
    def seed():
        from .services import seed_app
        seed_app(app)
    return app
