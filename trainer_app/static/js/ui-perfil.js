// Función para sanitizar HTML
function sanitizeHTML(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// Toggle edición Perfil + toasts y validaciones mock
(() => {
  const $ = (s) => document.querySelector(s);

  const view = $('#profileView');
  const form = $('#profileForm');
  $('#btnEditProfile')?.addEventListener('click', () => {
    view?.classList.add('d-none'); form?.classList.remove('d-none');
  });
  $('#btnCancelEdit')?.addEventListener('click', () => {
    form?.classList.add('d-none'); view?.classList.remove('d-none');
  });

  $('#btnSaveProfile')?.addEventListener('click', () => {
    // Validación mínima
    const email = $('#fEmail')?.value?.trim();
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      toast('Correo inválido'); return;
    }
    toast('Cambios guardados localmente (demo)');
    form?.classList.add('d-none'); view?.classList.remove('d-none');
  });

  $('#btnChangePwd')?.addEventListener('click', () => {
    const n1 = $('#pwdNew1')?.value || '';
    const n2 = $('#pwdNew2')?.value || '';
    if (n1.length < 8) return toast('La nueva contraseña debe tener al menos 8 caracteres');
    if (n1 !== n2) return toast('Las contraseñas no coinciden');
    toast('Contraseña actualizada (demo)');
  });

  $('#btnSavePrefs')?.addEventListener('click', () => {
    toast('Preferencias guardadas (demo)');
  });

  function toast(msg){
    const wrap = document.createElement('div');
    wrap.className = 'toast fitspace align-items-center border-0 position-fixed bottom-0 end-0 m-3 show';
    wrap.role = 'alert';
    wrap.ariaLive = 'assertive';
    wrap.ariaAtomic = 'true';
    wrap.innerHTML = `
      <div class="d-flex">
        <div class="toast-body">${sanitizeHTML(msg)}</div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Cerrar"></button>
      </div>`;
    document.body.appendChild(wrap);
    setTimeout(()=> wrap.remove(), 2600);
  }
})();
