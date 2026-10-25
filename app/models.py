from app.extensions import db
from datetime import datetime, date

class Usuario(db.Model):
    __tablename__ = 'usuario'
    
    id = db.Column(db.Integer, primary_key=True)
    nombres = db.Column(db.String(120), nullable=False)
    tipo_documento = db.Column(db.String(10), nullable=True, default='CC') # <-- NUEVO
    documento = db.Column(db.String(30), unique=True, index=True, nullable=False)
    telefono = db.Column(db.String(20), nullable=False)
    fecha_nacimiento = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    rol = db.Column(db.String(20), default='usuario', nullable=False)
    
    equipo = db.relationship('Equipo', backref='delegado_asignado', uselist=False)


class Categoria(db.Model):
    __tablename__ = 'categoria'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    
    # Relación con equipos
    equipos = db.relationship('Equipo', backref='categoria', lazy=True, cascade='all, delete-orphan')

class Equipo(db.Model):
    __tablename__ = 'equipo'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False, unique=True)
    
    # Llave foránea para la categoría
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'), nullable=True)
    
    # Llave foránea para conectar con el Usuario (Delegado) y hacer funcionar tu rel. 'delegado_asignado'
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
    
    # Relación con jugadores (ya la tienes)
    jugadores = db.relationship('Jugador', backref='equipo_asociado', lazy=True, cascade='all, delete-orphan')

class Jugador(db.Model):
    __tablename__ = 'jugador'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    documento = db.Column(db.String(30), nullable=False)
    eps = db.Column(db.String(50), nullable=True)
    rol_equipo = db.Column(db.String(30), nullable=False) # Deportista, DT, etc.
    fecha_inicio = db.Column(db.String(20), nullable=True)
    fecha_fin = db.Column(db.String(20), nullable=True)
    posicion = db.Column(db.String(30), nullable=True)
    
    # CAMBIO IMPORTANTE: Lo pasamos a nullable=True para permitir jugadores "Libres"
    equipo_id = db.Column(db.Integer, db.ForeignKey('equipo.id'), nullable=True)

    equipo = db.relationship('Equipo', backref=db.backref('jugadores_rel', lazy=True))
    
    # NUEVOS CAMPOS: Para dinero y estado en el mercado
    clausula_rescision = db.Column(db.Float, default=0.0)
    estado_fichaje = db.Column(db.String(20), default='Activo') # Activo, Libre, Prestamo

# Ampliamos tu clase Traspaso respetando tu lógica y estados
class Traspaso(db.Model):
    __tablename__ = 'traspaso'
    
    id = db.Column(db.Integer, primary_key=True)
    jugador_id = db.Column(db.Integer, db.ForeignKey('jugador.id'), nullable=False)
    
    # Origen ahora es nullable=True por si fichan a un jugador Libre (sin equipo previo)
    equipo_origen_id = db.Column(db.Integer, db.ForeignKey('equipo.id'), nullable=True)
    equipo_destino_id = db.Column(db.Integer, db.ForeignKey('equipo.id'), nullable=False)
    
    # Tu estado actual (añadiremos "Contraoferta" en la lógica)
    estado = db.Column(db.String(30), default='Pendiente') 
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow)

    # NUEVOS CAMPOS: Para la negociación (dinero, tiempo, intercambio)
    tipo = db.Column(db.String(20), nullable=True) # Compra, Prestamo, Libre
    monto = db.Column(db.Float, default=0.0)
    nuevo_fecha_fin = db.Column(db.String(20), nullable=True) # Hasta cuándo se le contrata
    jugador_intercambio_id = db.Column(db.Integer, db.ForeignKey('jugador.id'), nullable=True)
    mensaje_negociacion = db.Column(db.Text, nullable=True)
    
    # Relaciones para usarlas fácil en el HTML (equipo.nombre, jugador.nombre, etc.)
    jugador = db.relationship('Jugador', foreign_keys=[jugador_id])
    jugador_intercambio = db.relationship('Jugador', foreign_keys=[jugador_intercambio_id])
    equipo_origen = db.relationship('Equipo', foreign_keys=[equipo_origen_id])
    equipo_destino = db.relationship('Equipo', foreign_keys=[equipo_destino_id])


# NUEVO MODELO: Control global del torneo por el Admin
class Configuracion(db.Model):
    __tablename__ = 'configuracion'
    id = db.Column(db.Integer, primary_key=True)
    mercado_abierto = db.Column(db.Boolean, default=False)