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
    
    from app.blueprints.auth_bp import auth_bp
    from app.blueprints.admin_bp import admin_bp
    from app.blueprints.delegado_bp import delegado_bp
    from app.blueprints.yeimi_bp import yeimi_bp
    from app.blueprints.fifa_bp import fifa_bp
    from app.blueprints.main_bp import main_bp
    from app.models import Patrocinador
    from app.models import Patrocinador, Usuario
    from flask import session

    from flask_talisman import Talisman

    from flask_wtf.csrf import CSRFProtect
    csrf = CSRFProtect()

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(delegado_bp, url_prefix='/delegado')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(yeimi_bp, url_prefix='/yeimi')
    app.register_blueprint(fifa_bp, url_prefix='/fifa')
    app.register_blueprint(main_bp)

    app.config['MAX_CONTENT_LENGTH'] = 512 * 1024 

    app.config['SESSION_COOKIE_SECURE'] = True      
    app.config['SESSION_COOKIE_HTTPONLY'] = True    
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  

    @app.errorhandler(413)
    def error_archivo_grande(e):
         return render_template('errores/413.html'), 413


    @app.errorhandler(404)
    def pagina_no_encontrada(e):
        return render_template('errores/404.html'), 404

    @app.errorhandler(500)
    def error_interno_servidor(e):
        return render_template('errores/500.html'), 500

    @app.errorhandler(403)
    def acceso_prohibido(e):
        return render_template('errores/403.html'), 403

    @app.context_processor
    def inject_patrocinadores():
        patrocinadores = Patrocinador.query.all()
        return dict(patrocinadores=patrocinadores)

    @app.context_processor
    def inyectar_datos_globales():
        patrocinadores = Patrocinador.query.all()
        usuario_actual = None
        if 'user_id' in session:
            usuario_actual = Usuario.query.get(session['user_id'])
        return dict(patrocinadores=patrocinadores, usuario_actual=usuario_actual)

    csrf.init_app(app)
    Talisman(app, content_security_policy=None)

    
    return app