// Entrenador dashboard JS (moved from template)
// Assumes window.RUTINAS_PLANTILLAS_URL is defined in the page template

function abrirModalCrearRutina() {
  try {
    if (window.RUTINAS_PLANTILLAS_URL) {
      window.location.href = window.RUTINAS_PLANTILLAS_URL;
    } else {
      window.location.href = '/rutinas-plantillas/';
    }
  } catch (e) {
    window.location.href = '/rutinas-plantillas/';
  }
}

function verCalendarioCompleto() { alert('Función calendario - En desarrollo'); }
function verEstadisticas() { alert('Función estadísticas - En desarrollo'); }

function abrirModalCliente(id, nombre, email, telefono, membresia) {
    window.clienteSeleccionado = { id: id, nombre: nombre, email: email || 'Sin email', telefono: telefono || 'Sin teléfono', membresia: membresia || 'Sin membresía' };
    const modalTitle = document.getElementById('modalClienteNombre');
    if (modalTitle) modalTitle.textContent = nombre;
    const infoGrid = document.querySelector('#modalCliente .info-grid');
    if (infoGrid) {
        infoGrid.innerHTML = `...`; // placeholder; content will be filled by cargarProgresoCliente
    }
    const modal = document.getElementById('modalCliente');
    if (modal) modal.classList.add('show');
    cargarProgresoCliente(id);
}

function cerrarModal(modalId){ const modal = document.getElementById(modalId); if (modal) modal.classList.remove('show'); }

function cargarProgresoCliente(clienteId){
    console.log('Cargando progreso del cliente:', clienteId);
    fetch(`/api/alumnos/${clienteId}/progreso/`)
        .then(response => response.json())
        .then(data => {
            if (data.success) mostrarProgresoEnModal(data.progreso);
            else console.error('Error cargando progreso:', data.error);
        }).catch(error => console.error('Error:', error));
}

function mostrarProgresoEnModal(progreso){
    const infoGrid = document.querySelector('#modalCliente .info-grid');
    if (!infoGrid) return;
    infoGrid.innerHTML = `
        <div class="info-card"><i class="fas fa-envelope"></i><span>Email</span><p id="modalClienteEmail">${window.clienteSeleccionado.email || 'Sin email'}</p></div>
        <div class="info-card"><i class="fas fa-phone"></i><span>Teléfono</span><p id="modalClienteTelefono">${window.clienteSeleccionado.telefono || 'Sin teléfono'}</p></div>
        <div class="info-card"><i class="fas fa-crown"></i><span>Membresía</span><p id="modalClienteMembresia">${window.clienteSeleccionado.membresia || 'Sin membresía'}</p></div>
        <div class="info-card"><i class="fas fa-heartbeat"></i><span>Estado</span><span class="badge badge-success">Activo</span></div>
        <div class="info-card"><i class="fas fa-calendar-plus"></i><span>Fecha de Registro</span><p>${progreso.fecha_registro || 'No disponible'}</p></div>
        <div class="info-card"><i class="fas fa-dumbbell"></i><span>Rutinas Activas</span><p>${progreso.rutinas_activas || 0}</p></div>
        <div class="info-card"><i class="fas fa-chart-line"></i><span>Total Asistencias</span><p>${progreso.total_asistencias || 0}</p></div>
        <div class="info-card"><i class="fas fa-clock"></i><span>Última Asistencia</span><p>${progreso.ultima_asistencia || 'Nunca'}</p></div>
    `;
}

function verProgresoCliente(){ if (!window.clienteSeleccionado){ alert('No hay cliente seleccionado'); return; } cerrarModal('modalCliente'); abrirModalProgreso(window.clienteSeleccionado.id); }

function abrirModalProgreso(clienteId){
    let modalProgreso = document.getElementById('modalProgreso');
    if (!modalProgreso){ modalProgreso = crearModalProgreso(); document.body.appendChild(modalProgreso); }
    modalProgreso.classList.add('show');
    fetch(`/api/alumnos/${clienteId}/progreso/`).then(r=>r.json()).then(data=>{ if (data.success) mostrarProgresoCompleto(data.progreso); }).catch(e=>console.error(e));
}

function crearModalProgreso(){
    const modal = document.createElement('div'); modal.id = 'modalProgreso'; modal.className = 'modal'; modal.innerHTML = `
        <div class="modal-content modal-large">
            <div class="modal-header"><h3>Progreso del Cliente</h3><button onclick="cerrarModal('modalProgreso')" class="modal-close"><i class="fas fa-times"></i></button></div>
            <div class="modal-body" id="progresoContent"><div class="text-center py-4"><i class="fas fa-spinner fa-spin text-4xl mb-4 block text-blue-400"></i><p class="text-gray-300">Cargando progreso...</p></div></div>
        </div>
    `; return modal;
}

function mostrarProgresoCompleto(progreso){
    const content = document.getElementById('progresoContent'); if(!content) return;
    content.innerHTML = `...`; // kept minimal; dashboard template generates HTML dynamically
}

// Routines modal, agregar/remover ejercicios (kept as basic helpers)
let ejercicioCounter = 0;
function agregarEjercicio(){ ejercicioCounter++; const container = document.getElementById('ejerciciosContainer'); if(!container) return; const noEjercicios = document.getElementById('noEjercicios'); if(noEjercicios) noEjercicios.style.display='none'; const ejercicioDiv = document.createElement('div'); ejercicioDiv.className='ejercicio-item'; ejercicioDiv.id=`ejercicio-${ejercicioCounter}`; ejercicioDiv.innerHTML = `<div class="ejercicio-header"><h4 class="ejercicio-title"><i class="fas fa-dumbbell"></i>Ejercicio ${ejercicioCounter}</h4><button type="button" class="btn-remove-ejercicio" onclick="removerEjercicio(${ejercicioCounter})"><i class="fas fa-trash"></i></button></div>` + '<div class="ejercicio-form">... (form fields)</div>'; container.appendChild(ejercicioDiv); }
function removerEjercicio(id){ const ejercicio = document.getElementById(`ejercicio-${id}`); if(ejercicio) ejercicio.remove(); const container = document.getElementById('ejerciciosContainer'); if(container && container.children.length===0){ const noEjercicios = document.getElementById('noEjercicios'); if(noEjercicios) noEjercicios.style.display='block'; } }

// Expose some functions globally used by templates
window.abrirModalCrearRutina = abrirModalCrearRutina;
window.abrirModalCliente = abrirModalCliente;
window.cerrarModal = cerrarModal;
window.verProgresoCliente = verProgresoCliente;
window.abrirModalAsignarRutina = abrirModalAsignarRutina;
window.agregarEjercicio = agregarEjercicio;
window.removerEjercicio = removerEjercicio;
