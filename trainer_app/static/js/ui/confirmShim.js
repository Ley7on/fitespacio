// Lightweight confirm shim: ensures window.showConfirm exists.
// If a prettier modal is already provided by another script, this file does nothing.
(function(){
  if (window.showConfirm) return; // already provided by a richer modal

  window.showConfirm = function(message, opts) {
    opts = opts || {};
    return new Promise(function(resolve) {
      try {
        // Fallback to native confirm in a Promise so callers can await it.
        var result = window.confirm(message);
        resolve(!!result);
      } catch (err) {
        // In case confirm is unavailable for some reason, default to true
        console.warn('confirmShim: native confirm failed', err);
        resolve(true);
      }
    });
  };

  // Expose a tiny helper that mimics the nicer modal API shape used elsewhere
  window.maybeConfirm = function(message) {
    return window.showConfirm(message);
  };
})();
