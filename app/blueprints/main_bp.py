from flask import Blueprint, render_template
from app.models import Traspaso, Configuracion

# Asegúrate de que esta línea exista (nombre del Blueprint)
main_bp = Blueprint('main', __name__)

@main_bp.route('/historial-fichajes')
def historial_fichajes():
    # Buscar todos los traspasos que ya fueron aprobados por el admin
    traspasos_completados = Traspaso.query.filter_by(estado='Completado').all()
    config = Configuracion.query.first()
    
    return render_template('fichajes.html', 
                           traspasos=traspasos_completados,
                           config=config)

@main_bp.route('/')
def index():
    return render_template('index.html') # O la vista principal que uses