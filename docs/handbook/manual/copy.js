document.addEventListener('click', function (event) {
  var button = event.target.closest && event.target.closest('button.copy');
  if (!button) return;
  var box = document.getElementById(button.getAttribute('data-target'));
  if (!box) return;
  var text = box.textContent;
  var label = button.textContent;
  var select = function () {
    var range = document.createRange();
    range.selectNodeContents(box);
    var sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
  };
  var done = function (ok) {
    button.textContent = ok ? 'Copied' : 'Press Ctrl+C or Cmd+C to copy';
    setTimeout(function () { button.textContent = label; }, 2000);
  };
  try {
    navigator.clipboard.writeText(text).then(function () { done(true); }, function () { select(); done(false); });
  } catch (e) {
    select(); done(false);
  }
});
