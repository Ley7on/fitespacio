// Lightweight toast/notification system
(function(){
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.setAttribute('aria-live','polite');
    container.style.position = 'fixed';
    container.style.top = '1rem';
    container.style.right = '1rem';
    container.style.zIndex = 1055;
    container.style.display = 'flex';
    container.style.flexDirection = 'column';
    container.style.gap = '0.5rem';
    document.addEventListener('DOMContentLoaded', ()=> document.body.appendChild(container));

    function createToast(type, title, message, options={}){
        const id = 'toast-' + Date.now() + '-' + Math.floor(Math.random()*1000);
        const el = document.createElement('div');
        el.className = `toast toast-${type}`;
        el.id = id;
        el.setAttribute('role','status');
        el.setAttribute('aria-atomic','true');
        el.style.minWidth = '260px';
        el.style.maxWidth = '420px';
        el.style.background = type === 'success' ? '#0f172a' : (type === 'error' ? '#2b0b0b' : '#0f172a');
        el.style.color = '#fff';
        el.style.padding = '12px 14px';
        el.style.borderRadius = '8px';
        el.style.boxShadow = '0 6px 18px rgba(2,6,23,0.6)';
        el.style.display = 'flex';
        el.style.flexDirection = 'column';

        const header = document.createElement('div');
        header.style.display='flex'; header.style.justifyContent='space-between'; header.style.alignItems='center';
        const titleEl = document.createElement('strong'); titleEl.textContent = title || '';
        titleEl.style.fontSize = '0.95rem';
        const closeBtn = document.createElement('button'); closeBtn.innerHTML = '✕';
        closeBtn.style.background='transparent'; closeBtn.style.border='none'; closeBtn.style.color='inherit'; closeBtn.style.cursor='pointer';
        closeBtn.setAttribute('aria-label','Cerrar notificación');
        closeBtn.onclick = ()=> removeToast(id);
        header.appendChild(titleEl); header.appendChild(closeBtn);

        const msg = document.createElement('div'); msg.style.marginTop='6px'; msg.style.fontSize='0.9rem'; msg.innerHTML = message || '';

        el.appendChild(header); el.appendChild(msg);

        // actions
        if (options.actions && Array.isArray(options.actions) && options.actions.length){
            const actionsWrapper = document.createElement('div'); actionsWrapper.style.marginTop='8px'; actionsWrapper.style.display='flex'; actionsWrapper.style.gap='8px';
            options.actions.forEach(a=>{
                const b = document.createElement('button'); b.textContent = a.label; b.className='toast-action';
                b.style.background='rgba(255,255,255,0.06)'; b.style.color='white'; b.style.border='1px solid rgba(255,255,255,0.06)'; b.style.padding='6px 10px'; b.style.borderRadius='6px'; b.style.cursor='pointer';
                b.onclick = ()=>{ try{ a.onClick(); } catch(e){ console.error(e);} removeToast(id); };
                actionsWrapper.appendChild(b);
            });
            el.appendChild(actionsWrapper);
        }

        container.appendChild(el);

        const timeout = (options.timeout === 0) ? 0 : (options.timeout || 4500);
        if (timeout>0){
            const t = setTimeout(()=> removeToast(id), timeout);
            el.addEventListener('mouseenter', ()=> clearTimeout(t));
        }

        function removeToast(id){
            const node = document.getElementById(id);
            if (!node) return;
            node.style.transition = 'opacity 200ms ease, transform 200ms ease';
            node.style.opacity='0'; node.style.transform='translateY(-6px)';
            setTimeout(()=> node.remove(), 210);
        }

        return {id, remove: ()=> removeToast(id)};
    }

    window.toast = {
        success: (t,m,o)=> createToast('success', t, m, o),
        error: (t,m,o)=> createToast('error', t, m, o),
        info: (t,m,o)=> createToast('info', t, m, o),
        warning: (t,m,o)=> createToast('warning', t, m, o),
        raw: createToast
    };
})();
