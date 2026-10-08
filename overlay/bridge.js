// bridge.js
// Interface between Python (pywebview) and JavaScript

window.setVisibility = function(visible) {
  const wrap = document.getElementById('wrap');
  if (!wrap) return;
  if (visible) {
    wrap.classList.add('window-visible');
  } else {
    wrap.classList.remove('window-visible');
  }
};

window.setMode = function(mode) {
  const modeEl = document.getElementById('mode');
  if (!modeEl) return;

  modeEl.textContent = mode.toUpperCase();
  window.currentMode = mode;

  // SFX for state transitions
  if (mode === 'listening') {
    const sfxOpen = new Audio('../assets/sfx/core_UI_open.wav');
    sfxOpen.play().catch(() => {});
  } else if (mode === 'standby') {
    const sfxClose = new Audio('../assets/sfx/Core_UI_Close.wav');
    sfxClose.play().catch(() => {});
  }

  // Visual state triggers based on mode
  switch(mode) {
    case 'standby':
      targetScale = 180;
      targetRotateX = 0.2;
      targetRotateY = 0.3;
      break;
    case 'listening':
      targetScale = 220;
      targetRotateX = 0.5;
      targetRotateY = 0.8;
      startRingPulse('open');
      break;
    case 'thinking':
      targetScale = 200;
      targetRotateX = 1.2;
      targetRotateY = 1.5;
      break;
    case 'speaking':
      targetScale = 190;
      targetRotateX = 0.1;
      targetRotateY = 0.2;
      break;
  }
};

window.setCaption = function(text) {
  if (window.chrome && window.chrome.webview) {
    window.chrome.webview.postMessage("CAPTION_TRACE:JS_ENTER:" + String(text));
  }
  const trans = document.getElementById('transcript');
  if (!trans) {
    console.error("[BRIDGE_DEBUG] #transcript element not found!");
    return;
  }
  trans.textContent = text;
  if (window.chrome && window.chrome.webview) {
    window.chrome.webview.postMessage("CAPTION_TRACE:JS_DOM_UPDATED:" + String(trans.textContent));
  }
};

window.playVoiceLine = function(url, audioId) {
  const audio = document.getElementById('sage-audio');
  if (!audio) return;

  // 1. Register handlers BEFORE assigning src and calling play()
  audio.onplay = () => {
    console.log(`Audio playback started. ID: ${audioId}`);
  };

  audio.onended = () => {
    console.log(`[AUDIO_TRACE] JS onended id=${audioId}`);
    console.log(`[AUDIO_TRACE] JS postMessage AUDIO_ENDED:${audioId}`);
    console.log(`Audio playback ended. ID: ${audioId}`);
    // Report event with ID to WPF Host via WebView2 bridge
    if (window.chrome && window.chrome.webview) {
      window.chrome.webview.postMessage(`AUDIO_ENDED:${audioId}`);
    } else {
      console.warn("WebView2 bridge not available");
    }
  };

  audio.onerror = (e) => {
    console.error(`[AUDIO_TRACE] JS onerror id=${audioId}:`, e);
    console.error(`Audio playback error for ID ${audioId}:`, e);
    if (window.chrome && window.chrome.webview) {
      window.chrome.webview.postMessage(`AUDIO_ERROR:${audioId}`);
    }
  };

  // 2. Assign source
  audio.src = url;

  // 3. Play
  audio.play().catch(e => console.error(`Audio playback failed for ID ${audioId}:`, e));
};

window.playUiSfx = function(key) {
  const sfxMap = {
    'interfaceClick': 'sfx-interface-click',
    'startup': 'sfx-startup',
    'overlayAppear': 'sfx-overlay-appear',
    'coreOpen': 'sfx-core-open',
    'coreClose': 'sfx-core-close',
    'thinking': 'sfx-thinking',
    'fail': 'sfx-fail',
    'crack': 'sfx-crack',
    'shatter': 'sfx-shatter'
  };
  const id = sfxMap[key];
  if (!id) return;
  const el = document.getElementById(id);
  if (el) el.play().catch(e => console.error(`SFX ${key} failed:`, e));
};

window.triggerSuccess = function() {
  startRingPulse('close');
  outcomeGlowTarget = 1.5;
  outcomeGlowUntil = performance.now() + 1000;
};

window.triggerFailure = function() {
  startRingPulse('open');
  outcomeGlowTarget = 0.5;
  outcomeGlowUntil = performance.now() + 1000;
  spawnFailureParticles();

  // Failure SFX
  const sfxFail = new Audio('../assets/sfx/fail.ogg');
  sfxFail.play().catch(() => {});
};
