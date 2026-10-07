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

  // 1. Update Scales & Rotations
  const driftSpeed = window.currentMode === 'thinking' ? 0.005 : 0.002;
  currentRotateX += driftSpeed;
  currentRotateY += driftSpeed * 0.7;

  currentScale += (targetScale - currentScale) * 0.1;
  currentRotateX += (targetRotateX - currentRotateX) * 0.05;
  currentRotateY += (targetRotateY - currentRotateY) * 0.05;

  const ringMul = updateRingPulse();
  updateOutcomeGlow(now);

  // Glitch Logic
  const glitchChance = (window.currentMode === 'thinking') ? 0.02 : 0.005;
  if (Math.random() < glitchChance) {
    glitchTimer = 3;
    sfx.glitch.currentTime = 0;
    sfx.glitch.volume = 0.15; // Reduced volume further to prevent jarring peaks
    sfx.glitch.play().catch(() => {}); // Catch browsers blocking autoplay
  }

  let currentGlitchX = 0, currentGlitchY = 0, currentGlitchScale = 1;
  if (glitchTimer > 0) {
    currentGlitchX = (Math.random() - 0.5) * 0.1;
    currentGlitchY = (Math.random() - 0.5) * 0.1;
    currentGlitchScale = 0.98 + Math.random() * 0.04;
    glitchTimer--;
  }

  // Voice/Thinking SFX Logic
  if (window.currentMode === 'thinking') {
    if (sfx.thinking.paused) sfx.thinking.play().catch(() => {});
  } else {
    sfx.thinking.pause();
  }

  // 2. Handle Particles (Ambient Dust + Failure)
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

  // 3. Draw Core Geometry
  ctx.save();
  ctx.translate(cx, cy);
  ctx.globalAlpha = globalAlpha * outcomeGlowMultiplier;

  const scale = currentScale * ringMul;
  const dist = 400;

  // Projected points
  const projPts = pts.map((p, i) => {
    // Vertex Drift
    const offset = Math.sin(now * 0.001 + i) * 0.02;
    const driftP = { x: p.x + offset, y: p.y + offset, z: p.z + offset };

    const rotated = rotate(
      driftP,
      currentRotateX + currentGlitchX,
      currentRotateY + currentGlitchY
    );
    const projected = project(rotated, scale * currentGlitchScale, dist);
    return { x: projected.x - cx, y: projected.y - cy, s: projected.s };
  });

  // Draw edges
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  edges.forEach(e => {
    const p1 = projPts[e.a];
    const p2 = projPts[e.b];
    ctx.moveTo(p1.x, p1.y);
    ctx.lineTo(p2.x, p2.y);
  });
  ctx.stroke();

  // Draw vertices
  projPts.forEach((p, i) => {
    const size = 2 * p.s * 0.1;
    ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
    ctx.beginPath();
    ctx.arc(p.x, p.y, size, 0, Math.PI*2);
    ctx.fill();
  });

  // Cosmic Ring
  const cosmicRadius = scale * 1.2;
  const cosmicAlpha = 0.2 + Math.sin(now * 0.001) * 0.1;

  ctx.beginPath();
  ctx.arc(0, 0, cosmicRadius, 0, Math.PI * 2);
  ctx.strokeStyle = `rgba(200, 230, 255, ${cosmicAlpha})`;
  ctx.lineWidth = 2;
  ctx.shadowBlur = 15;
  ctx.shadowColor = 'rgba(200, 230, 255, 0.5)';
  ctx.stroke();
  ctx.shadowBlur = 0; // Reset shadow for other elements

  // Add orbiting sparkles to the ring
  for(let i=0; i<5; i++) {
    const sAngle = (now * 0.0005) + (i * Math.PI * 2 / 5);
    const sx = Math.cos(sAngle) * cosmicRadius;
    const sy = Math.sin(sAngle) * cosmicRadius;
    const sSize = Math.random() * 1.5;
    ctx.fillStyle = `rgba(255, 255, 255, ${0.5 + Math.sin(now * 0.005 + i) * 0.5})`;
    ctx.beginPath();
    ctx.arc(sx, sy, sSize, 0, Math.PI * 2);
    ctx.fill();
  }

  // 4. Thinking-Scanner Visuals
  if(window.currentMode === 'thinking'){
    const scanAngle = (now * 0.002) % (Math.PI * 2);
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(Math.cos(scanAngle) * scale * 0.6, Math.sin(scanAngle) * scale * 0.6);
    ctx.stroke();

    // Scanner Arc
    ctx.beginPath();
    ctx.arc(0, 0, scale * 0.6, scanAngle - 0.4, scanAngle + 0.4);
    ctx.stroke();
  }

  // 5. Bohr Orbit Rings
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

    // Electrons
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

// Entry point
function startRenderLoop(){
  requestAnimationFrame(draw);
}
