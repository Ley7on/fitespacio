// Routine editor modal and delete confirmation
(function(){
    function getCSRF(){
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || (function(){
            const m = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/); return m ? decodeURIComponent(m[1]) : null;
        })();
    }

    function buildModalHtml(){
        return `
        <div class="rs-modal-overlay" style="position:fixed;inset:0;background:rgba(2,6,23,0.6);z-index:1060;display:flex;align-items:center;justify-content:center;">
          <div class="rs-modal" role="dialog" aria-modal="true" style="background:#0b0f1a;color:#fff;border-radius:10px;max-width:820px;width:92%;box-shadow:0 12px 40px rgba(2,6,23,0.8);">
            <div style="padding:18px 20px;border-bottom:1px solid rgba(255,255,255,0.04);display:flex;justify-content:space-between;align-items:center;">
              <strong id="rs-modal-title">Editar Rutina</strong>
              <button id="rs-modal-close" aria-label="Cerrar" style="background:transparent;border:none;color:#fff;font-size:16px;cursor:pointer;">✕</button>
            </div>
            <div style="padding:18px;">
              <form id="rs-modal-form">
                <div style="display:flex;gap:12px;flex-wrap:wrap;">
                  <div style="flex:2;min-width:200px;">
                    <label class="form-label">Nombre</label>
                    <input name="nombre" class="form-control" style="width:100%;padding:10px;border-radius:8px;background:#0b1220;border:1px solid rgba(255,255,255,0.06);color:#fff;" />
                    <div class="error nombre-error" style="color:#fca5a5;font-size:0.85rem;margin-top:6px;display:none;"></div>
                  </div>
                  <div style="flex:1;min-width:160px;">
                    <label class="form-label">Objetivo</label>
                    <select name="objetivo" class="form-control" style="width:100%;padding:10px;border-radius:8px;background:#0b1220;border:1px solid rgba(255,255,255,0.06);color:#fff;">
                      <option value="fuerza">Fuerza</option>
                      <option value="hipertrofia">Hipertrofia</option>
                      <option value="resistencia">Resistencia</option>
                      <option value="perdida_grasa">Pérdida de Grasa</option>
                      <option value="funcional">Funcional</option>
                    </select>
                  </div>
                  <div style="flex:1;min-width:160px;">
                    <label class="form-label">Día asignado</label>
                    <select name="dia_asignado" class="form-control" style="width:100%;padding:10px;border-radius:8px;background:#0b1220;border:1px solid rgba(255,255,255,0.06);color:#fff;">
                      <option value="">Sin asignar</option>
                      <option value="lunes">Lunes</option>
                      <option value="martes">Martes</option>
                      <option value="miercoles">Miércoles</option>
                      <option value="jueves">Jueves</option>
                      <option value="viernes">Viernes</option>
                      <option value="sabado">Sábado</option>
                      <option value="domingo">Domingo</option>
                    </select>
                  </div>
                </div>

                <div style="margin-top:12px;">
                  <label class="form-label">Descripción</label>
                  <textarea name="descripcion" rows="4" style="width:100%;padding:10px;border-radius:8px;background:#0b1220;border:1px solid rgba(255,255,255,0.06);color:#fff;"></textarea>
                </div>

                <div style="margin-top:14px;display:flex;gap:8px;justify-content:flex-end;">
                  <button type="button" id="rs-modal-cancel" class="btn btn-secondary">Cancelar</button>
                  <button type="submit" id="rs-modal-save" class="btn btn-primary">Guardar</button>
                </div>
              </form>
            </div>
          </div>
        </div>
        `;
    }

    function openEditor(rutinaId){
        // create modal
        const wrapper = document.createElement('div'); wrapper.innerHTML = buildModalHtml();
        document.body.appendChild(wrapper);
        const overlay = wrapper.querySelector('.rs-modal-overlay');
        const form = wrapper.querySelector('#rs-modal-form');
        const closeBtn = wrapper.querySelector('#rs-modal-close');
        const cancelBtn = wrapper.querySelector('#rs-modal-cancel');
        const saveBtn = wrapper.querySelector('#rs-modal-save');

        // focus trap
        const firstInput = form.querySelector('[name=nombre]'); setTimeout(()=> firstInput.focus(),50);

    // wire handlers and ensure they are removed when modal closes to avoid leaks
    function cleanup(){
      try{
        // remove document-level listener
        document.removeEventListener('keydown', escHandler);
      }catch(e){}
      try{ closeBtn.removeEventListener('click', onClose); }catch(e){}
      try{ cancelBtn.removeEventListener('click', onClose); }catch(e){}
      try{ overlay.removeEventListener('click', onOverlayClick); }catch(e){}
      wrapper.remove();
    }

    const onClose = () => cleanup();
    const onOverlayClick = (e) => { if (e.target === overlay) cleanup(); };
    const escHandler = (e) => { if (e.key === 'Escape') cleanup(); };

    closeBtn.addEventListener('click', onClose);
    cancelBtn.addEventListener('click', onClose);
    overlay.addEventListener('click', onOverlayClick);
    document.addEventListener('keydown', escHandler);

    // load rutina detail (with timeout). IMPORTANT: do not auto-close the modal on failure — keep it open so user can still edit
    (function(){
      const controller = new AbortController();
      const timeoutId = setTimeout(()=> controller.abort(), 5000);
      fetch(`/alumno/api/rutina/${rutinaId}/detalle/`, { credentials: 'same-origin', signal: controller.signal, headers: { 'Accept': 'application/json' } })
      .then(r=>{
        clearTimeout(timeoutId);
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(data=>{
        if (!data || !data.success){
          // keep modal open, surface a non-blocking error
          window.toast.error('Error','Rutina no encontrada o sin permisos');
          return;
        }
        const rdata = data.rutina || {};
        form.querySelector('[name=nombre]').value = rdata.nombre || '';
        form.querySelector('[name=descripcion]').value = (rdata.descripcion && typeof rdata.descripcion === 'string') ? rdata.descripcion : '';
        form.querySelector('[name=objetivo]').value = (rdata.objetivo || 'fuerza');
        form.querySelector('[name=dia_asignado]').value = rdata.dia_asignado || '';
      })
      .catch(err=>{
        clearTimeout(timeoutId);
        if (err.name === 'AbortError'){
          console.warn('rutina detalle: request aborted (timeout)');
          window.toast.warning('Toma mucho tiempo','No se pudo cargar la rutina rápidamente; intenta de nuevo');
          return;
        }
        console.error('Error cargando rutina detalle:', err);
        // keep modal open and let user edit manually
        window.toast.error('Error','No se pudo cargar la rutina — puedes editar manualmente');
      });
    })();

        form.addEventListener('submit', function(ev){
            ev.preventDefault();
            saveBtn.disabled = true; saveBtn.textContent = 'Guardando...';
            const payload = {
                nombre: form.querySelector('[name=nombre]').value.trim(),
                descripcion: form.querySelector('[name=descripcion]').value.trim(),
                dia_asignado: form.querySelector('[name=dia_asignado]').value || '',
                objetivo: form.querySelector('[name=objetivo]').value
            };
            const csrftoken = getCSRF();
      fetch(`/alumno/api/rutina/${rutinaId}/editar/`, { // use API edit endpoint
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type':'application/json', 'X-CSRFToken': csrftoken },
                body: JSON.stringify(payload)
            }).then(r=> r.json())
            .then(result=>{
                if (result && result.success){
                    window.toast.success('Rutina actualizada','Los cambios fueron guardados');
                    // refresh lists
                    if (window.cargarRutinasPersonales) window.cargarRutinasPersonales();
                    if (window.cargarCalendarioSemanal) window.cargarCalendarioSemanal();
                    cleanup();
                } else {
                    const msg = (result && (result.message || result.error)) || 'Error al guardar';
                    window.toast.error('Error', msg);
                    saveBtn.disabled = false; saveBtn.textContent = 'Guardar';
                }
            }).catch(err=>{ console.error(err); window.toast.error('Error','Fallo de red al guardar'); saveBtn.disabled=false; saveBtn.textContent='Guardar'; });
        });
    }

    function confirmDelete(rutinaId, nombre){
        // show a prettier confirm modal instead of native confirm()
        showConfirm(`¿Eliminar la rutina '${nombre}'? Esta acción es permanente.`, { title: 'Eliminar rutina', confirmText: 'Eliminar', cancelText: 'Cancelar', danger: true })
        .then(ok=>{
            if (!ok) return;
            const csrftoken = getCSRF();
            // call delete endpoint (we added DELETE on the resource)
            fetch(`/alumno/api/rutina/${rutinaId}/`, {
              method: 'DELETE', credentials: 'same-origin', headers: {'Content-Type':'application/json','X-CSRFToken':csrftoken}
            }).then(async r=> {
              // handle 204 or JSON
              if (r.status === 204) return { success: true };
              try { return await r.json(); } catch(e){ return { success: r.ok, message: r.statusText }; }
            }).then(res=>{
                    if (res && res.success){
                        // optimistic remove
                        if (window.cargarRutinasPersonales) window.cargarRutinasPersonales();
                        if (window.cargarRutinasAsignadas) window.cargarRutinasAsignadas();
                        window.toast.success('Rutina eliminada', res.message || 'La rutina fue eliminada', { actions: [ { label: 'Deshacer', onClick: ()=>{
                            // try to restore via editar endpoint (activa=true)
                            fetch(`/alumno/api/rutina/${rutinaId}/editar/`, { method: 'POST', credentials: 'same-origin', headers: {'Content-Type':'application/json','X-CSRFToken':csrftoken}, body: JSON.stringify({activa:true}) }).then(()=>{ window.cargarRutinasPersonales && window.cargarRutinasPersonales(); window.toast.success('Restaurada','Rutina restaurada'); }).catch(()=>{ window.toast.error('No se pudo restaurar','Intenta más tarde'); });
                        }} ] });
                    } else {
                        const msg = (res && (res.message || res.error)) || 'Error al eliminar';
                        window.toast.error('No se pudo eliminar', msg);
                    }
                }).catch(err=>{ console.error(err); window.toast.error('Error','Fallo de red al eliminar'); });
        });
    }

    // prettier confirm modal that returns a Promise<boolean>
    function showConfirm(message, opts){
        opts = Object.assign({ title: '', confirmText: 'OK', cancelText: 'Cancelar', danger: false }, opts || {});
        return new Promise((resolve)=>{
            const wrapper = document.createElement('div');
            wrapper.innerHTML = `
            <div class="rs-confirm-overlay" style="position:fixed;inset:0;background:rgba(2,6,23,0.6);z-index:1070;display:flex;align-items:center;justify-content:center;">
              <div class="rs-confirm" role="dialog" aria-modal="true" style="background:#0f1724;color:#fff;border-radius:12px;max-width:520px;width:92%;box-shadow:0 18px 50px rgba(2,6,23,0.9);border:1px solid rgba(255,255,255,0.03);overflow:hidden;">
                <div style="padding:16px 18px;border-bottom:1px solid rgba(255,255,255,0.03);display:flex;align-items:center;gap:12px;">
                  <div style="width:44px;height:44px;border-radius:8px;background:${opts.danger? 'linear-gradient(180deg,#16a34a,#059669)' : 'linear-gradient(180deg,#134e4a,#0ea5a0)'};display:flex;align-items:center;justify-content:center;font-weight:700;">${opts.danger? '!' : '?'}</div>
                  <div style="flex:1;">
                    <div style="font-weight:600;font-size:1rem;">${opts.title || ''}</div>
                    <div style="font-size:0.95rem;color:rgba(255,255,255,0.85);margin-top:6px;">${message}</div>
                  </div>
                </div>
                <div style="padding:14px 18px;display:flex;gap:8px;justify-content:flex-end;background:linear-gradient(180deg,rgba(255,255,255,0.01),transparent);">
                  <button type="button" class="rs-confirm-cancel" style="background:transparent;border:1px solid rgba(255,255,255,0.06);color:#cbd5e1;padding:8px 12px;border-radius:8px;cursor:pointer;">${opts.cancelText}</button>
                  <button type="button" class="rs-confirm-ok" style="background:${opts.danger? '#16a34a' : '#06b6d4'};border:none;color:#ffffff;padding:8px 14px;border-radius:8px;cursor:pointer;font-weight:600;">${opts.confirmText}</button>
                </div>
              </div>
            </div>
            `;
            document.body.appendChild(wrapper);
            const overlay = wrapper.querySelector('.rs-confirm-overlay');
            const okBtn = wrapper.querySelector('.rs-confirm-ok');
            const cancelBtn = wrapper.querySelector('.rs-confirm-cancel');

            function cleanup(){ wrapper.remove(); document.removeEventListener('keydown', keyHandler); }
            function keyHandler(e){ if (e.key === 'Escape'){ cleanup(); resolve(false); } }
            document.addEventListener('keydown', keyHandler);

            overlay.addEventListener('click', (e)=>{ if (e.target === overlay){ cleanup(); resolve(false); } });
            cancelBtn.addEventListener('click', ()=>{ cleanup(); resolve(false); });
            okBtn.addEventListener('click', ()=>{ cleanup(); resolve(true); });

            // focus
            okBtn.focus();
        });
    }

  // expose helper globally so other scripts can reuse the prettier confirm modal
  window.showConfirm = showConfirm;
  window.rsModal = { openEditor, confirmDelete };
})();
