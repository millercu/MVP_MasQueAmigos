document.addEventListener("DOMContentLoaded", function() {
    // Buscador instantáneo y exacto
    const buscador = document.getElementById("buscadorMercado");
    if (buscador) {
        buscador.addEventListener("input", function() { 
            let filtro = this.value.toLowerCase().trim();
            let filas = document.querySelectorAll("#tablaMercado tbody tr");
            
            filas.forEach(fila => {
                let textoFila = "";
                
                // Extraemos SOLO el texto de Nombre(0), Posición(1), Equipo(2) y Cláusula(3)
                for (let i = 0; i < 4; i++) {
                    if (fila.cells[i]) {
                        textoFila += fila.cells[i].textContent.toLowerCase() + " ";
                    }
                }
                
                if (textoFila.includes(filtro)) {
                    fila.style.display = ""; 
                } else {
                    fila.style.display = "none"; 
                }
            });
        });
    }

    // Temporizador para desaparecer mensajes Flash
    setTimeout(function() {
        let alertas = document.querySelectorAll(".alert-dismissible");
        alertas.forEach(alerta => {
            if (typeof bootstrap !== "undefined") {
                let bsAlert = new bootstrap.Alert(alerta);
                bsAlert.close();
            } else {
                alerta.remove();
            }
        });
    }, 4000);
});