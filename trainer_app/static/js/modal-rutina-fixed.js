// Versión optimizada v3.0 - SOLO MANEJA MODAL, NO RENDERIZA
console.log('[modal-rutina-fixed] v3.0 cargado - Solo modal, sin renderizado');

// Variables globales
let ejerciciosTemporales = []; // Lista de ejercicios en el modal de creación
let ejerciciosEditar = []; // Lista de ejercicios en el modal de edición

// Funciones básicas
function mostrarToast(message, type = 'info') {
    console.log(`[${type}] ${message}`);
    
    const toast = document.createElement('div');
    toast.className = `fixed top-4 right-4 z-[9999] px-6 py-3 rounded-lg shadow-lg text-white ${
        type === 'success' ? 'bg-green-600' : 
        type === 'error' ? 'bg-red-600' : 
        'bg-blue-600'
    }`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function getCsrfToken() {
    if (window._csrfToken) return window._csrfToken;
    
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) {
        window._csrfToken = meta.getAttribute('content');
        return window._csrfToken;
    }
    
    const cookie = document.cookie.match(/csrftoken=([^;]+)/);
    if (cookie) {
        window._csrfToken = cookie[1];
        return window._csrfToken;
    }
    return '';
}

// ============= FUNCIONES DE CARGA Y RENDERIZADO (ACTIVAS) =============

// Cargar rutinas desde API
async function cargarRutinas() {
    console.log('[modal-rutina-fixed] Cargando rutinas desde API...');
    
    // Si ya están cargadas desde Django, no recargar
    if (window._rutinasYaCargadas && window.rutinas && window.rutinas.length > 0) {
        console.log('[modal-rutina-fixed] Rutinas ya cargadas desde Django, skip API');
        actualizarContadores();
        return;
    }
    
    try {
        const response = await fetch('/api/rutinas/', {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        // Normalizar datos
        if (Array.isArray(data)) {
            window.rutinas = data;
            window.rutinasData = data;
        } else if (data.rutinas && Array.isArray(data.rutinas)) {
            window.rutinas = data.rutinas;
            window.rutinasData = data.rutinas;
        } else {
            window.rutinas = [];
            window.rutinasData = [];
        }
        
        console.log('[modal-rutina-fixed] Cargadas', window.rutinas.length, 'rutinas desde API');
        actualizarContadores();
        
    } catch (error) {
        console.error('[modal-rutina-fixed] Error cargando rutinas:', error);
        mostrarToast('Error de conexión', 'error');
    }
}

// Actualizar contadores
function actualizarContadores() {
    const rutinasActivas = window.rutinas ? window.rutinas.filter(r => r.status === 'activa').length : 0;
    
    const totalRutinasEl = document.getElementById('totalRutinas');
    const badgeRutinas = document.getElementById('badgeRutinas');
    
    if (totalRutinasEl) totalRutinasEl.textContent = rutinasActivas;
    if (badgeRutinas) badgeRutinas.textContent = rutinasActivas;
}

// Modal nueva rutina
function abrirModal() {
    console.log('[modal-rutina-fixed] abrirModal llamada');
    const modal = document.getElementById('modalNuevaRutina');
    if (modal) {
        modal.classList.remove('hidden');
        modal.style.display = 'flex';
        console.log('[modal-rutina-fixed] Modal abierto');
    } else {
        console.error('[modal-rutina-fixed] Modal no encontrado');
    }
}

// Exportar función globalmente
window.abrirModal = abrirModal;

function cerrarModal() {
    console.log('[modal-rutina-fixed] cerrarModal llamada');
    const modal = document.getElementById('modalNuevaRutina');
    if (modal) {
        modal.classList.add('hidden');
        modal.style.display = 'none';
    }
    // Limpiar ejercicios temporales
    ejerciciosTemporales = [];
    const lista = document.getElementById('listaEjercicios');
    if (lista) {
        lista.innerHTML = '<p class="text-gray-500 text-sm text-center py-4">No hay ejercicios agregados.</p>';
    }
}

// Exportar función globalmente
window.cerrarModal = cerrarModal;

// Funciones para manejar ejercicios en el modal
function agregarEjercicio() {
    const container = document.getElementById('listaEjercicios');
    if (!container) return;
    
    const index = ejerciciosTemporales.length;
    
    const ejercicioDiv = document.createElement('div');
    ejercicioDiv.className = 'bg-neutral-800 p-3 rounded-lg';
    ejercicioDiv.setAttribute('data-index', index);
    ejercicioDiv.innerHTML = `
        <div class="grid grid-cols-4 gap-2 mb-2">
            <input type="text" placeholder="Nombre ejercicio" class="col-span-2 p-2 bg-neutral-700 rounded text-white text-sm ejercicio-nombre" />
            <input type="number" placeholder="Series" min="1" value="3" class="p-2 bg-neutral-700 rounded text-white text-sm ejercicio-series" />
            <input type="number" placeholder="Reps" min="1" value="10" class="p-2 bg-neutral-700 rounded text-white text-sm ejercicio-reps" />
        </div>
        <div class="flex justify-end">
            <button type="button" class="text-red-400 hover:text-red-300 text-xs btn-eliminar-ejercicio" data-index="${index}">
                <i class="fa-solid fa-trash"></i> Eliminar
            </button>
        </div>
    `;
    
    if (container.querySelector('p')) {
        container.innerHTML = '';
    }
    
    container.appendChild(ejercicioDiv);
    ejerciciosTemporales.push({ nombre: '', series: 3, repeticiones: 10 });
    
    // Eventos para actualizar valores
    const inputs = ejercicioDiv.querySelectorAll('input');
    inputs[0].addEventListener('input', (e) => {
        ejerciciosTemporales[index].nombre = e.target.value;
    });
    inputs[1].addEventListener('input', (e) => {
        ejerciciosTemporales[index].series = parseInt(e.target.value) || 3;
    });
    inputs[2].addEventListener('input', (e) => {
        ejerciciosTemporales[index].repeticiones = parseInt(e.target.value) || 10;
    });
    
    const btnEliminar = ejercicioDiv.querySelector('.btn-eliminar-ejercicio');
    btnEliminar.addEventListener('click', () => {
        ejerciciosTemporales.splice(index, 1);
        ejercicioDiv.remove();
        if (ejerciciosTemporales.length === 0) {
            container.innerHTML = '<p class="text-gray-500 text-sm text-center py-4">No hay ejercicios agregados.</p>';
        }
    });
}

// Guardar nueva rutina - OPTIMIZADO con ejercicios
async function guardarRutina(event) {
    if (event) event.preventDefault();
    
    const form = event?.target || document.getElementById('formNuevaRutina');
    if (form?.dataset.submitting) return;
    if (form) form.dataset.submitting = '1';

    const nombre = document.getElementById('nombreRutina')?.value?.trim();
    const descripcion = document.getElementById('descripcionRutina')?.value?.trim();
    const objetivo = document.getElementById('objetivoRutina')?.value;
    const tipo = document.getElementById('tipoRutina')?.value;
    const dificultad = document.getElementById('dificultadRutina')?.value;
    const semanas = document.getElementById('semanasDuracion')?.value;
    
    if (!nombre) {
        mostrarToast('El nombre es obligatorio', 'error');
        if (form) form.dataset.submitting = '0';
        return;
    }
    
    // Filtrar ejercicios válidos
    const ejerciciosValidos = ejerciciosTemporales.filter(e => e.nombre && e.nombre.trim() !== '');
    
    const data = {
        nombre, 
        descripcion: descripcion || '', 
        objetivo: objetivo || 'hipertrofia',
        tipo: tipo || 'personalizada', 
        status: 'activa',
        dificultad: dificultad || 'intermedio',
        semanas_duracion: parseInt(semanas) || 4,
        ejercicios: ejerciciosValidos
    };
    
    try {
        const response = await fetch('/api/rutinas/crear/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            mostrarToast('Rutina creada exitosamente', 'success');
            cerrarModal();
            if (form) form.reset();
            ejerciciosTemporales = [];
            
            // Recargar página para mostrar la nueva rutina
            setTimeout(() => {
                window.location.reload();
            }, 500);
        } else {
            const errorData = await response.json().catch(() => ({}));
            mostrarToast(errorData.error || 'Error al crear rutina', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarToast('Error de conexión', 'error');
    } finally {
        if (form) form.dataset.submitting = '0';
    }
}

// Editar rutina - OPTIMIZADO con caché local
async function editarRutina(id) {
    try {
        // Asegurarse de que window.rutinas sea un array
        if (!Array.isArray(window.rutinas)) {
            window.rutinas = [];
        }
        
        // Inicializar caché si no existe
        if (!window._rutinasCache) {
            window._rutinasCache = {};
        }
        
        // Primero intentar buscar en rutinas cargadas
        let rutina = window.rutinas.find(r => r.id == id);
        
        // Si no está en la lista, intentar caché
        if (!rutina && window._rutinasCache[id]) {
            rutina = window._rutinasCache[id];
        }
        
        // Si aún no tenemos, hacer fetch
        if (!rutina) {
            const response = await fetch(`/api/rutinas/${id}/`, {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin'
            });
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('Error response:', errorText);
                mostrarToast('Error al obtener la rutina', 'error');
                return;
            }
            
            const data = await response.json();
            // La API puede devolver {success: true, ...rutina} o directamente la rutina
            rutina = data.success !== undefined ? data : data;
            window._rutinasCache[id] = rutina; // Guardar en caché
        }
        
        // Llenar campos del modal - OPTIMIZADO
        const inputs = {
            editarRutinaId: rutina.id,
            editarNombreRutina: rutina.nombre || '',
            editarDescripcionRutina: rutina.descripcion || '',
            editarObjetivoRutina: rutina.objetivo || 'fuerza',
            editarTipoRutina: rutina.tipo || 'personalizada',
            editarDuracionRutina: rutina.duracion || rutina.duracion_semanas || '4'
        };
        
        for (const [id, value] of Object.entries(inputs)) {
            const elem = document.getElementById(id);
            if (elem) elem.value = value;
        }
        
        // Cargar ejercicios existentes
        ejerciciosEditar = rutina.ejercicios || [];
        mostrarEjerciciosEditar();
        
        // Abrir modal
        const modal = document.getElementById('modalEditarRutina');
        if (modal) {
            modal.classList.remove('hidden');
            modal.style.display = 'flex';
        }
        
    } catch (error) {
        console.error('Error en editarRutina:', error);
        mostrarToast('Error al editar la rutina', 'error');
    }
}

// Exportar función globalmente
window.editarRutina = editarRutina;

// Cerrar modal de edición
function cerrarModalEditar() {
    const modal = document.getElementById('modalEditarRutina');
    if (modal) {
        modal.classList.add('hidden');
        modal.style.display = 'none';
    }
    // Limpiar lista de ejercicios
    ejerciciosEditar = [];
}

// Exportar función globalmente
window.cerrarModalEditar = cerrarModalEditar;

// Mostrar ejercicios en el modal de edición
function mostrarEjerciciosEditar() {
    const lista = document.getElementById('listaEjerciciosEditar');
    if (!lista) return;
    
    lista.innerHTML = '';
    
    if (ejerciciosEditar.length === 0) {
        lista.innerHTML = '<p class="text-gray-400 text-sm italic">No hay ejercicios agregados</p>';
        return;
    }
    
    ejerciciosEditar.forEach((ej, index) => {
        const div = document.createElement('div');
        div.className = 'flex items-center justify-between bg-gray-800 p-2 rounded border border-gray-700';
        div.innerHTML = `
            <div class="flex-1">
                <span class="text-white text-sm font-medium">${ej.nombre_ejercicio || ej.nombre || 'Sin nombre'}</span>
                <span class="text-gray-400 text-xs ml-2">${ej.repeticiones || '—'}</span>
            </div>
            <button type="button" onclick="eliminarEjercicioEditar(${index})" class="text-red-500 hover:text-red-400 text-sm">
                <i class="fa-solid fa-trash"></i>
            </button>
        `;
        lista.appendChild(div);
    });
}

// Agregar ejercicio al modal de edición
function agregarEjercicioEditar() {
    const nombreInput = document.getElementById('editarNombreEjercicio');
    const repeticionesInput = document.getElementById('editarRepeticiones');
    
    if (!nombreInput || !repeticionesInput) return;
    
    const nombre = nombreInput.value.trim();
    const repeticiones = repeticionesInput.value.trim();
    
    if (!nombre) {
        mostrarToast('Ingresa el nombre del ejercicio', 'error');
        return;
    }
    
    ejerciciosEditar.push({
        nombre_ejercicio: nombre,
        repeticiones: repeticiones || '3x12'
    });
    
    // Limpiar inputs
    nombreInput.value = '';
    repeticionesInput.value = '';
    
    mostrarEjerciciosEditar();
    mostrarToast('Ejercicio agregado', 'success');
}

// Exportar función globalmente
window.agregarEjercicioEditar = agregarEjercicioEditar;

// Eliminar ejercicio del modal de edición
function eliminarEjercicioEditar(index) {
    ejerciciosEditar.splice(index, 1);
    mostrarEjerciciosEditar();
    mostrarToast('Ejercicio eliminado', 'info');
}

// Exportar función globalmente
window.eliminarEjercicioEditar = eliminarEjercicioEditar;

// Guardar cambios de rutina editada - OPTIMIZADO
async function actualizarRutina(event) {
    if (event) event.preventDefault();
    
    // Prevenir duplicados
    const form = event?.target;
    if (form?.dataset.submitting) return;
    form.dataset.submitting = '1';
    
    try {
        const rutinaId = document.getElementById('editarRutinaId').value;
        const nombre = document.getElementById('editarNombreRutina').value.trim();
        const descripcion = document.getElementById('editarDescripcionRutina').value.trim();
        const objetivo = document.getElementById('editarObjetivoRutina').value;
        const tipo = document.getElementById('editarTipoRutina').value;
        const duracion = parseInt(document.getElementById('editarDuracionRutina').value || '0', 10) || 4;
        
        if (!nombre) {
            mostrarToast('El nombre de la rutina es obligatorio', 'error');
            form.dataset.submitting = '0';
            return;
        }
        
        const payload = {
            nombre, descripcion, objetivo, tipo, duracion
        };
        
        // Solo enviar ejercicios nuevos (los que no tienen ID)
        const nuevosEjercicios = ejerciciosEditar.filter(ej => !ej.id).map(ej => ({
            nombre: ej.nombre_ejercicio || ej.nombre,
            repeticiones: ej.repeticiones || '3x12'
        }));
        
        if (nuevosEjercicios.length > 0) {
            payload.nuevos_ejercicios = nuevosEjercicios;
        }
        
        const response = await fetch(`/api/rutinas/${rutinaId}/actualizar/`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            mostrarToast('Error al actualizar rutina', 'error');
            form.dataset.submitting = '0';
            return;
        }
        
        // Actualizar caché
        window._rutinasCache[rutinaId] = { id: rutinaId, ...payload };
        
        mostrarToast('Rutina actualizada correctamente', 'success');
        cerrarModalEditar();
        
        // Recargar página para ver cambios
        setTimeout(() => location.reload(), 500);
        
    } catch (error) {
        console.error('Error:', error);
        mostrarToast('Error al guardar cambios', 'error');
    } finally {
        form.dataset.submitting = '0';
    }
}

// Exportar función globalmente
window.actualizarRutina = actualizarRutina;

// Eliminar rutina - OPTIMIZADO
async function eliminarRutina(id) {
    console.log('Intentando eliminar rutina ID:', id);
    
    if (!confirm('¿Estás seguro de eliminar esta rutina? Esta acción no se puede deshacer.')) {
        console.log('Eliminación cancelada por el usuario');
        return;
    }

    try {
        console.log('Enviando petición DELETE a:', `/api/rutinas/${id}/eliminar/`);
        
        const response = await fetch(`/api/rutinas/${id}/eliminar/`, {
            method: 'DELETE',
            headers: { 'X-CSRFToken': getCsrfToken() }
        });
        
        console.log('Respuesta recibida:', response.status, response.ok);
        
        if (response.ok) {
            const data = await response.json();
            console.log('Rutina eliminada correctamente:', data);
            mostrarToast('Rutina eliminada', 'success');
            delete window._rutinasCache[id];
            cerrarModalEditar();
            
            // Recargar página para ver cambios
            setTimeout(() => location.reload(), 500);
        } else {
            const errorData = await response.json().catch(() => ({}));
            console.error('Error al eliminar:', errorData);
            mostrarToast('Error al eliminar rutina: ' + (errorData.error || 'Desconocido'), 'error');
        }
    } catch (error) {
        console.error('Error en eliminarRutina:', error);
        mostrarToast('Error de conexión', 'error');
    }
}

// Exportar función globalmente
window.eliminarRutina = eliminarRutina;

// Función auxiliar para eliminar la rutina actual del modal
window.eliminarRutinaActual = function() {
    const rutinaId = document.getElementById('editarRutinaId')?.value;
    if (rutinaId) {
        eliminarRutina(rutinaId);
    }
};

// Exportar CSV
function exportarCSV() {
    if (!window.rutinas || window.rutinas.length === 0) {
        mostrarToast('No hay rutinas para exportar', 'info');
        return;
    }
    
    const csv = 'ID,Nombre,Objetivo,Estado\n' + 
        window.rutinas.map(r => `${r.id},"${r.nombre}","${r.objetivo}","${r.status}"`).join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'rutinas.csv';
    a.click();
    URL.revokeObjectURL(url);
}

// Inicialización - SOLO event listeners, NO renderizado
document.addEventListener('DOMContentLoaded', function() {
    console.log('[modal-rutina-fixed] DOMContentLoaded - Configurando event listeners (sin carga/renderizado)');
    
    if (window._rutinaFormBound) {
        console.log('[modal-rutina-fixed] Ya inicializado, skip');
        return;
    }
    window._rutinaFormBound = true;
    
    // Attachers individuales
    const attachListener = (id, event, fn) => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener(event, fn);
            console.log(`[modal-rutina-fixed] Listener agregado: ${id}.${event}`);
        }
    };
    
    attachListener('btnNuevaRutina', 'click', abrirModal);
    attachListener('btnCerrarModal', 'click', cerrarModal);
    attachListener('btnAgregarEjercicio', 'click', agregarEjercicio);
    attachListener('formNuevaRutina', 'submit', guardarRutina);
    attachListener('formEditarRutina', 'submit', actualizarRutina);
    attachListener('btnExportarCSV', 'click', exportarCSV);
    
    // Event delegation para botones de editar/eliminar
    document.addEventListener('click', (e) => {
        const btnEditar = e.target.closest('[data-action="editar"]');
        if (btnEditar) {
            e.preventDefault();
            const id = btnEditar.closest('[data-id]')?.dataset.id;
            if (id) editarRutina(id);
            return;
        }
        
        const btnEliminar = e.target.closest('[data-action="eliminar"]');
        if (btnEliminar) {
            e.preventDefault();
            const id = btnEliminar.closest('[data-id]')?.dataset.id;
            if (id) eliminarRutina(id);
        }
    }, true); // Captura en fase de captura para mayor velocidad
    
    // Cerrar modales con Escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            cerrarModal();
            cerrarModalEditar();
        }
    });
});

console.log('modal-rutina-fixed.js v2.0 optimizado - Cargado exitosamente');