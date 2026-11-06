from flask import Flask, render_template
from config import Config
from app.extensions import db, oauth, migrate, mail



def create_app(config_class=Config):
    app = Flask(__name__)
    
    # Cargar configuración desde config.py
    app.config.from_object(config_class)

    # 1. Inicializar extensiones con la app
    db.init_app(app)
    migrate.init_app(app, db)
    oauth.init_app(app)

    mail.init_app(app)

    # 2. Registro de Blueprints (Rutas aisladas)
    # Se importan dentro de la función para garantizar que la app ya exista
    
    from app.blueprints.auth_bp import auth_bp
    from app.blueprints.admin_bp import admin_bp
    from app.blueprints.delegado_bp import delegado_bp
    # from app.blueprints.futbol_bp import futbol_bp
    from app.blueprints.yeimi_bp import yeimi_bp
    from app.blueprints.fifa_bp import fifa_bp
    from app.blueprints.main_bp import main_bp

    from flask_talisman import Talisman

    from flask_wtf.csrf import CSRFProtect
    csrf = CSRFProtect()

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(delegado_bp, url_prefix='/delegado')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    # app.register_blueprint(futbol_bp, url_prefix='/futbol')
    app.register_blueprint(yeimi_bp, url_prefix='/yeimi')
    app.register_blueprint(fifa_bp, url_prefix='/fifa')
    app.register_blueprint(main_bp)

    app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # Límite de 5 MB por archivo

    app.config['SESSION_COOKIE_SECURE'] = True      # Solo transmite cookies por HTTPS
    app.config['SESSION_COOKIE_HTTPONLY'] = True    # Evita que el JavaScript acceda a la cookie (mitiga ataques XSS)
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'   # Protege la cookie contra envíos cruzados


    @app.errorhandler(404)
    def pagina_no_encontrada(e):
        return render_template('errores/404.html'), 404

    @app.errorhandler(500)
    def error_interno_servidor(e):
        return render_template('errores/500.html'), 500

    @app.errorhandler(403)
    def acceso_prohibido(e):
        return render_template('errores/403.html'), 403

    csrf.init_app(app)
    Talisman(app, content_security_policy=None)

    # Ruta de validación para confirmar que el servidor levanta correctamente
    
    return app