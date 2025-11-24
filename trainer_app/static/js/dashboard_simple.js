// dashboard_simple.js - adapted from former dashboard_nuevo.js
(function(){
// Simple dashboard script: carga alumnos y controla la tabla

function mostrarError(mensaje) {
    const tbody = document.getElementById('tablaAlumnos');
    const contenido = document.getElementById('contenidoAlumnos');
    const tablaWrap = document.getElementById('tablaWrap');
    if (contenido) {
        contenido.innerHTML = `<div class="text-red-400 text-center py-8">${mensaje}</div>`;
        contenido.style.display = 'block';
    }
    if (tbody) {
        tbody.innerHTML = '';
    }
    if (tablaWrap) tablaWrap.style.display = 'none';
}

function mostrarAlumnos(alumnos) {
    const tbody = document.getElementById('tablaAlumnos');
    const tablaWrap = document.getElementById('tablaWrap');
    const contenido = document.getElementById('contenidoAlumnos');
    if (!tbody || !tablaWrap) return;
    tbody.innerHTML = '';

    if (!alumnos || alumnos.length === 0) {
        contenido.innerHTML = '<div class="text-gray-400 text-center py-8">No hay alumnos registrados</div>';
        contenido.style.display = 'block';
        if (tablaWrap) tablaWrap.style.display = 'none';
        return;
    }

    alumnos.forEach(function(alumno) {
        const row = document.createElement('tr');
        row.className = 'border-b border-gray-700';
        const nombre = alumno.nombre || alumno.username || 'Sin nombre';
        const email = alumno.email || 'Sin email';
        const telefono = alumno.telefono || '-';
        const membresia = alumno.membresia || '-';
        const rutinas = alumno.rutinas_asignadas || 0;

        row.innerHTML = `
            <td data-label="Alumno" class="py-4 px-4"><div class="flex items-center gap-3"><div class="w-10 h-10 bg-emerald-500 rounded-full flex items-center justify-center font-bold text-white">${(nombre[0]||'').toUpperCase()}</div><div><div class="text-white font-semibold">${nombre}</div><div class="text-gray-400 text-sm">ID: ${alumno.id}</div></div></div></td>
            <td data-label="Email" class="py-4 px-4 text-gray-300">${email}</td>
            <td data-label="Teléfono" class="py-4 px-4 text-gray-300 hidden-mobile">${telefono}</td>
            <td data-label="Membresía" class="py-4 px-4 text-gray-300">${membresia}</td>
            <td data-label="Rutinas" class="py-4 px-4"><span class="bg-emerald-500/20 text-emerald-300 px-3 py-1 rounded-full text-sm">${rutinas}</span></td>
        `;
        tbody.appendChild(row);
    });

    if (tablaWrap) tablaWrap.style.display = 'block';
    if (contenido) contenido.style.display = 'none';
    const totalEl = document.getElementById('totalAlumnos'); if (totalEl) totalEl.textContent = alumnos.length;
}

// Extrae un array de alumnos de distintos formatos de respuesta posibles
function extraerArrayAlumnos(raw) {
    if (!raw) return [];
    // Si ya es array
    if (Array.isArray(raw)) return raw;
    // Posibles keys donde viene el array
    const keys = ['alumnos', 'data', 'results', 'items'];
    for (let k of keys) {
        if (raw[k] && Array.isArray(raw[k])) return raw[k];
    }
    // Buscar primer array anidado
    for (const k in raw) {
        if (Array.isArray(raw[k])) return raw[k];
    }
    // No se encontró, devolver vacío
    return [];
}

async function cargarAlumnosDesdeAPI() {
    const tablaWrap = document.getElementById('tablaWrap');
    const contenido = document.getElementById('contenidoAlumnos');
    // show loader (if tablaWrap exists we keep showing until replaced)
    try {
        if (!window.fetch) throw new Error('fetch-not-supported');
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 10000);
        const resp = await fetch('/api/alumnos/', {
            method: 'GET', headers: {'Accept': 'application/json'}, credentials: 'same-origin', signal: controller.signal
        });
        clearTimeout(timeout);
        if (!resp.ok) { mostrarError('Error HTTP: ' + resp.status); return; }
        let data;
        try { data = await resp.json(); } catch(e) { console.warn('JSON parse error', e); mostrarError('Error parseando respuesta'); return; }
        const alumnos = extraerArrayAlumnos(data);
        mostrarAlumnos(alumnos);
    } catch (err) {
        console.warn('Fetch error:', err);
        if (err && err.name === 'AbortError') mostrarError('La solicitud tardó demasiado (timeout)'); else mostrarError('Error cargando alumnos');
    } finally {
        // asegurar que el loader/placeholder no quede visible
        try {
            if (contenido && contenido.innerHTML && contenido.innerHTML.match(/spinner|cargando|procesando/i)) {
                contenido.style.display = 'none';
            }
            if (tablaWrap && tablaWrap.style.display === 'none') {
                // si tabla sigue oculta y no hay filas, mostramos mensaje en contenido
                const tbody = document.getElementById('tablaAlumnos');
                if (tbody && tbody.children.length === 0) {
                    contenido.innerHTML = '<div class="text-gray-400 text-center py-8">No hay alumnos disponibles</div>';
                    contenido.style.display = 'block';
                }
            }
        } catch(e) { /* ignore */ }
    }
}

window.cargarAlumnosDesdeAPI = cargarAlumnosDesdeAPI;

document.addEventListener('DOMContentLoaded', function() {
    try {
        const initial = window.INITIAL_ALUMNOS || null;
        if (initial && Array.isArray(initial) && initial.length) { mostrarAlumnos(initial); return; }
    } catch(e) { console.warn('Initial alumnos parse error', e); }
    setTimeout(function(){ cargarAlumnosDesdeAPI(); }, 300);
});

})();
