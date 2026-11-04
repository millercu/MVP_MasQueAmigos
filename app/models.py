import secrets
from app.extensions import db
from datetime import datetime, date, timedelta

class Torneo(db.Model):
    __tablename__ = 'torneo'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False) # Ej: "Torneo Noviembre 2026"
    estado = db.Column(db.String(20), default='Activo') # 'Activo' o 'Finalizado'
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    categorias = db.relationship('Categoria', backref='torneo', cascade='all, delete-orphan')
    documentos = db.relationship('DocumentoTorneo', backref='torneo', cascade='all, delete-orphan')

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

    reset_token = db.Column(db.String(100), unique=True, nullable=True)
    token_expiracion = db.Column(db.DateTime, nullable=True)

    def generar_token_recuperacion(self):
        self.reset_token = secrets.token_urlsafe(32)
        self.token_expiracion = datetime.utcnow() + timedelta(hours=1)
        return self.reset_token


class Categoria(db.Model):
    __tablename__ = 'categoria'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    torneo_id = db.Column(db.Integer, db.ForeignKey('torneo.id'), nullable=True) # Vinculación


    # Restaura solo esta línea para recuperar la categoría de los equipos:
    equipos = db.relationship('Equipo', backref='categoria', cascade='all, delete-orphan')

class Equipo(db.Model):
    __tablename__ = 'equipo'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False, unique=True)
    escudo = db.Column(db.String(255), nullable=True, default='default_escudo.png')    
    # Llave foránea para la categoría
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'), nullable=True)
    
    # Llave foránea para conectar con el Usuario (Delegado) y hacer funcionar tu rel. 'delegado_asignado'
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
    
    # Relación con jugadores (ya la tienes)
    jugadores = db.relationship('Jugador', backref='equipo', lazy=True, cascade='all, delete-orphan')


class Carrusel(db.Model):
    __tablename__ = 'carrusel'
    id = db.Column(db.Integer, primary_key=True)
    imagen = db.Column(db.String(255), nullable=False)
    orden = db.Column(db.Integer, default=0)



class Patrocinador(db.Model):
    __tablename__ = 'patrocinador'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    logo = db.Column(db.String(255), nullable=False)
    enlace = db.Column(db.String(255), nullable=False)



class Jugador(db.Model):
    __tablename__ = 'jugador'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    tipo_documento = db.Column(db.String(10), nullable=True, default='CC')
    documento = db.Column(db.String(30), nullable=False)
    eps = db.Column(db.String(50), nullable=True)
    rol_equipo = db.Column(db.String(30), nullable=False) # Deportista, DT, etc.
    fecha_inicio = db.Column(db.String(20), nullable=True)
    fecha_fin = db.Column(db.String(20), nullable=True)
    posicion = db.Column(db.String(30), nullable=True)
    foto = db.Column(db.String(255), nullable=True)
    
    # CAMBIO IMPORTANTE: Lo pasamos a nullable=True para permitir jugadores "Libres"
    equipo_id = db.Column(db.Integer, db.ForeignKey('equipo.id'), nullable=True)



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


class Partido(db.Model):
    __tablename__ = 'partido'
    id = db.Column(db.Integer, primary_key=True)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'), nullable=False)

    categoria = db.relationship('Categoria', foreign_keys=[categoria_id])
    
    # Fase: 'Repechaje', 'Semifinal 1', 'Semifinal 2', 'Tercer Puesto', 'Final'
    fase = db.Column(db.String(50), nullable=False) 
    
    # Equipos (Pueden ser nulos inicialmente si están esperando rival)
    equipo_local_id = db.Column(db.Integer, db.ForeignKey('equipo.id'), nullable=True)
    equipo_visitante_id = db.Column(db.Integer, db.ForeignKey('equipo.id'), nullable=True)
    
    # Textos temporales (Ej: "Ganador Semifinal 1", "Perdedor Semifinal 2")
    info_local = db.Column(db.String(100), nullable=True)
    info_visitante = db.Column(db.String(100), nullable=True)
    
    fecha = db.Column(db.String(20), nullable=True) # El admin la asigna después
    hora = db.Column(db.String(10), nullable=True)
    cancha = db.Column(db.String(100), nullable=True)
    
    estado = db.Column(db.String(20), default='Pendiente') # Pendiente, Jugado
    goles_local = db.Column(db.Integer, default=0)
    goles_visitante = db.Column(db.Integer, default=0)
    penales_local = db.Column(db.Integer, nullable=True)
    penales_visitante = db.Column(db.Integer, nullable=True)
    
    # LLAVES DE PROGRESIÓN AUTOMÁTICA
    partido_siguiente_ganador_id = db.Column(db.Integer, db.ForeignKey('partido.id'), nullable=True)
    partido_siguiente_perdedor_id = db.Column(db.Integer, db.ForeignKey('partido.id'), nullable=True)

    equipo_local = db.relationship('Equipo', foreign_keys=[equipo_local_id])
    equipo_visitante = db.relationship('Equipo', foreign_keys=[equipo_visitante_id])


class EstadisticaPartido(db.Model):
    __tablename__ = 'estadistica_partido'
    id = db.Column(db.Integer, primary_key=True)
    partido_id = db.Column(db.Integer, db.ForeignKey('partido.id'), nullable=False)
    jugador_id = db.Column(db.Integer, db.ForeignKey('jugador.id'), nullable=False)
    equipo_id = db.Column(db.Integer, db.ForeignKey('equipo.id'), nullable=False)
    
    goles = db.Column(db.Integer, default=0)
    asistencias = db.Column(db.Integer, default=0)
    amarillas = db.Column(db.Integer, default=0)
    rojas = db.Column(db.Integer, default=0)
    
    partido = db.relationship('Partido', backref=db.backref('estadisticas', cascade='all, delete-orphan'))
    jugador = db.relationship('Jugador', backref='estadisticas')
    equipo = db.relationship('Equipo', foreign_keys=[equipo_id])


class DocumentoTorneo(db.Model):
    __tablename__ = 'documento_torneo'
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(150), nullable=False)
    archivo = db.Column(db.String(255), nullable=False)
    subido_por_rol = db.Column(db.String(50), nullable=False) # 'admin' o 'delegado'
    torneo_id = db.Column(db.Integer, db.ForeignKey('torneo.id'), nullable=False)
    equipo_id = db.Column(db.Integer, db.ForeignKey('equipo.id'), nullable=True) # Si lo sube el delegado
    fecha_subida = db.Column(db.DateTime, default=datetime.utcnow)
    
    equipo = db.relationship('Equipo', backref='documentos')



class PodioEsports(db.Model):
    __tablename__ = 'podio_esports'
    id = db.Column(db.Integer, primary_key=True)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'), nullable=False, unique=True)
    campeon = db.Column(db.String(100), nullable=True)
    subcampeon = db.Column(db.String(100), nullable=True)
    tercer_puesto = db.Column(db.String(100), nullable=True)
    
    # Relación para acceder fácil desde la categoría
    categoria = db.relationship('Categoria', backref=db.backref('podio', uselist=False, cascade='all, delete-orphan'))



class PodioYeimi(db.Model):
    __tablename__ = 'podio_yeimi'
    id = db.Column(db.Integer, primary_key=True)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'), nullable=False, unique=True)
    campeon_id = db.Column(db.Integer, db.ForeignKey('equipo.id'), nullable=True)
    subcampeon_id = db.Column(db.Integer, db.ForeignKey('equipo.id'), nullable=True)
    tercer_puesto_id = db.Column(db.Integer, db.ForeignKey('equipo.id'), nullable=True)
    
    categoria = db.relationship('Categoria', backref=db.backref('podio_yeimi', uselist=False, cascade='all, delete-orphan'))
    campeon = db.relationship('Equipo', foreign_keys=[campeon_id])
    subcampeon = db.relationship('Equipo', foreign_keys=[subcampeon_id])
    tercer_puesto = db.relationship('Equipo', foreign_keys=[tercer_puesto_id])