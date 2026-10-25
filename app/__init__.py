from flask import Flask
from config import Config
from app.extensions import db, oauth, migrate

def create_app(config_class=Config):
    app = Flask(__name__)
    
    # Cargar configuración desde config.py
    app.config.from_object(config_class)

    # 1. Inicializar extensiones con la app
    db.init_app(app)
    migrate.init_app(app, db)
    oauth.init_app(app)

    # 2. Registro de Blueprints (Rutas aisladas)
    # Se importan dentro de la función para garantizar que la app ya exista
    
    from app.blueprints.auth_bp import auth_bp
    from app.blueprints.admin_bp import admin_bp
    from app.blueprints.delegado_bp import delegado_bp
    # from app.blueprints.futbol_bp import futbol_bp
    # from app.blueprints.yeimi_bp import yeimi_bp
    # from app.blueprints.fifa27_bp import fifa27_bp
    from app.blueprints.main_bp import main_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(delegado_bp, url_prefix='/delegado')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    # app.register_blueprint(futbol_bp, url_prefix='/futbol')
    # app.register_blueprint(yeimi_bp, url_prefix='/yeimi')
    # app.register_blueprint(fifa27_bp, url_prefix='/fifa27')
    app.register_blueprint(main_bp)

    # Ruta de validación para confirmar que el servidor levanta correctamente
    
    return app