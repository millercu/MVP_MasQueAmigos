from flask import Blueprint, render_template
from app.models import Traspaso, Configuracion, Categoria, Partido

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
    # Obtenemos todas las categorías con sus equipos relacionados
    categorias = Categoria.query.all()
    partidos_jugados = Partido.query.filter_by(estado='Jugado').all()
    return render_template('index.html', categorias=categorias, partidos_jugados=partidos_jugados)