from app import create_app
from app.extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Conectado a la base de datos de Flask...")
    try:
        # 1. Desactivar llaves foráneas temporalmente
        db.session.execute(text("PRAGMA foreign_keys=OFF;"))
        
        # 2. Renombrar la tabla de equipos actual
        db.session.execute(text("ALTER TABLE equipo RENAME TO equipo_old;"))
        db.session.commit()
        
        # 3. Recrear la tabla limpia desde models.py (sin la restricción UNIQUE)
        db.create_all()
        
        # 4. Copiar todos los equipos antiguos a la nueva tabla
        db.session.execute(text("INSERT INTO equipo SELECT * FROM equipo_old;"))
        db.session.commit()
        
        # 5. Eliminar la tabla vieja y reactivar llaves foráneas
        db.session.execute(text("DROP TABLE equipo_old;"))
        db.session.execute(text("PRAGMA foreign_keys=ON;"))
        db.session.commit()
        
        print("¡Éxito! La restricción UNIQUE de 'equipo.nombre' ha sido eliminada.")
    except Exception as e:
        db.session.rollback()
        print(f"Error al migrar la tabla: {e}")