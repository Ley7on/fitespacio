// Sistema completo de rutinas con CRUD
// Usar una variable global compartida si ya existe (rutinasData)
window.rutinas = window.rutinasData || [];

// Cargar rutinas al iniciar
// NOTE: la inicialización se hace desde la plantilla principal para asegurar que las funciones fallback
// (mostrarToast, actualizarContadores, etc.) ya estén definidas. No ejecutar automáticamente aquí.
// document.addEventListener('DOMContentLoaded', function() {
//     cargarRutinas();
// });

// Normalize API response to always return an Array of rutinas
function normalizeRutinas(data) {
  // Manejo defensivo: aceptar array, objetos con claves comunes y JSON en string
  if (!data) return [];
  if (Array.isArray(data)) return data.slice();
  if (typeof data === 'string') {
    try {
      const parsed = JSON.parse(data);
      return normalizeRutinas(parsed);
    } catch (e) {
      return [];
    }
  }
  if (Array.isArray(data.rutinas)) return data.rutinas.slice();
  if (data.data && Array.isArray(data.data.rutinas)) return data.data.rutinas.slice();
  if (data.result && Array.isArray(data.result.rutinas)) return data.result.rutinas.slice();
  // intentar extraer el primer array que encontremos dentro del objeto
  try {
    for (const key in data) {
      if (Object.prototype.hasOwnProperty.call(data, key) && Array.isArray(data[key])) {
        return data[key].slice();
      }
    }
  } catch (e) { /* ignore */ }
  console.warn('[normalizeRutinas] formato desconocido, devolviendo array vacío', data);
  return [];
}

// Helper: asegurar que cualquier valor sea devuelto como array (copia)
function ensureArray(val) {
  if (!val) return [];
  if (Array.isArray(val)) return val.slice();
  // si es objeto que contiene arrays conocidas
  const possible = normalizeRutinas(val);
  if (Array.isArray(possible)) return possible.slice();
  return [];
}

// Nuevo helper: normaliza y asigna las rutinas a los globals de forma segura
function setGlobalRutinas(source) {
  const arr = normalizeRutinas(source);
  try {
    // asignar copias para evitar referencias inesperadas
    window.rutinas = Array.isArray(arr) ? arr.slice() : [];
    window.rutinasData = Array.isArray(arr) ? arr.slice() : [];
  } catch (e) {
    window.rutinas = window.rutinas || [];
    window.rutinasData = window.rutinasData || [];
  }
}

// === CARGAR Y MOSTRAR RUTINAS ===
async function cargarRutinas() {
    try {
        console.log('Cargando rutinas (modal-rutina.js)...');
        const url = (window.obtenerRutinasUrl) ? window.obtenerRutinasUrl : '/api/rutinas/';
        const response = await fetch(url);
        if (response.ok) {
            const json = await response.json().catch(() => null);

            // Normalizar la respuesta a un array y fijarla en globals
            const rutinasArr = normalizeRutinas(json);

            // Usar setGlobalRutinas para garantizar arrays en window.rutinas / window.rutinasData
            setGlobalRutinas(rutinasArr || json);

            // Si existe una fuente centralizada ya poblada (window.rutinasData) y es array, respetarla
            if (window.rutinasData && Array.isArray(window.rutinasData) && window.rutinasData.length > 0) {
                window.rutinas = window.rutinasData.slice();
            }

            // Garantizar que window.rutinas sea un Array antes de llamar a otras funciones que usen .filter/.forEach
            try {
              const safe = Array.isArray(window.rutinas) ? window.rutinas : (
                Array.isArray(window.rutinas.rutinas) ? window.rutinas.rutinas : (
                  Array.isArray(window.rutinasData) ? window.rutinasData : []
                )
              );
              window.rutinas = Array.isArray(safe) ? safe.slice() : [];
              window.rutinasData = Array.isArray(safe) ? safe.slice() : Array.isArray(window.rutinasData) ? window.rutinasData.slice() : [];
            } catch(e) {
              window.rutinas = Array.isArray(window.rutinas) ? window.rutinas : [];
              window.rutinasData = Array.isArray(window.rutinasData) ? window.rutinasData : [];
            }

            mostrarRutinas();
            if (typeof actualizarEstadisticas === 'function') try { actualizarEstadisticas(); } catch(e){ console.warn('actualizarEstadisticas falló, usando local:', e); actualizarEstadisticasLocal(); }
            else actualizarEstadisticasLocal();
        } else {
            console.error('Error en respuesta:', response.status);
        }
    } catch (error) {
        console.error('Error cargando rutinas:', error);
    }
}

// Ensure globals are arrays (coerce objects with .rutinas)
(function normalizeGlobalRutinas(){
  try {
    // intentar normalizar cualquier forma irregular
    if (window.rutinas && !Array.isArray(window.rutinas)) {
      setGlobalRutinas(window.rutinas);
    }
    if (window.rutinasData && !Array.isArray(window.rutinasData)) {
      setGlobalRutinas(window.rutinasData);
    }
    if (!window.rutinas) window.rutinas = Array.isArray(window.rutinasData) ? window.rutinasData.slice() : [];
    if (!window.rutinasData) window.rutinasData = Array.isArray(window.rutinas) ? window.rutinas.slice() : [];
  } catch (e) {
    console.warn('normalizeGlobalRutinas error', e);
    window.rutinas = window.rutinas || [];
    window.rutinasData = window.rutinasData || [];
  }
})();

function getRutinasArray() {
  // Intentar devolver el array más fiable disponible
  if (Array.isArray(window.rutinas)) return window.rutinas.slice();
  if (window.rutinas && Array.isArray(window.rutinas.rutinas)) return window.rutinas.rutinas.slice();
  if (Array.isArray(window.rutinasData)) return window.rutinasData.slice();
  if (window.rutinasData && Array.isArray(window.rutinasData.rutinas)) return window.rutinasData.rutinas.slice();
  // último recurso: intentar normalizar globals o la variable local rutinasData
  const candidates = [window.rutinas, window.rutinasData, typeof rutinasData !== 'undefined' ? rutinasData : null];
  for (const c of candidates) {
    const arr = ensureArray(c);
    if (arr.length) return arr;
  }
  return [];
}

function mostrarRutinas(inputData) {
    // Si se pasa data explícita, usarla; si no, leer globals
    let data = Array.isArray(inputData) ? inputData.slice() : getRutinasArray();
    // Forzar normalización final (acepta objetos con key rutinas)
    try {
      data = normalizeRutinas(data);
    } catch (e) {
      console.warn('normalizeRutinas falló en mostrarRutinas', e, data);
    }

    // Asegurar que data sea un array antes de iterar
    data = ensureArray(data);

    const container = document.getElementById('vistaTarjetas');
    if (!container) return;
    container.innerHTML = '';
    
    if (data.length === 0) {
        container.innerHTML = `
            <div class="col-12 text-center py-5">
                <i class="bi bi-clipboard-x display-1 text-muted"></i>
                <h5 class="text-muted mt-3">No hay rutinas</h5>
                <p class="text-muted">Crea tu primera rutina</p>
                <button class="btn btn-primary" id="btnCrearRutinaInline">
                    <i class="bi bi-plus"></i> Crear Rutina
                </button>
            </div>
        `;
        // attach fallback listener
        const inlineBtn = document.getElementById('btnCrearRutinaInline');
        if (inlineBtn) inlineBtn.addEventListener('click', () => {
          if (typeof window.abrirModal === 'function') return window.abrirModal();
          const modal = document.getElementById('modalNuevaRutina'); if (modal) modal.style.display = 'flex';
        });
        return;
    }
    
    data.forEach(rutina => {
        const card = crearTarjetaRutina(rutina);
        container.appendChild(card);
    });
}

function crearTarjetaRutina(rutina) {
    const div = document.createElement('div');
    div.className = 'col-12 col-md-6 col-lg-4';
    
    const objetivoIcons = {
        'fuerza': '🏋️',
        'hipertrofia': '💪',
        'resistencia': '🏃',
        'perdida_grasa': '🔥'
    };
    
    const dificultadColors = {
        'principiante': 'success',
        'intermedio': 'warning',
        'avanzado': 'danger'
    };
    
    // Asignar data-id para delegación de clicks
    const fecha = rutina.fecha_creacion ? new Date(rutina.fecha_creacion).toLocaleDateString() : '';
    div.innerHTML = `
        <div class="card h-100 border-0 shadow-sm routine-card" data-id="${rutina.id}">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start mb-3">
                    <span class="badge bg-${dificultadColors[rutina.dificultad] || 'primary'}">
                        ${objetivoIcons[rutina.objetivo] || '💪'} ${rutina.objetivo}
                    </span>
                    <div class="dropdown">
                        <button class="btn btn-sm btn-outline-secondary" data-bs-toggle="dropdown">
                            <i class="bi bi-three-dots-vertical"></i>
                        </button>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item" onclick="editarRutina(${rutina.id})">
                                <i class="bi bi-pencil"></i> Editar
                            </a></li>
                            <li><a class="dropdown-item text-danger" onclick="eliminarRutina(${rutina.id})">
                                <i class="bi bi-trash"></i> Eliminar
                            </a></li>
                        </ul>
                    </div>
                </div>
                
                <h5 class="card-title">${rutina.nombre}</h5>
                <p class="text-muted small mb-3">
                    <i class="bi bi-signal"></i> ${rutina.dificultad || ''} • 
                    <i class="bi bi-list-check"></i> ${rutina.ejercicios?.length || 0} ejercicios
                </p>
                
                ${rutina.notas_entrenador ? `<p class="small text-muted">${rutina.notas_entrenador}</p>` : ''}
                
                <div class="d-flex justify-content-between align-items-center mt-3">
                    <small class="text-muted">
                        ${fecha}
                    </small>
                    <span class="badge bg-${rutina.status === 'activa' ? 'success' : 'secondary'}">
                        ${rutina.status}
                    </span>
                </div>
            </div>
        </div>
    `;
    
    return div;
}

function actualizarEstadisticasLocal() {
    const data = Array.isArray(window.rutinas) ? window.rutinas : [];
    const rutinasActivas = data.filter(r => r.status === 'activa').length;
    const totalRutinasEl = document.getElementById('totalRutinas');
    const badge = document.getElementById('badgeRutinas');
    if (totalRutinasEl) totalRutinasEl.textContent = rutinasActivas;
    if (badge) badge.textContent = rutinasActivas;
}

// === MODAL NUEVA RUTINA ===
function abrirModal() {
    const modal = document.getElementById('modalNuevaRutina');
    if (modal) modal.style.display = 'flex';
    if (typeof resetearFormulario === 'function') resetearFormulario();

    // Cargar lista de alumnos para creación (sin seleccionados)
    try { cargarAlumnos([]); } catch (e) { console.warn('No se pudo cargar alumnos al abrir modal nueva rutina', e); }
}

function cerrarModal() {
    const modal = document.getElementById('modalNuevaRutina');
    if (modal) modal.style.display = 'none';
}

function resetearFormulario() {
    const form = document.getElementById('formNuevaRutina');
    if (form) form.reset();
    // Asegurarse de que exista el contenedor de ejercicios; si no, crearlo para evitar null
    let container = document.getElementById('ejerciciosContainer');
    if (!container) {
      // intentar insertar dentro del formulario en una posición razonable
      try {
        container = document.createElement('div');
        container.id = 'ejerciciosContainer';
        // añadir clases mínimas para que el CSS no rompa el layout
        container.className = 'mb-3';
        // colocar al final del form
        if (form) form.appendChild(container);
        else document.body.appendChild(container);
      } catch (e) {
        console.warn('No se pudo crear #ejerciciosContainer', e);
        container = null;
      }
    }
    if (container) {
        try {
          container.innerHTML = `
            <div class="ejercicio-item">
                <input type="text" placeholder="Nombre del ejercicio" class="form-control nombre-ejercicio" required>
                <div class="ejercicio-details d-flex gap-2 mt-2">
                    <div class="ej-detail text-start">
                      <label class="form-label small text-muted">Series</label>
                      <input type="number" placeholder="Series" aria-label="Series" min="1" max="10" value="3" class="form-control-sm" title="Número de series" />
                    </div>
                    <div class="ej-detail text-start">
                      <label class="form-label small text-muted">Reps (ej. 10-12)</label>
                      <input type="text" placeholder="Reps (ej. 10-12)" aria-label="Repeticiones" value="10-12" class="form-control-sm" title="Repeticiones" />
                    </div>
                    <div class="ej-detail text-start">
                      <label class="form-label small text-muted">Peso (kg)</label>
                      <input type="text" placeholder="Peso (kg)" aria-label="Peso inicial" class="form-control-sm" title="Peso sugerido en kg" />
                    </div>
                    <button type="button" onclick="eliminarEjercicio(this)" class="btn-remove" aria-label="Eliminar ejercicio">×</button>
                </div>
                <!-- Video block -->
                <div class="mt-2">
                  <label class="form-label small text-muted mb-1 d-block">Video del ejercicio</label>
                  <div class="d-flex gap-2 align-items-center">
                    <input type="file" accept="video/mp4,video/webm" class="form-control-file video-file-input" onchange="uploadVideo(this)" />
                    <div class="video-preview-box" style="width:64px;height:40px;background:#0b0b0b;border-radius:6px;overflow:hidden;display:flex;align-items:center;justify-content:center;">
                      <video class="d-none" muted loop style="width:100%;height:100%;object-fit:cover;"></video>
                      <span class="text-muted small">Sin video</span>
                    </div>
                  </div>
                  <div class="w-100 mt-2 progress-container d-none">
                    <div class="progress" style="height:6px;background:#2b2b2b;border-radius:4px;overflow:hidden;">
                      <div class="progress-bar bg-primary" style="width:0%;height:100%;transition:width .2s;"></div>
                    </div>
                  </div>
                  <input type="hidden" class="video-url" value="">
                </div>
            </div>
        `;
        } catch (e) { console.error('Error asignando innerHTML en resetearFormulario', e); }
    }
}

function agregarEjercicio() {
    const container = document.getElementById('ejerciciosContainer');
    if (!container) return;
    const nuevoEjercicio = document.createElement('div');
    nuevoEjercicio.className = 'ejercicio-item';
    nuevoEjercicio.innerHTML = `
        <input type="text" placeholder="Nombre del ejercicio" class="form-control nombre-ejercicio" required>
        <div class="ejercicio-details d-flex gap-2 mt-2">
            <div class="ej-detail text-start">
              <label class="form-label small text-muted">Series</label>
              <input type="number" placeholder="Series" aria-label="Series" min="1" max="10" value="3" class="form-control-sm">
            </div>
            <div class="ej-detail text-start">
              <label class="form-label small text-muted">Reps (ej. 10-12)</label>
              <input type="text" placeholder="Reps (ej. 10-12)" aria-label="Repeticiones" value="10-12" class="form-control-sm">
            </div>
            <div class="ej-detail text-start">
              <label class="form-label small text-muted">Peso (kg)</label>
              <input type="text" placeholder="Peso (kg)" aria-label="Peso inicial" class="form-control-sm">
            </div>
            <button type="button" onclick="eliminarEjercicio(this)" class="btn-remove" aria-label="Eliminar ejercicio">×</button>
        </div>
        <div class="mt-2">
          <label class="form-label small text-muted mb-1 d-block">Video del ejercicio</label>
          <div class="d-flex gap-2 align-items-center">
            <input type="file" accept="video/mp4,video/webm" class="form-control-file video-file-input" onchange="uploadVideo(this)" />
            <div class="video-preview-box" style="width:64px;height:40px;background:#0b0b0b;border-radius:6px;overflow:hidden;display:flex;align-items:center;justify-content:center;">
              <video class="d-none" muted loop style="width:100%;height:100%;object-fit:cover;"></video>
              <span class="text-muted small">Sin video</span>
            </div>
          </div>
          <div class="w-100 mt-2 progress-container d-none">
            <div class="progress" style="height:6px;background:#2b2b2b;border-radius:4px;overflow:hidden;">
              <div class="progress-bar bg-primary" style="width:0%;height:100%;transition:width .2s;"></div>
            </div>
          </div>
          <input type="hidden" class="video-url" value="">
        </div>
    `;
    container.appendChild(nuevoEjercicio);
}

function eliminarEjercicio(btn) {
    const container = document.getElementById('ejerciciosContainer');
    if (container && container.children.length > 1) {
        btn.closest('.ejercicio-item').remove();
    }
}

// === GUARDAR RUTINA ===
async function guardarRutina(event) {
  if (event) event.preventDefault();

  const form = (event && event.target && event.target.form) ? event.target.form : document.getElementById('formNuevaRutina');
  try { if (form && form.dataset.rutinaSubmitting === '1') { console.warn('guardarRutina: submission in progress, ignoring duplicate'); return; } } catch(e) {}
  try { if (form) form.dataset.rutinaSubmitting = '1'; } catch(e) {}

  const data = recopilarDatosFormulario('ejerciciosContainer');
  if (!data) { try{ if (form) form.dataset.rutinaSubmitting = '0'; }catch(e){}; return; }
    
    try {
        const response = await fetch((window.crearRutinaUrl) ? window.crearRutinaUrl : '/api/rutinas/crear/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
    if (result && (result.success || result.id || result.nombre)) {
      alert('Rutina creada exitosamente');
      cerrarModal();
      // refrescar via cargarRutinas o sincronizar con fuente central
      if (typeof window.cargarDatos === 'function') window.cargarDatos();
      else cargarRutinas();
      try{ if (form) form.dataset.rutinaSubmitting = '0'; }catch(e){}
    } else {
      alert('Error: ' + (result.error || 'No se pudo crear la rutina'));
      try{ if (form) form.dataset.rutinaSubmitting = '0'; }catch(e){}
    }
    } catch (error) {
        console.error('Error:', error);
        alert('Error al guardar la rutina');
    try{ if (form) form.dataset.rutinaSubmitting = '0'; }catch(e){}
    }
}

// === EDITAR RUTINA ===
async function editarRutina(id, _attempt = 0) {
  const MAX_ATTEMPTS = 6;
  try {
    // Obtener datos desde la API para tener la fuente de verdad
    const resp = await fetch(`/api/rutinas/${id}/editar/`);
    if (!resp.ok) throw new Error('Respuesta no OK: ' + resp.status);
    const payload = await resp.json().catch(() => null);
    const rutina = (payload && (payload.rutina || payload.data || payload)) || null;
    if (!rutina) throw new Error('Respuesta sin rutina');

    console.log('[EDITAR RUTINA] cargada:', rutina);

    // Comprobar que los elementos del modal estén presentes
    const inputId = document.getElementById('editarRutinaId') || document.getElementById('editar_id') || document.getElementById('idRutinaEditar');
    const inputNombre = document.getElementById('editarNombreRutina') || document.getElementById('nombreRutina') || document.querySelector('#formEditarRutina input[name="nombre"]');
    const inputObjetivo = document.getElementById('editarObjetivoRutina') || document.getElementById('objetivoRutina');
    const inputDificultad = document.getElementById('editarDificultadRutina') || document.getElementById('dificultadRutina');
    const inputNotas = document.getElementById('editarNotasRutina') || document.getElementById('notasRutina') || document.querySelector('#formEditarRutina textarea[name="notas_entrenador"]');
    const ejerciciosContainer = document.getElementById('editarEjerciciosContainer');

    // Si el modal o inputs no están listos, reintentar unas pocas veces
    if ((!inputNombre || !ejerciciosContainer) && _attempt < MAX_ATTEMPTS) {
      console.warn('[editarRutina] Modal o inputs no están listos. Reintentando en 200ms. Intento:', _attempt + 1);
      setTimeout(() => editarRutina(id, _attempt + 1), 200);
      return;
    }

    // Rellenar campos (si existen)
    if (inputId) inputId.value = rutina.id || id || '';
    if (inputNombre) inputNombre.value = rutina.nombre || '';
    if (inputObjetivo) inputObjetivo.value = rutina.objetivo || '';
    if (inputDificultad) inputDificultad.value = rutina.dificultad || '';
    if (inputNotas) inputNotas.value = rutina.notas_entrenador || rutina.notas || '';

    // Renderizar ejercicios: preferir helper existente
    const ejercicios = Array.isArray(rutina.ejercicios) ? rutina.ejercicios : (Array.isArray(rutina.data?.ejercicios) ? rutina.data.ejercicios : []);

    if (typeof window.llenarEjerciciosEditar === 'function') {
      try {
        window.llenarEjerciciosEditar(ejercicios);
      } catch (e) {
        console.warn('llenarEjerciciosEditar falló, usando fallback:', e);
      }
    }

    // Fallback: renderizar manualmente si no hay helper o fallo
    if ((!window.llenarEjerciciosEditar || typeof window.llenarEjerciciosEditar !== 'function') && ejerciciosContainer) {
      ejerciciosContainer.innerHTML = '';
      if (ejercicios.length === 0) {
        // dejar al menos un ejercicio vacío
        agregarEjercicioEditar();
      } else {
        ejercicios.forEach(ejercicio => {
          try {
            const div = document.createElement('div');
            div.className = 'ejercicio-item';
            // data-ejercicio-id para que uploadVideo pueda usarlo
            if (ejercicio.id) div.dataset.ejercicioId = ejercicio.id;

            const nombre = ejercicio.nombre ? String(ejercicio.nombre).replace(/"/g,'\"') : '';
            const series = ejercicio.series || ejercicio.series_count || 3;
            const reps = ejercicio.repeticiones || ejercicio.reps || ejercicio.repetitions || '10-12';
            const peso = ejercicio.peso_inicial || ejercicio.peso || ejercicio.peso_sugerido || '';
            const videoUrl = ejercicio.video_url || ejercicio.video || '';

            div.innerHTML = `
              <input type="text" value="${nombre}" class="form-control nombre-ejercicio" required>
              <div class="ejercicio-details d-flex gap-2 mt-2">
                <div class="ej-detail text-start">
                  <label class="form-label small text-muted">Series</label>
                  <input type="number" value="${series}" min="1" max="10" aria-label="Series" class="form-control-sm">
                </div>
                <div class="ej-detail text-start">
                  <label class="form-label small text-muted">Reps (ej. 10-12)</label>
                  <input type="text" value="${reps}" aria-label="Repeticiones" class="form-control-sm">
                </div>
                <div class="ej-detail text-start">
                  <label class="form-label small text-muted">Peso (kg)</label>
                  <input type="text" value="${peso}" aria-label="Peso inicial" class="form-control-sm">
                </div>
                <button type="button" onclick="eliminarEjercicioEditar(this)" class="btn-remove" aria-label="Eliminar ejercicio">×</button>
              </div>
              <div class="mt-2">
                <label class="form-label small text-muted mb-1 d-block">Video del ejercicio</label>
                <div class="d-flex gap-2 align-items-center">
                  <input type="file" accept="video/mp4,video/webm" class="form-control-file video-file-input" />
                  <div class="video-preview-box" style="width:64px;height:40px;background:#0b0b0b;border-radius:6px;overflow:hidden;display:flex;align-items:center;justify-content:center;">
                    <video class="d-none" muted loop style="width:100%;height:100%;object-fit:cover;"></video>
                    <span class="text-muted small">Sin video</span>
                  </div>
                </div>
                <div class="w-100 mt-2 progress-container d-none">
                  <div class="progress" style="height:6px;background:#2b2b2b;border-radius:4px;overflow:hidden;">
                    <div class="progress-bar bg-primary" style="width:0%;height:100%;transition:width .2s;"></div>
                  </div>
                </div>
                <input type="hidden" class="video-url" value="${videoUrl}">
              </div>
            `;

            ejerciciosContainer.appendChild(div);

            // inicializar preview si hay URL
            if (videoUrl) {
              const vid = div.querySelector('video');
              const span = div.querySelector('span');
              if (vid) { vid.src = videoUrl; vid.classList.remove('d-none'); if (span) span.classList.add('d-none'); }
            }

            // añadir listener al input file para subir
            const fileInput = div.querySelector('.video-file-input');
            if (fileInput) {
              fileInput.addEventListener('change', (ev) => uploadVideoFromInput(ev.target));
            }

          } catch (e) {
            console.warn('Error renderizando ejercicio en fallback', e, ejercicio);
          }
        });
      }
    }

    // Finalmente abrir el modal de edición de forma segura
    const modal = document.getElementById('modalEditarRutina');
    if (modal) {
      modal.style.display = 'flex';
    }

  } catch (err) {
    console.error('Error en editarRutina:', err);
    try { mostrarToast('No se pudo cargar la rutina para edición', 'error'); } catch(e){}
  }
}

function cerrarModalEditar() {
    const modal = document.getElementById('modalEditarRutina');
    if (modal) modal.style.display = 'none';
}

function agregarEjercicioEditar() {
    const container = document.getElementById('editarEjerciciosContainer');
    if (!container) return;
    const nuevoEjercicio = document.createElement('div');
    nuevoEjercicio.className = 'ejercicio-item';
    nuevoEjercicio.innerHTML = `
        <input type="text" placeholder="Nombre del ejercicio" class="form-control nombre-ejercicio" required>
        <div class="ejercicio-details d-flex gap-2 mt-2">
            <div class="ej-detail text-start">
              <label class="form-label small text-muted">Series</label>
              <input type="number" placeholder="Series" aria-label="Series" min="1" max="10" value="3" class="form-control-sm">
            </div>
            <div class="ej-detail text-start">
              <label class="form-label small text-muted">Reps (ej. 10-12)</label>
              <input type="text" placeholder="Reps (ej. 10-12)" aria-label="Repeticiones" value="10-12" class="form-control-sm">
            </div>
            <div class="ej-detail text-start">
              <label class="form-label small text-muted">Peso (kg)</label>
              <input type="text" placeholder="Peso (kg)" aria-label="Peso inicial" class="form-control-sm">
            </div>
            <button type="button" onclick="eliminarEjercicioEditar(this)" class="btn-remove" aria-label="Eliminar ejercicio">×</button>
        </div>
        <div class="mt-2">
          <label class="form-label small text-muted mb-1 d-block">Video del ejercicio</label>
          <div class="d-flex gap-2 align-items-center">
            <input type="file" accept="video/mp4,video/webm" class="form-control-file video-file-input" onchange="uploadVideo(this)" />
            <div class="video-preview-box" style="width:64px;height:40px;background:#0b0b0b;border-radius:6px;overflow:hidden;display:flex;align-items:center;justify-content:center;">
              <video class="d-none" muted loop style="width:100%;height:100%;object-fit:cover;"></video>
              <span class="text-muted small">Sin video</span>
            </div>
          </div>
          <div class="w-100 mt-2 progress-container d-none">
            <div class="progress" style="height:6px;background:#2b2b2b;border-radius:4px;overflow:hidden;">
              <div class="progress-bar bg-primary" style="width:0%;height:100%;transition:width .2s;"></div>
            </div>
          </div>
          <input type="hidden" class="video-url" value="">
        </div>
    `;
    container.appendChild(nuevoEjercicio);
}

function eliminarEjercicioEditar(btn) {
    const container = document.getElementById('editarEjerciciosContainer');
    if (container && container.children.length > 1) {
        btn.closest('.ejercicio-item').remove();
    }
}

async function actualizarRutina(event) {
    if (event) event.preventDefault();
    
    // Leer el id de forma defensiva: varios selectores de fallback
    const idEl = document.getElementById('editarRutinaId')
                 || document.getElementById('editar_id')
                 || document.getElementById('idRutinaEditar')
                 || document.querySelector('#formEditarRutina input[name="id"]')
                 || document.querySelector('#formEditarRutina input[name="editar_id"]')
                 || null;

    const id = idEl ? (idEl.value || idEl.getAttribute('value') || null) : null;
    if (!id) {
      console.error('actualizarRutina: no se encontró el input de id de rutina. idEl=', idEl);
      try { mostrarToast && mostrarToast('No se encontró la rutina a actualizar. Abre el modal de edición e inténtalo de nuevo.', 'error'); } catch(e){}
      return;
    }

    const data = recopilarDatosFormulario('editarEjerciciosContainer', true);
    if (!data) return;

    try {
        const response = await fetch(`/api/rutinas/${id}/editar/`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result && result.success) {
            alert('Rutina actualizada exitosamente');
            cerrarModalEditar();
            if (typeof window.cargarDatos === 'function') window.cargarDatos();
            else cargarRutinas();
        } else {
            alert('Error: ' + (result.error || 'No se pudo actualizar la rutina'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error al actualizar la rutina');
    }
}

// === ELIMINAR RUTINA ===
async function eliminarRutina(id) {
  // Use the global showConfirm helper (shim ensures it exists)
  const ok = await window.showConfirm('¿Estás seguro de que quieres eliminar esta rutina?', { title: 'Eliminar rutina', confirmText: 'Eliminar', cancelText: 'Cancelar', danger: true });
  if (!ok) return;

  try {
    const response = await fetch(`/api/rutinas/${id}/eliminar/`, {
      method: 'DELETE',
      headers: {
        'X-CSRFToken': getCsrfToken()
      }
    });
        
    const result = await response.json();
        
    if (result && result.success) {
      alert('Rutina eliminada exitosamente');
      if (typeof window.cargarDatos === 'function') window.cargarDatos();
      else cargarRutinas();
    } else {
      alert('Error: ' + (result.error || 'No se pudo eliminar la rutina'));
    }
  } catch (error) {
    console.error('Error:', error);
    alert('Error al eliminar la rutina');
  }
}

// === FUNCIONES AUXILIARES ===
function recopilarDatosFormulario(containerId, esEdicion = false) {
    const prefijo = esEdicion ? 'editar' : '';
    const nombre = (document.getElementById(`${prefijo}NombreRutina`) || document.getElementById('nombreRutina'))?.value || '';
    const objetivo = (document.getElementById(`${prefijo}ObjetivoRutina`) || document.getElementById('objetivoRutina'))?.value || '';
    const dificultad = (document.getElementById(`${prefijo}DificultadRutina`) || document.getElementById('dificultadRutina'))?.value || '';
    const notas = (document.getElementById(`${prefijo}NotasRutina`) || document.getElementById('notasRutina'))?.value || '';
    
    // Recopilar ejercicios
    const ejercicios = [];
    const ejerciciosItems = document.querySelectorAll(`#${containerId} .ejercicio-item`);
    
    ejerciciosItems.forEach((item, index) => {
        // Buscar campos por selector para no depender del orden de inputs
        const nombreInput = item.querySelector('.nombre-ejercicio') || item.querySelector('input[type="text"]');
        const seriesInput = item.querySelector('input[type="number"][aria-label="Series"]') || item.querySelector('input[type="number"]');
        const repsInput = item.querySelector('input[aria-label="Repeticiones"]') || item.querySelector('input[type="text"].reps') || item.querySelectorAll('input[type="text"]')[1];
        const pesoInput = item.querySelector('input[aria-label="Peso inicial"]') || item.querySelectorAll('input[type="text"]')[2] || item.querySelectorAll('input[type="text"]')[0];
        const videoUrlInput = item.querySelector('input.video-url');

        if (nombreInput && nombreInput.value && nombreInput.value.trim()) {
            ejercicios.push({
                nombre: nombreInput.value.trim(),
                series: parseInt(seriesInput?.value) || 3,
                repeticiones: repsInput?.value || '10-12',
                peso_inicial: pesoInput?.value || '',
                video_url: videoUrlInput ? videoUrlInput.value || '' : '',
                orden: index + 1
            });
        }
    });
    
    if (ejercicios.length === 0) {
        alert('Agrega al menos un ejercicio');
        return null;
    }
    
    return {
        nombre: nombre,
        objetivo: objetivo,
        dificultad: dificultad,
        tipo: 'personalizada',
        status: 'activa',
        duracion_estimada: 60,
        frecuencia_semanal: 3,
        semanas_duracion: 4,
        notas_entrenador: notas,
        ejercicios: ejercicios
    };
}

function getCsrfToken() {
    const cookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
    if (cookie) return cookie.split('=')[1];
    
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

// Exportar CSV expuesto en window
function exportarCSV() {
    const data = getRutinasArray();
    if (!Array.isArray(data) || data.length === 0) { return mostrarToast('No hay rutinas para exportar', 'info'); }
    const rows = [];
    rows.push(['id','nombre','objetivo','dificultad','status','ejercicios_count']);
    data.forEach(r => rows.push([r.id||'', r.nombre||'', r.objetivo||'', r.dificultad||'', r.status||'', (r.ejercicios && r.ejercicios.length) || r.ejercicios_count || 0]));
    const csv = rows.map(r => r.map(cell => '"' + String(cell).replace(/"/g,'""') + '"').join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'rutinas_export.csv'; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
}
window.exportarCSV = exportarCSV;

// Exponer helpers globales para que la plantilla pueda forzar normalización si es necesario
window.normalizeRutinas = normalizeRutinas;
window.setGlobalRutinas = setGlobalRutinas;
window.cargarRutinas = cargarRutinas;

// Cerrar modales con clic fuera o Escape
document.addEventListener('click', function(event) {
    if (event.target.id === 'modalNuevaRutina') cerrarModal();
    if (event.target.id === 'modalEditarRutina') cerrarModalEditar();
});

document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        cerrarModal();
        cerrarModalEditar();
    }
});

// Upload video: acepta File, input element o (file, exerciseId)
async function uploadVideo(fileOrInput, exerciseId = null) {
  try {
    // Soporte para pasar el elemento <input type="file"> directamente
    let file = null;
    let inputEl = null;

    if (fileOrInput instanceof File) {
      file = fileOrInput;
    } else if (fileOrInput && fileOrInput.files && fileOrInput.files[0]) {
      inputEl = fileOrInput;
      file = fileOrInput.files[0];
    } else if (fileOrInput && fileOrInput.target && fileOrInput.target.files) {
      // si se pasa un event
      inputEl = fileOrInput.target;
      file = fileOrInput.target.files[0];
    }

    if (!file) {
      console.error('[uploadVideo] No se ha seleccionado ningún archivo o archivo inválido:', fileOrInput);
      try { mostrarToast && mostrarToast('Selecciona un video válido antes de subir', 'error'); } catch(e){}
      return { success: false, error: 'No file' };
    }

    // Validación básica de tipo y tamaño
    const validTypes = ['video/mp4', 'video/webm'];
    if (!validTypes.includes(file.type)) {
      try { mostrarToast && mostrarToast('Formato de video no soportado. Usa MP4 o WebM.', 'error'); } catch(e){}
      return { success: false, error: 'Unsupported format' };
    }
    const MAX_BYTES = 100 * 1024 * 1024; // 100 MB
    if (file.size > MAX_BYTES) {
      try { mostrarToast && mostrarToast('El video supera los 100MB permitidos.', 'error'); } catch(e){}
      return { success: false, error: 'File too large' };
    }

    // Determinar el contenedor del ejercicio para actualizar UI
    let container = null;
    if (exerciseId) container = document.querySelector(`.ejercicio-item[data-ejercicio-id="${exerciseId}"]`);
    if (!container && inputEl) container = inputEl.closest('.ejercicio-item');
    if (!container) container = document.querySelector('.ejercicio-item'); // fallback

    const statusEl = container ? (container.querySelector('.video-status') || container.querySelector('.video-preview-box span')) : null;
    const previewVideo = container ? (container.querySelector('video') || container.querySelector('.video-preview')) : null;
    const hiddenInput = container ? (container.querySelector('.video-url') || (exerciseId ? document.querySelector(`#video-url-${exerciseId}`) : null)) : (exerciseId ? document.querySelector(`#video-url-${exerciseId}`) : null);

    // Crear object URL de preview con manejo de errores
    let objectUrl = null;
    try {
      objectUrl = URL.createObjectURL(file);
    } catch (e) {
      console.error('[uploadVideo] createObjectURL fallo:', e);
      try { mostrarToast && mostrarToast('No se pudo generar vista previa del video', 'error'); } catch(e){}
      objectUrl = null;
    }

    if (previewVideo && objectUrl) {
      try {
        previewVideo.src = objectUrl;
        previewVideo.classList.remove('hidden');
        previewVideo.style.display = 'block';
      } catch (e) { /* ignore */ }
    }

    if (statusEl) {
      try { statusEl.textContent = 'Subiendo...'; } catch(e){}
    }

    // Preparar FormData y enviar
    const formData = new FormData();
    formData.append('video', file);
    if (exerciseId) formData.append('ejercicio_id', exerciseId);

    const resp = await fetch(window.uploadEjercicioVideoUrl || '/api/ejercicios/upload-video/', {
      method: 'POST',
      body: formData,
      headers: (typeof getCsrfToken === 'function') ? { 'X-CSRFToken': getCsrfToken() } : undefined,
    });

    let data = null;
    try { data = await resp.json(); } catch (e) { data = null; }

    if (!resp.ok || !data || data.success === false) {
      const errMsg = (data && (data.error || data.message)) || `HTTP ${resp.status}`;
      console.error('[uploadVideo] subida fallida:', errMsg, data);
      try { mostrarToast && mostrarToast('Error al subir el video: ' + errMsg, 'error'); } catch(e){}
      if (statusEl) try { statusEl.textContent = '❌ Error al subir video'; } catch(e){}
      // revocar blob si existiera
      try { if (objectUrl) URL.revokeObjectURL(objectUrl); } catch (e) {}
      return { success: false, error: errMsg };
    }

    // Asignar URL devuelta al campo oculto
    const publicUrl = data.video_url || data.url || '';
    if (hiddenInput && publicUrl) {
      try { hiddenInput.value = publicUrl; } catch(e){}
    }

    // Actualizar status y preview con la URL final
    if (statusEl) {
      try { statusEl.textContent = '✅ Video subido'; } catch(e){}
    }

    if (previewVideo && publicUrl) {
      try {
        // Reemplazar la preview por la URL del servidor
        previewVideo.src = publicUrl;
        // cuando cargue la fuente remota, revocar el objectUrl temporal si existía
        if (objectUrl) {
          const onLoaded = () => { try { URL.revokeObjectURL(objectUrl); } catch(e){}; previewVideo.removeEventListener('loadeddata', onLoaded); };
          previewVideo.addEventListener('loadeddata', onLoaded);
        }
      } catch (e) { console.warn('No se pudo asignar preview final:', e); }
    } else if (previewVideo && objectUrl) {
      // No hay URL pública pero tenemos preview temporal: revocar cuando cargue
      const onLoadedTmp = () => { try { URL.revokeObjectURL(objectUrl); } catch(e){}; previewVideo.removeEventListener('loadeddata', onLoadedTmp); };
      previewVideo.addEventListener('loadeddata', onLoadedTmp);
    } else {
      try { if (objectUrl) URL.revokeObjectURL(objectUrl); } catch(e){}
    }

    return { success: true, data };
  } catch (err) {
    console.error('Error en uploadVideo:', err);
    try { mostrarToast && mostrarToast('Error al subir el video', 'error'); } catch(e){}
    return { success: false, error: String(err) };
  }
}

// Wrapper que recibe el <input type="file"> y determina exerciseId desde el DOM
function uploadVideoFromInput(fileInput) {
  if (!fileInput || !fileInput.files || !fileInput.files[0]) return;
  const file = fileInput.files[0];

  // Buscar el elemento ejercicio padre
  const ejercicioElem = fileInput.closest('.ejercicio-item');
  let exerciseId = null;
  if (ejercicioElem) {
    // Intentar leer data-ejercicio-id o id en formato 'ejercicio-<id>' o atributo data-id
    exerciseId = ejercicioElem.dataset.ejercicioId || ejercicioElem.dataset.id || (ejercicioElem.id && ejercicioElem.id.replace(/^ejercicio-/, '')) || null;

    // Si existen elementos preview/input sin ids, asignar ids para futuras referencias
    if (exerciseId) {
      const preview = ejercicioElem.querySelector('.video-preview');
      if (preview) preview.id = preview.id || `preview-video-${exerciseId}`;
      const hidden = ejercicioElem.querySelector('.video-url');
      if (hidden) hidden.id = hidden.id || `video-url-${exerciseId}`;
    }
  }

  // Llamar al uploader principal
  return uploadVideo(file, exerciseId);
}

// Inicializar previews para ejercicios que ya tengan video_url al abrir el modal o al cargar la página
function initializeExercisePreviews(root = document) {
  const items = root.querySelectorAll('.ejercicio-item');
  items.forEach(item => {
    const hidden = item.querySelector('.video-url');
    const preview = item.querySelector('video');
    const status = item.querySelector('.video-status');
    if (hidden && hidden.value) {
      if (preview) {
        preview.src = hidden.value;
        preview.classList.remove('hidden');
        preview.style.display = 'block';
      }
      if (status) status.textContent = '✅ Video cargado';
    } else {
      if (preview) {
        // ocultar por defecto si no hay video
        preview.classList.add('hidden');
        preview.style.display = 'none';
      }
      if (status) status.textContent = '';
    }
  });
}

// Delegación: cuando cambie cualquier input.file con clase .video-file-input, llamar al wrapper
document.addEventListener('change', function(e) {
  const t = e.target;
  if (t && t.matches && t.matches('.video-file-input')) {
    uploadVideoFromInput(t);
  }
});

// Asegurar que los formularios usen nuestras funciones y cargar alumnos cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
  try {
        // avoid double-binding if this script is loaded more than once
        if (window._rutinaFormBound) return;
        window._rutinaFormBound = true;

        const formEditar = document.getElementById('formEditarRutina');
        if (formEditar) {
          formEditar.addEventListener('submit', function(e){ e.preventDefault(); actualizarRutina(e); });
        }
        const formNueva = document.getElementById('formNuevaRutina');
        if (formNueva) {
          formNueva.addEventListener('submit', function(e){ e.preventDefault(); guardarRutina(e); });
          // cargar alumnos para el modal de creación si existe select
          try { cargarAlumnos([]); } catch(e) { /* ignore */ }
        }
  } catch (e) { /* ignore */ }
});

// Guard against duplicate submissions: mark form while submitting
function _markFormSubmitting(form, val){ try{ if(!form) return; form.dataset.rutinaSubmitting = val ? '1' : '0'; }catch(e){} }

// Ejecutar inicialización al cargar DOM
document.addEventListener('DOMContentLoaded', function() {
  try { initializeExercisePreviews(); } catch (e) {}
});