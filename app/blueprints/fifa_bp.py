from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.extensions import db
from app.models import Torneo, Categoria, Equipo, PodioEsports

# Respetando estrictamente el nombre que me indicaste
fifa_bp = Blueprint('fifa', __name__, template_folder='templates/fifa')

@fifa_bp.route('/panel')
def panel():
    if session.get('user_rol') != 'admin':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('main.index'))
        
    torneo_activo = Torneo.query.filter_by(estado='Activo').first()
    
    # FILTRO ESTRICTO: Solo traemos las categorías cuyo nombre contenga "esports" o "e-sports"
    if torneo_activo:
        categorias = Categoria.query.filter(
            Categoria.torneo_id == torneo_activo.id,
            Categoria.nombre.ilike('%easports%')
        ).all()
    else:
        categorias = []
    
    return render_template('fifa/panelesports.html', 
                           torneo_activo=torneo_activo,
                           categorias=categorias)

@fifa_bp.route('/guardar-podio/<int:categoria_id>', methods=['POST'])
def guardar_podio(categoria_id):
    if session.get('user_rol') != 'admin':
        return redirect(url_for('main.index'))
        
    categoria = Categoria.query.get_or_404(categoria_id)
    
    # Buscamos o creamos el registro del podio para esta categoría
    podio = PodioEsports.query.filter_by(categoria_id=categoria.id).first()
    if not podio:
        podio = PodioEsports(categoria_id=categoria.id)
        db.session.add(podio)
        
    podio.campeon = request.form.get('campeon')
    podio.subcampeon = request.form.get('subcampeon')
    podio.tercer_puesto = request.form.get('tercer_puesto')
    
    db.session.commit()
    flash(f'Podio guardado con éxito para la categoría {categoria.nombre}.', 'success')
    return redirect(url_for('fifa.panel'))


@fifa_bp.route('/eliminar-podio/<int:categoria_id>', methods=['POST'])
def eliminar_podio(categoria_id):
    if session.get('user_rol') != 'admin':
        return redirect(url_for('main.index'))
        
    podio = PodioEsports.query.filter_by(categoria_id=categoria_id).first()
    if podio:
        db.session.delete(podio)
        db.session.commit()
        flash('El podio de esta categoría ha sido eliminado correctamente.', 'info')
    
    return redirect(url_for('fifa.panel'))