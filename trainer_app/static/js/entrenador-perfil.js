document.addEventListener('DOMContentLoaded', function() {
  function editarPerfil() {
    const modal = document.getElementById('modalEditarPerfil'); if(modal) modal.classList.remove('hidden');
  }

  function cerrarModalEditar() {
    const modal = document.getElementById('modalEditarPerfil'); if(modal) modal.classList.add('hidden');
  }

  function cambiarContrasena() {
    const modal = document.getElementById('modalCambiarContrasena'); 
    if(modal) modal.classList.remove('hidden');
  }

  function cerrarModalContrasena() {
    const modal = document.getElementById('modalCambiarContrasena'); 
    if(modal) modal.classList.add('hidden');
  }

  const form = document.getElementById('formEditarPerfil');
  if (form) {
    form.addEventListener('submit', function(e) {
      e.preventDefault();
      const formData = new FormData(this);

      fetch('/actualizar-perfil/', {
        method: 'POST',
        body: formData,
        headers: {
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
        }
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          alert('Perfil actualizado exitosamente');
          location.reload();
        } else {
          alert('Error: ' + (data.message || 'Error desconocido'));
        }
      })
      .catch(error => {
        console.error('Error:', error);
        alert('Error de conexión');
      });
    });
  }

  // Cerrar modales al hacer clic fuera
  const modalEditar = document.getElementById('modalEditarPerfil');
  if (modalEditar) {
    modalEditar.addEventListener('click', function(e) {
      if (e.target === this) cerrarModalEditar();
    });
  }

  const modalContrasena = document.getElementById('modalCambiarContrasena');
  if (modalContrasena) {
    modalContrasena.addEventListener('click', function(e) {
      if (e.target === this) cerrarModalContrasena();
    });
  }

  // Expose small helpers to the template buttons
  window.editarPerfil = editarPerfil;
  window.cerrarModalEditar = cerrarModalEditar;
  window.cambiarContrasena = cambiarContrasena;
  window.cerrarModalContrasena = cerrarModalContrasena;

  console.log('Entrenador perfil JS loaded');
});
