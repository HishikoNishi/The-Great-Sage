// render-loop.js
// Core animation loop, canvas management, and drawing

const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');
const wrap = document.getElementById('wrap');

let cx, cy;
let currentScale = 180;
let targetScale = 180;
let currentRotateX = 0, currentRotateY = 0;
let targetRotateX = 0, targetRotateY = 0;
let globalAlpha = 1;
let glitchTimer = 0;

// --- ASTRAL VOID CONFIG ---
const starCount = 60;
const stars = [];
for(let i=0; i<starCount; i++) {
  stars.push({
    x: Math.random(),
    y: Math.random(),
    z: Math.random(),
    s: Math.random() * 1.5,
    o: Math.random() * Math.PI * 2
  });
}

const dustCount = 30;
const dust = [];
for(let i=0; i<dustCount; i++) {
  dust.push({
    x: Math.random() * 2000 - 1000,
    y: Math.random() * 2000 - 1000,
    z: Math.random() * 1000,
    vx: (Math.random() - 0.5) * 0.2,
    vy: -0.2 - Math.random() * 0.3,
    s: Math.random() * 2
  });
}
// --------------------------

// SFX Management
const sfx = {
  thinking: new Audio('../assets/sfx/AI_Thinking_idle.wav'),
  glitch: new Audio('../assets/sfx/glitch.mp3'),
  fail: new Audio('../assets/sfx/fail.ogg'),
};
sfx.thinking.loop = true;

const particles = [];

function resizeCanvas(){
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  cx = canvas.width / 2;
  cy = canvas.height / 2;
}
window.addEventListener('resize', resizeCanvas);
resizeCanvas();

function draw(){
  requestAnimationFrame(draw);
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const now = performance.now();

  // --- ASTRAL VOID PASS (Background) ---
  ctx.save();
  ctx.translate(cx, cy);

  const gradient = ctx.createRadialGradient(0, 0, 0, 0, 0, canvas.width * 0.6);
  gradient.addColorStop(0, 'rgba(40, 60, 80, 0.15)');
  gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
  ctx.fillStyle = gradient;
  ctx.fillRect(-cx, -cy, canvas.width, canvas.height);

  ctx.fillStyle = 'rgba(255, 255, 255, 0.4)';
  stars.forEach(s => {
    const twinkle = 0.5 + Math.sin(now * 0.001 + s.o) * 0.5;
    const x = (s.x - 0.5) * canvas.width;
    const y = (s.y - 0.5) * canvas.height;
    ctx.globalAlpha = twinkle * 0.6;
    ctx.beginPath();
    ctx.arc(x, y, s.s, 0, Math.PI * 2);
    ctx.fill();
  });

  ctx.globalAlpha = 1;
  ctx.fillStyle = 'rgba(200, 230, 255, 0.3)';
  for(let i=0; i<dust.length; i++) {
    const d = dust[i];
    d.x += d.vx;
    d.y += d.vy;
    if(d.y < -cy) d.y = cy;
    if(d.x < -cx) d.x = cx;
    if(d.x > cx) d.x = -cx;
    ctx.fillRect(d.x, d.y, d.s, d.s);
  }
  ctx.restore();

  // 1. Update Scales & Rotations
  const driftSpeed = window.currentMode === 'thinking' ? 0.005 : 0.002;
  currentRotateX += driftSpeed;
  currentRotateY += driftSpeed * 0.7;

  let voiceScaleTarget = 180;
  if (window.currentMode === 'speaking' || (window.currentMode !== 'standby' && window.currentMode !== 'thinking')) {
    voiceScaleTarget = 210;
  } else if (window.currentMode === 'thinking') {
    voiceScaleTarget = 190;
  }

  currentScale += (voiceScaleTarget - currentScale) * 0.1;
  currentRotateX += (targetRotateX - currentRotateX) * 0.05;
  currentRotateY += (targetRotateY - currentRotateY) * 0.05;

  const ringMul = updateRingPulse();
  updateOutcomeGlow(now);

  const glitchChance = (window.currentMode === 'thinking') ? 0.02 : 0.005;
  if (Math.random() < glitchChance) {
    glitchTimer = 3;
    sfx.glitch.currentTime = 0;
    sfx.glitch.volume = 0.05;
    sfx.glitch.play().catch(() => {});
  }

  let currentGlitchX = 0, currentGlitchY = 0, currentGlitchScale = 1;
  if (glitchTimer > 0) {
    currentGlitchX = (Math.random() - 0.5) * 0.1;
    currentGlitchY = (Math.random() - 0.5) * 0.1;
    currentGlitchScale = 0.98 + Math.random() * 0.04;
    glitchTimer--;
  }

  if (window.currentMode === 'thinking') {
    if (sfx.thinking.paused) sfx.thinking.play().catch(() => {});
  } else {
    sfx.thinking.pause();
  }

  for(let i=particles.length-1; i>=0; i--){
    const p = particles[i];
    p.x += p.vx;
    p.y += p.vy;
    p.life -= 1/60;
    if(p.life <= 0){
      particles.splice(i, 1);
      continue;
    }
    ctx.fillStyle = p.type === 'fail' ? `rgba(255, 50, 50, ${p.life})` : `rgba(255, 255, 255, ${p.life})`;
    ctx.beginPath();
    ctx.arc(p.x, p.y, p.size, 0, Math.PI*2);
    ctx.fill();
  }

  ctx.save();
  ctx.translate(cx, cy);
  ctx.globalAlpha = globalAlpha * outcomeGlowMultiplier;

  const scale = currentScale * ringMul;
  const dist = 400;

  const projPts = pts.map((p, i) => {
    const offset = Math.sin(now * 0.001 + i) * 0.02;
    const driftP = { x: p.x + offset, y: p.y + offset, z: p.z + offset };
    const rotated = rotate(driftP, currentRotateX + currentGlitchX, currentRotateY + currentGlitchY);
    const projected = project(rotated, scale * currentGlitchScale, dist);
    return { x: projected.x - cx, y: projected.y - cy, s: projected.s, z: rotated.z };
  });

  const sortedEdges = edges.map(e => ({
    ...e,
    avgZ: (projPts[e.a].z + projPts[e.b].z) / 2
  })).sort((a, b) => a.avgZ - b.avgZ);

  sortedEdges.forEach(e => {
    const p1 = projPts[e.a];
    const p2 = projPts[e.b];
    const depthAlpha = Math.max(0.05, 0.2 * (p1.s));
    ctx.strokeStyle = `rgba(255, 255, 255, ${depthAlpha})`;
    ctx.lineWidth = 1 * p1.s;
    ctx.beginPath();
    ctx.moveTo(p1.x, p1.y);
    ctx.lineTo(p2.x, p2.y);
    ctx.stroke();
  });

  const sortedPts = [...projPts].sort((a, b) => a.z - b.z);
  sortedPts.forEach((p) => {
    const size = 2 * p.s * 0.1;
    const alpha = Math.min(0.7, 0.2 + p.s * 0.3);
    ctx.fillStyle = `rgba(255, 255, 255, ${alpha})`;
    ctx.shadowBlur = p.s > 1.3 ? 5 * (p.s - 1.3) : 0;
    ctx.shadowColor = 'white';
    ctx.beginPath();
    ctx.arc(p.x, p.y, size, 0, Math.PI*2);
    ctx.fill();
    ctx.shadowBlur = 0;
  });

  // 3D Cosmic Rings Implementation
  const ringConfigs = [
    { radiusMul: 1.2, tilt: 0.6, speed: 0.0008, orbitR: 20, color: 'rgba(200, 230, 255, 0.15)', lineW: 1.5, glow: 8, glowC: 'rgba(200, 230, 255, 0.3)', orbitSpeedMul: 1.0 },
    { radiusMul: 1.6, tilt: 0.3, speed: 0.0004, orbitR: 40, color: 'rgba(180, 200, 255, 0.1)', lineW: 1.0, glow: 5, glowC: 'rgba(180, 200, 255, 0.2)', orbitSpeedMul: -0.7 },
    { radiusMul: 2.0, tilt: 0.8, speed: 0.0006, orbitR: 15, color: 'rgba(220, 240, 255, 0.08)', lineW: 1.0, glow: 10, glowC: 'rgba(220, 240, 255, 0.2)', orbitSpeedMul: 1.3 }
  ];

  ringConfigs.forEach((cfg, ringIdx) => {
    const cosmicRadius = scale * cfg.radiusMul;
    const ringOffsetX = Math.cos(now * cfg.speed * cfg.orbitSpeedMul) * cfg.orbitR;
    const ringOffsetY = Math.sin(now * cfg.speed * cfg.orbitSpeedMul * 0.8) * cfg.orbitR;

    ctx.beginPath();
    ctx.ellipse(ringOffsetX, ringOffsetY, cosmicRadius, cosmicRadius * (1 - cfg.tilt), currentRotateX * (0.2 + ringIdx * 0.1), 0, Math.PI * 2);
    ctx.strokeStyle = cfg.color;
    ctx.lineWidth = cfg.lineW;
    ctx.shadowBlur = cfg.glow;
    ctx.shadowColor = cfg.glowC;
    ctx.stroke();
    ctx.shadowBlur = 0;

    for(let i=0; i<3; i++) {
      const sAngle = (now * 0.0005 + ringIdx * 100) + (i * Math.PI * 2 / 3);
      const sx = ringOffsetX + Math.cos(sAngle) * cosmicRadius;
      const sy = ringOffsetY + Math.sin(sAngle) * cosmicRadius * (1 - cfg.tilt);
      const sDepth = Math.sin(sAngle);
      const sSize = (0.5 + sDepth * 0.5) * (1.5 - ringIdx * 0.2);
      const sAlpha = 0.2 + sDepth * 0.3;
      ctx.fillStyle = `rgba(255, 255, 255, ${sAlpha})`;
      ctx.beginPath();
      ctx.arc(sx, sy, sSize, 0, Math.PI * 2);
      ctx.fill();
    }
  });

  if(window.currentMode === 'thinking'){
    const scanAngle = (now * 0.002) % (Math.PI * 2);
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(Math.cos(scanAngle) * scale * 0.6, Math.sin(scanAngle) * scale * 0.6);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(0, 0, scale * 0.6, scanAngle - 0.4, scanAngle + 0.4);
    ctx.stroke();
  }

  const orbits = [0.4, 0.7, 1.0];
  orbits.forEach((rMul, idx) => {
    const r = scale * rMul;
    const speed = (idx + 1) * 0.0005;
    const offset = now * speed;
    ctx.strokeStyle = `rgba(255, 255, 255, ${0.15 - idx * 0.03})`;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(0, 0, r, 0, Math.PI * 2);
    ctx.stroke();
    const eAngle = offset + (idx * Math.PI * 2 / 3);
    const ex = Math.cos(eAngle) * r;
    const ey = Math.sin(eAngle) * r;
    ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
    ctx.beginPath();
    ctx.arc(ex, ey, 2, 0, Math.PI * 2);
    ctx.fill();
  });

  ctx.restore();
}

function startRenderLoop(){
  requestAnimationFrame(draw);
}
