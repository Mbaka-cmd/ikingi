(function () {
  'use strict';
  var form = document.getElementById('enquiry-form');
  if (!form) return;
  var status = document.getElementById('form-status');

  function field(name) { return form.elements[name]; }
  function setError(name, msg) {
    var input = field(name), box = document.getElementById('e-' + name);
    if (!box) return;
    if (msg) { box.textContent = msg; box.hidden = false; input.setAttribute('aria-invalid', 'true'); }
    else { box.hidden = true; box.textContent = ''; input.removeAttribute('aria-invalid'); }
  }
  function validate() {
    var bad = [];
    var name = field('name').value.trim();
    var phone = field('phone').value.replace(/[^\d]/g, '');
    var email = field('email').value.trim();
    var msg = field('message').value.trim();
    setError('name', name.length < 2 ? 'Please enter your name.' : '');
    setError('phone', (phone.length < 9 || phone.length > 15) ? 'Please enter a valid phone number.' : '');
    setError('email', (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) ? 'Please enter a valid email address.' : '');
    setError('message', msg.length < 10 ? 'Please write a message of at least 10 characters.' : '');
    ['name', 'phone', 'email', 'message'].forEach(function (n) {
      if (field(n).getAttribute('aria-invalid') === 'true') bad.push(n);
    });
    return bad;
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    status.className = 'form-status';
    if (field('website').value) return; // honeypot: bots fill this, people never see it
    var bad = validate();
    if (bad.length) {
      status.textContent = 'Please correct the highlighted fields and try again.';
      status.className = 'form-status is-error';
      field(bad[0]).focus();
      return;
    }
    var text = 'Hello, my name is ' + field('name').value.trim() + ' (phone: ' + field('phone').value.trim() +
      (field('email').value.trim() ? ', email: ' + field('email').value.trim() : '') + ').\n' +
      'Enquiry type: ' + field('type').value + '\n\n' + field('message').value.trim() +
      '\n\n(Sent from the ' + form.dataset.school + ' website)';
    if (form.dataset.wa) {
      window.open(form.dataset.wa + '?text=' + encodeURIComponent(text), '_blank', 'noopener');
      status.textContent = 'WhatsApp is opening with your message. Press Send in WhatsApp to deliver it.';
    } else if (form.dataset.email) {
      window.location.href = 'mailto:' + form.dataset.email + '?subject=' + encodeURIComponent('Enquiry: ' + field('type').value) + '&body=' + encodeURIComponent(text);
      status.textContent = 'Your email app is opening with your message. Press Send there to deliver it.';
    } else {
      status.textContent = 'Sorry, we could not open a messaging app. Please call the school instead.';
      status.className = 'form-status is-error';
      return;
    }
    status.className = 'form-status is-success';
    form.reset();
  });
})();