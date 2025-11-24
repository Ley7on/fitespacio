// Guardar en: backend/trainer_app/static/js/test-calendario.js
// Uso: Agregar <script src="{% static 'js/test-calendario.js' %}"></script> en calendario.html temporal para testing

console.log('%c=== TEST CALENDARIO FITSPACE ===', 'color: #06b6d4; font-size: 16px; font-weight: bold;');

// Test 1: Verificar elementos del DOM
console.log('%cTest 1: Elementos del DOM', 'color: #10b981; font-weight: bold;');
const modal = document.getElementById('modalNuevoEvento');
const form = document.getElementById('formNuevoEvento');
const titulo = document.getElementById('eventoTitulo');
const tipo = document.getElementById('eventoTipo');
const fecha = document.getElementById('eventoFecha');
const horaInicio = document.getElementById('eventoHoraInicio');
const horaFin = document.getElementById('eventoHoraFin');
const descripcion = document.getElementById('eventoDescripcion');
const color = document.getElementById('eventoColor');

console.log(`  Modal: ${modal ? '✓' : '✗'} ${modal ? modal.id : 'NO ENCONTRADO'}`);
console.log(`  Form: ${form ? '✓' : '✗'} ${form ? form.id : 'NO ENCONTRADO'}`);
console.log(`  Título input: ${titulo ? '✓' : '✗'}`);
console.log(`  Tipo select: ${tipo ? '✓' : '✗'}`);
console.log(`  Fecha input: ${fecha ? '✓' : '✗'}`);
console.log(`  Hora inicio: ${horaInicio ? '✓' : '✗'}`);
console.log(`  Hora fin: ${horaFin ? '✓' : '✗'}`);
console.log(`  Descripción: ${descripcion ? '✓' : '✗'}`);
console.log(`  Color: ${color ? '✓' : '✗'}`);

// Test 2: Verificar funciones
console.log('%cTest 2: Funciones JavaScript', 'color: #10b981; font-weight: bold;');
console.log(`  nuevoEvento: ${typeof nuevoEvento === 'function' ? '✓' : '✗'}`);
console.log(`  cerrarModalEvento: ${typeof cerrarModalEvento === 'function' ? '✓' : '✗'}`);
console.log(`  guardarEvento: ${typeof guardarEvento === 'function' ? '✓' : '✗'}`);
console.log(`  cargarEventos: ${typeof cargarEventos === 'function' ? '✓' : '✗'}`);
console.log(`  generarCalendario: ${typeof generarCalendario === 'function' ? '✓' : '✗'}`);

// Test 3: Verificar CSRF Token
console.log('%cTest 3: Seguridad CSRF', 'color: #10b981; font-weight: bold;');
const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
console.log(`  CSRF Token presente: ${csrfToken ? '✓' : '✗'}`);
if (csrfToken) {
  console.log(`  Token value: ${csrfToken.value.substring(0, 20)}...`);
}

// Test 4: Verificar endpoint
console.log('%cTest 4: Endpoint API', 'color: #10b981; font-weight: bold;');
fetch('/api/eventos/', {
  headers: {
    'X-CSRFToken': csrfToken ? csrfToken.value : ''
  }
})
  .then(r => {
    console.log(`  GET /api/eventos/: ✓ (${r.status})`);
    return r.json();
  })
  .then(data => {
    console.log(`  Eventos cargados: ${data.length || data.length === 0 ? '✓' : '?'} (${Array.isArray(data) ? data.length : 'N/A'} eventos)`);
  })
  .catch(e => console.log(`  Error al cargar eventos: ✗ ${e.message}`));

// Test 5: Simular modal
console.log('%cTest 5: Simulación de Modal', 'color: #10b981; font-weight: bold;');
console.log('  Ejecuta esto en la consola para probar:');
console.log('  → nuevoEvento()  // Abre el modal');
console.log('  → cerrarModalEvento()  // Cierra el modal');

// Test 6: Rellenar formulario para prueba
console.log('%cTest 6: Función helper para pruebas', 'color: #10b981; font-weight: bold;');
window.testForm = function() {
  if (!titulo || !tipo || !fecha || !horaInicio || !horaFin) {
    console.error('❌ Formulario no está completo en el DOM');
    return false;
  }
  
  const hoy = new Date().toISOString().split('T')[0];
  titulo.value = 'Test Evento ' + new Date().getTime();
  tipo.value = 'sesion';
  fecha.value = hoy;
  horaInicio.value = '10:00';
  horaFin.value = '11:00';
  descripcion.value = 'Evento de prueba automática';
  color.value = '#06b6d4';
  
  console.log('✓ Formulario rellenado con datos de prueba');
  console.log('  Ahora ejecuta: guardarEvento({preventDefault: () => {}})');
  return true;
};

console.log('%c✅ Tests completados', 'color: #06b6d4; font-size: 14px; font-weight: bold;');
console.log('Ejecuta testForm() para rellenar el formulario con datos de prueba');
