document.addEventListener('DOMContentLoaded', () => {
  const el = document.getElementById('fullcalendar');
  if (!el) return;

  // Paleta de tipos
  const TYPE = {
    workout: { bg: '#4f8cff', text: '#ffffff' },
    rest:    { bg: 'rgba(255,107,154,.35)', text: '#ffffff' },
    event:   { bg: '#2ee59d', text: '#0a2b1d' }
  };

  // Modal y refs
  const modalEl  = document.getElementById('eventModal');
  const modal    = new bootstrap.Modal(modalEl);
  const titleEl  = document.getElementById('eventTitle');
  const datesEl  = document.getElementById('eventDates');
  const notesEl  = document.getElementById('eventNotes');
  const deleteBtn= document.getElementById('eventDeleteBtn');
  let selectedEvent = null;

  // Calendario
  const cal = new FullCalendar.Calendar(el, {
    themeSystem: 'bootstrap5',
    initialView: 'dayGridMonth',
    headerToolbar: false,
    locale: 'es',
    firstDay: 1,
    height: 'auto',
    dayMaxEventRows: 3,
    nowIndicator: true,
    editable: true,
    selectable: true,

    events: [
      ...[1,3,5,8,10,12,15,18,22,25,29].map(d => ev('Entrenamiento', d, 'workout', 'Fuerza + core')),
      ...[7,14,21,28].map(d => bgDay('Descanso', d, 'rest', 'Movilidad suave')),
      single('Test 1RM', 9, 'event', 'Sentadilla + banca'),
    ],

    // Etiqueta visible para background events (Descanso)
    eventContent: function(arg) {
      if (arg.event.display === 'background') {
        const wrap = document.createElement('div');
        wrap.className = 'fc-rest-label';
        wrap.textContent = arg.event.title || 'Descanso';
        return { domNodes: [wrap] };
      }
      return true;
    },

    dateClick(info) {
      try {
        cal.addEvent({
          title: 'Nuevo entrenamiento',
          start: info.dateStr,
          backgroundColor: TYPE.workout.bg,
          borderColor: TYPE.workout.bg,
          textColor: TYPE.workout.text,
          extendedProps: { kind: 'workout', notes: 'Por definir' },
        });
      } catch (error) {
        console.error('Error al agregar evento:', error);
      }
    },

    // Click en evento normal -> abrir modal
    eventClick(info) {
      if (info.event.display === 'background') return; // no modal para descanso
      selectedEvent = info.event;
      fillModal(selectedEvent);
      modal.show();
    }
  });

  cal.render();

  // Navegación externa
  document.getElementById('btn-today')?.addEventListener('click', () => cal.today());
  document.getElementById('btn-prev')?.addEventListener('click', () => cal.prev());
  document.getElementById('btn-next')?.addEventListener('click', () => cal.next());

  // Cerrar modal al navegar/drag/resize para evitar overlays colgados
  cal.on('datesSet', () => { safeHideModal(); selectedEvent = null; });
  cal.on('eventDragStart', () => safeHideModal());
  cal.on('eventResizeStart', () => safeHideModal());

  // Eliminar evento (usar modal bonito)
  deleteBtn?.addEventListener('click', () => {
    if (!selectedEvent) return;
    // use global showConfirm (provided by routineModal.js) — shim guarantees it exists
    window.showConfirm('¿Eliminar este entrenamiento?', { title: 'Eliminar entrenamiento', confirmText: 'Eliminar', cancelText: 'Cancelar', danger: true })
    .then(ok => {
      if (!ok) return;
      try {
        selectedEvent.remove();
        selectedEvent = null;
        safeHideModal();
      } catch (error) {
        console.error('Error al eliminar evento:', error);
      }
    });
  });

  // Utilidades
  function safeHideModal(){
    const inst = bootstrap.Modal.getInstance(modalEl);
    if (inst) inst.hide();
  }

  function fillModal(e){
    titleEl.textContent = e.title || 'Evento';
    datesEl.textContent = formatRange(e.start, e.end || e.start, e.allDay);
    notesEl.textContent = e.extendedProps?.notes || 'Sin notas';
  }

  function pad(n){ return String(n).padStart(2,'0'); }
  function ymd(y,m,d){ return `${y}-${pad(m)}-${pad(d)}`; }
  function monthDate(d){
    const now = new Date();
    return ymd(now.getFullYear(), now.getMonth()+1, d);
  }
  function ev(title, d, kind, notes){
    return {
      title,
      start: monthDate(d),
      backgroundColor: TYPE[kind].bg,
      borderColor: TYPE[kind].bg,
      textColor: TYPE[kind].text,
      extendedProps: { kind, notes }
    };
  }
  function bgDay(title, d, kind, notes){
    return {
      title,
      start: monthDate(d),
      end: monthDate(d+1),
      display: 'background',
      backgroundColor: TYPE[kind].bg,
      extendedProps: { kind: 'rest-bg', notes }
    };
  }
  function single(title, d, kind, notes){ return ev(title, d, kind, notes); }

  function formatRange(start, end, allDay){
    if (allDay) {
      const s = start.toLocaleDateString('es-ES', { day:'2-digit', month:'short', year:'numeric' });
      const e = end.toLocaleDateString('es-ES', { day:'2-digit', month:'short', year:'numeric' });
      return s === e ? s : `${s} – ${e}`;
    }
    const fmt = d => d.toLocaleString('es-ES', { dateStyle:'medium', timeStyle:'short' });
    return start && end ? `${fmt(start)} — ${fmt(end)}` : fmt(start || new Date());
  }
});
