// Mostrar alerta flotante
function mostrarAlerta(mensaje, tipo='success') {
    // Validar tipo
    const tiposValidos = ['success', 'danger', 'warning', 'info'];
    if (!tiposValidos.includes(tipo)) {
        tipo = 'success';
    }
    
    let alerta = document.createElement('div');
    alerta.className = `alert alert-${tipo} alert-dismissible fade show position-fixed top-0 end-0 m-3 shadow-lg`;
    alerta.role = "alert";
    alerta.textContent = String(mensaje);
    
    let closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.className = 'btn-close';
    closeBtn.setAttribute('data-bs-dismiss', 'alert');
    alerta.appendChild(closeBtn);
    
    document.body.appendChild(alerta);
    setTimeout(() => { 
        if (alerta && alerta.parentNode) {
            alerta.remove();
        }
    }, 4000);
}

// Funciones de reportes
function actualizarReportes() {
    alert('Actualizando reportes...');
    window.location.reload();
}

function exportarPDF() {
    alert('Descargando PDF...');
    window.location.assign('/reportes/exportar/pdf/');
}

function exportarExcel() {
    alert('Descargando Excel...');
    window.location.assign('/reportes/exportar/excel/');
}

// Ejemplo: lanzar una alerta cuando cargue la página
document.addEventListener("DOMContentLoaded", () => {
    console.log("Panel cargado 🚀");
});
