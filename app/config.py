import os


#! Agrupa la configuración de Flask y obtiene secretos, base de datos y
#! credenciales iniciales desde variables de entorno cuando están disponibles.
class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "development-only-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///maintenance.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    INITIAL_ENGINEER_EMAIL = os.getenv("INITIAL_ENGINEER_EMAIL", "ingeniero@demo.local")
    INITIAL_ENGINEER_PASSWORD = os.getenv("INITIAL_ENGINEER_PASSWORD", "cambiar-para-demo")
