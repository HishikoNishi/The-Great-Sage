// main-init.js
// Orchestration and initialization

function initOverlayLifecycle() {
  console.log("Initializing Great Sage Overlay...");

  // 1. Initial Setup
  const wrap = document.getElementById('wrap');
  if (wrap) {
    wrap.classList.add('window-visible');
  }

  // Boot SFX
  const sfxStartup = new Audio('../assets/sfx/Startup.wav');
  sfxStartup.play().catch(() => {});

  setTimeout(() => {
    const sfxAppear = new Audio('../assets/sfx/Overlay_apear.wav');
    sfxAppear.play().catch(() => {});
  }, 500);

  // 2. Boot Sequence
  bootStartTime = performance.now();

  // 3. Start Render Loop
  startRenderLoop();

  // 4. Initial Mode
  window.setMode('standby');

  console.log("Overlay lifecycle started.");
}

// Execute on load
window.addEventListener('DOMContentLoaded', () => {
  initOverlayLifecycle();
});
