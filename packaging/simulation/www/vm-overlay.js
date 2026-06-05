// VM deployment overlay: disables cross-lab tool links and stops status polling.
// Injected at build time; executes synchronously before window.load fires.

window.pollOnce = function() {};

window.openTool = function() {
  alert('Tool links are only available in the Docker deployment.');
};

document.addEventListener('DOMContentLoaded', function() {
  ['attacker', 'defender', 'caldera', 'wazuh'].forEach(function(tool) {
    var dot  = document.getElementById(tool + 'Dot');
    var text = document.getElementById(tool + 'Text');
    if (dot)  { dot.style.background = '#6b7280'; dot.style.boxShadow = 'none'; }
    if (text) text.textContent = 'Docker only';
  });

  document.querySelectorAll('.btn[onclick*="openTool"], .small-btn[onclick*="openTool"]')
    .forEach(function(btn) {
      btn.style.opacity = '0.4';
      btn.style.cursor = 'not-allowed';
      btn.title = 'Available in Docker deployment only';
    });
});
