from app import create_app

# Instanciamos la aplicación usando el patrón Application Factory
app = create_app()

if __name__ == '__main__':
    # debug=True permite ver los cambios en tiempo real mientras desarrollamos
    app.run(debug=True, port=5000)