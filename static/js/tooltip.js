(function () {
  var MARGIN = 8; // separación mínima con los bordes de la pantalla (px)
  var triggers = document.querySelectorAll('.tooltip-trigger');

  // Barra superior fija/sticky de ancho completo (la de móvil); 0 si no hay
  function topLimit() {
    var bar = document.querySelector('.sidebar');
    if (!bar) return 0;
    var pos = getComputedStyle(bar).position;
    if (pos !== 'sticky' && pos !== 'fixed') return 0;
    var r = bar.getBoundingClientRect();
    return r.width >= window.innerWidth * 0.9 ? Math.max(0, r.bottom) : 0;
  }

  function place(trigger) {
    var box = trigger.querySelector('.tooltip-box');
    if (!box) return;

    // Se calcula desde el botón y el tamaño de la caja (offsetWidth/Height no
    // dependen de transform), así la medición no se altera durante la animación.
    var tr = trigger.getBoundingClientRect();
    var w = box.offsetWidth, h = box.offsetHeight;
    var vw = document.documentElement.clientWidth;
    var center = tr.left + tr.width / 2;

    // Horizontal: mantener la caja dentro de la pantalla
    var left = center - w / 2, right = center + w / 2, shift = 0;
    if (left < MARGIN) shift = MARGIN - left;
    else if (right > vw - MARGIN) shift = (vw - MARGIN) - right;
    box.style.setProperty('--tt-shift', shift + 'px');

    // Vertical: si no cabe arriba (borde o barra superior), abrir hacia abajo
    var topIfAbove = tr.top - 8 - h;
    trigger.classList.toggle('is-below', topIfAbove < topLimit() + MARGIN);
  }

  function closeAll(except) {
    triggers.forEach(function (t) {
      if (t !== except) t.classList.remove('is-open');
    });
  }

  triggers.forEach(function (t) {
    t.addEventListener('mouseenter', function () { place(t); });
    t.addEventListener('focus', function () { place(t); });
    // En móvil no hay hover, y Safari no da foco a los botones al tocarlos
    t.addEventListener('click', function (e) {
      e.stopPropagation();
      var open = !t.classList.contains('is-open');
      closeAll(t);
      t.classList.toggle('is-open', open);
      if (open) place(t);
    });
  });

  document.addEventListener('click', function () { closeAll(); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeAll(); });
  // Un tooltip abierto en móvil se cierra al hacer scroll para no quedar flotando mal colocado
  window.addEventListener('scroll', function () { closeAll(); }, { passive: true });
  window.addEventListener('resize', function () {
    triggers.forEach(function (t) { if (t.classList.contains('is-open')) place(t); });
  });
})();