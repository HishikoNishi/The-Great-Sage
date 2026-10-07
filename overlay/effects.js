// effects.js
// Failure/Success animations, Bohr orbits, thinking-scanner

const ringPulse = { active:false, start:0, kind:'open', mul:1 };
const RING_PULSE_MS = 300;
function easeOutCubic(t){ return 1-Math.pow(1-t,3); }

function startRingPulse(kind){
  ringPulse.active = true;
  ringPulse.start = performance.now();
  ringPulse.kind = kind;
}

function updateRingPulse(){
  if(!ringPulse.active) return 1;
  const t = Math.min(1, (performance.now()-ringPulse.start)/RING_PULSE_MS);
  const e = easeOutCubic(t);
  if(ringPulse.kind === 'open'){
    ringPulse.mul = 1 + 0.15*(1-e);
  } else {
    ringPulse.mul = 0.9 + 0.1*e;
  }
  if(t >= 1){
    ringPulse.mul = 1;
    ringPulse.active = false;
  }
  return ringPulse.mul;
}

let outcomeGlowMultiplier = 1;
let outcomeGlowTarget = 1;
let outcomeGlowUntil = 0;
const successPing = { active: false, start: 0, startR: 0, endR: 0, pendingScale: false };

const failureFx = { active: false, phase: 'idle', phaseStarted: 0, scanGlitch: [] };

let thinkingTickAngle = 0;
let thinkingTickTargetAngle = 0;
let thinkingTickLastStep = 0;
let thinkingTickFlashUntil = 0;

function resetThinkingTick(){
  thinkingTickAngle = 0;
  thinkingTickTargetAngle = 0;
  thinkingTickLastStep = 0;
  thinkingTickFlashUntil = 0;
}

function shortestAngle(from, to){
  return Math.atan2(Math.sin(to-from), Math.cos(to-from));
}

function updateOutcomeGlow(now){
  if(now < outcomeGlowUntil){
    outcomeGlowMultiplier += (outcomeGlowTarget - outcomeGlowMultiplier) * 0.22;
  } else {
    outcomeGlowTarget = 1;
    outcomeGlowMultiplier += (1 - outcomeGlowMultiplier) * 0.1;
  }
}

function spawnFailureParticles(){
  const count = 15 + Math.floor(Math.random() * 6);
  for(let i=0;i<count;i++){
    particles.push({
      type: 'fail',
      x: Math.random() * canvas.width,
      y: -8 - Math.random() * 24,
      vx: (Math.random() - 0.5) * 1.4,
      vy: 1.2 + Math.random() * 2.8,
      size: 0.7 + Math.random() * 1.5,
      life: 1,
      maxLife: 1.5 + Math.random() * 0.55,
    });
  }
}

function createCracks(){
  const crackCount = 3 + Math.floor(Math.random() * 3);
  const minGap = Math.PI / 5;
  const baseAngles = [];
  let attempts = 0;
  while(baseAngles.length < crackCount && attempts < 100){
    attempts += 1;
    const candidate = Math.random() * Math.PI * 2;
    const spaced = baseAngles.every(a=>{
      const diff = Math.abs(Math.atan2(Math.sin(candidate - a), Math.cos(candidate - a)));
      return diff >= minGap;
    });
    if(spaced) baseAngles.push(candidate);
  }
  return baseAngles;
}
