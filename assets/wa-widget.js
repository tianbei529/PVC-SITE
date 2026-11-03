/* Tianbei WhatsApp chat widget — self-contained, no deps.
   Reads data-product / data-wa / data-msg from #wa-widget, builds a
   mini chat panel. Quick replies + typed message open wa.me prefilled. */
(function () {
  var root = document.getElementById('wa-widget');
  if (!root) return;
  var wa = root.getAttribute('data-wa') || '8615893110948';
  var name = root.getAttribute('data-name') || 'Anna';
  var product = root.getAttribute('data-product') || '';

  var svgSend = '<svg viewBox="0 0 24 24" width="19" height="19" fill="currentColor" aria-hidden="true"><path d="M2.01 21 23 12 2.01 3 2 10l15 2-15 2z"/></svg>';
  var svgWa = '<svg viewBox="0 0 24 24" width="30" height="30" fill="currentColor" aria-hidden="true"><path d="M17.47 14.38c-.3-.15-1.75-.86-2.02-.96-.27-.1-.47-.15-.67.15-.2.3-.77.96-.95 1.16-.17.2-.35.22-.65.07-.3-.15-1.25-.46-2.38-1.47-.88-.79-1.48-1.76-1.65-2.06-.17-.3-.02-.46.13-.61.13-.13.3-.35.45-.52.15-.17.2-.3.3-.5.1-.2.05-.37-.02-.52-.08-.15-.67-1.6-.92-2.19-.24-.58-.49-.5-.67-.51h-.57c-.2 0-.52.07-.79.37-.27.3-1.04 1.01-1.04 2.47 0 1.46 1.06 2.87 1.21 3.07.15.2 2.09 3.19 5.07 4.47.71.31 1.26.49 1.69.63.71.22 1.36.19 1.87.12.57-.08 1.75-.71 1.99-1.4.25-.69.25-1.28.17-1.4-.07-.13-.27-.2-.57-.35zM12.05 21.5h-.01a9.4 9.4 0 01-4.78-1.31l-.34-.2-3.55.93.95-3.46-.22-.36a9.37 9.37 0 01-1.44-5.01c0-5.18 4.22-9.4 9.4-9.4 2.51 0 4.87.98 6.64 2.75a9.33 9.33 0 012.75 6.65c0 5.18-4.22 9.4-9.4 9.4zM20.36 3.6A11.8 11.8 0 0012.05 0C5.5 0 .17 5.33.17 11.88c0 2.09.55 4.14 1.59 5.94L0 24l6.33-1.66a11.86 11.86 0 005.72 1.46h.01c6.55 0 11.88-5.33 11.88-11.88 0-3.17-1.23-6.15-3.58-8.4z"/></svg>';

  var chips = product
    ? ['Price for ' + product, 'Free A4 samples', 'MOQ & lead time', 'Container loading']
    : ['Get price list', 'Free A4 samples', 'MOQ & lead time', 'Factory video'];

  var panel = document.createElement('div');
  panel.className = 'wa-panel';
  panel.setAttribute('role', 'dialog');
  panel.setAttribute('aria-label', 'Chat with ' + name + ' on WhatsApp');
  panel.innerHTML =
    '<div class="wa-panel-head">' +
      '<span class="wa-avatar">' + name.charAt(0) + '</span>' +
      '<div><b>' + name + ' — Tianbei</b>' +
      '<span><i class="wa-dot"></i>Online · replies in minutes</span></div>' +
    '</div>' +
    '<div class="wa-panel-body">' +
      '<div class="wa-msg time">Typically replies within 12 hours</div>' +
      '<div class="wa-msg">Hi there 👋 This is ' + name + ' from Henan Tianbei.' +
      (product
        ? ' I see you are looking at <b>' + product + '</b>. How can I help?'
        : ' How can I help you today?') +
      '</div>' +
    '</div>' +
    '<div class="wa-chips">' +
      chips.map(function (c) { return '<button type="button" class="wa-chip">' + c + '</button>'; }).join('') +
    '</div>' +
    '<div class="wa-panel-foot">' +
      '<input class="wa-input" type="text" placeholder="Type your message…" aria-label="Your message">' +
      '<button type="button" class="wa-send" aria-label="Send on WhatsApp">' + svgSend + '</button>' +
    '</div>';

  var bubble = document.createElement('button');
  bubble.type = 'button';
  bubble.className = 'wa-float';
  bubble.setAttribute('aria-label', 'Chat with ' + name + ' on WhatsApp');
  bubble.setAttribute('aria-expanded', 'false');
  bubble.innerHTML = svgWa;

  root.appendChild(panel);
  root.appendChild(bubble);

  function go(msg) {
    var text = msg || document.querySelector('.wa-input', panel).value;
    if (!text || !text.trim()) return;
    var url = 'https://wa.me/' + wa + '?text=' + encodeURIComponent(text.trim());
    window.open(url, '_blank', 'noopener');
  }

  bubble.addEventListener('click', function () {
    var open = panel.classList.toggle('open');
    bubble.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (open) {
      var inp = panel.querySelector('.wa-input');
      setTimeout(function () { inp.focus(); }, 250);
    }
  });

  panel.querySelectorAll('.wa-chip').forEach(function (chip) {
    chip.addEventListener('click', function () {
      var msg = chip.textContent;
      panel.querySelector('.wa-input').value = msg;
      go(msg);
    });
  });

  panel.querySelector('.wa-send').addEventListener('click', function () { go(); });
  panel.querySelector('.wa-input').addEventListener('keydown', function (e) {
    if (e.key === 'Enter') go();
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') panel.classList.remove('open');
  });
})();
