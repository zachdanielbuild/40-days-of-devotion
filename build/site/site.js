// 40 Day Journeys: small enhancements for the day pages. Everything still reads fine without it.
(function () {
  // Worship videos load only when played (faster pages, no YouTube tracking until then).
  document.querySelectorAll('.video[data-id]').forEach(function (box) {
    var btn = box.querySelector('button');
    if (!btn) return;
    btn.addEventListener('click', function () {
      var f = document.createElement('iframe');
      f.src = 'https://www.youtube-nocookie.com/embed/' + box.dataset.id + '?autoplay=1&rel=0';
      f.title = box.dataset.title || 'Worship video';
      f.allow = 'autoplay; encrypted-media; picture-in-picture; fullscreen';
      f.allowFullscreen = true;
      box.innerHTML = '';
      box.appendChild(f);
    });
  });

  // Copy the sign-up link.
  document.querySelectorAll('[data-copy]').forEach(function (btn) {
    var label = btn.querySelector('.label');
    btn.addEventListener('click', function () {
      var done = function () { if (label) { var old = label.textContent; label.textContent = 'Copied'; setTimeout(function () { label.textContent = old; }, 2000); } };
      if (navigator.clipboard) navigator.clipboard.writeText(btn.dataset.copy).then(done, function () { window.prompt('Copy this link:', btn.dataset.copy); });
      else window.prompt('Copy this link:', btn.dataset.copy);
    });
  });

  // Two minutes of quiet.
  document.querySelectorAll('.timer').forEach(function (btn) {
    var label = btn.querySelector('.label'), start = label.textContent, t = null;
    function fmt(s) { return Math.floor(s / 60) + ':' + ('0' + (s % 60)).slice(-2); }
    btn.addEventListener('click', function () {
      if (t) { clearInterval(t); t = null; btn.removeAttribute('data-running'); label.textContent = start; return; }
      var left = 120; btn.setAttribute('data-running', ''); label.textContent = fmt(left) + ' · tap to stop';
      t = setInterval(function () {
        left -= 1;
        if (left <= 0) { clearInterval(t); t = null; btn.removeAttribute('data-running'); label.textContent = 'Amen. Write down what you heard.'; if (navigator.vibrate) navigator.vibrate(200); return; }
        label.textContent = fmt(left) + ' · tap to stop';
      }, 1000);
    });
  });

  // Journal notes stay on this device only.
  document.querySelectorAll('.journal textarea').forEach(function (ta) {
    var key = 'journal:' + location.pathname;
    try { var v = localStorage.getItem(key); if (v) ta.value = v; } catch (e) {}
    ta.addEventListener('input', function () { try { localStorage.setItem(key, ta.value); } catch (e) {} });
  });
})();
