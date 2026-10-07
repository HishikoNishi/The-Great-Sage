// core-geometry.js
// Polyhedron point cloud and projection math

const N = 42;
const pts = [];
for(let i=0;i<N;i++){
  const y = 1 - (i/(N-1))*2;
  const r = Math.sqrt(1-y*y);
  const theta = Math.PI*(3-Math.sqrt(5))*i;
  pts.push({x:Math.cos(theta)*r, y:y, z:Math.sin(theta)*r});
}
const disp = pts.map(()=>({x:0,y:0,z:0, vx:0,vy:0,vz:0}));
const ptRest = pts.map(p=>({x:p.x,y:p.y,z:p.z}));
const ptBootFrom = pts.map(p=>{
  const mag = 2.4 + Math.random()*2.2;
  const j = () => (Math.random()-0.5)*0.35;
  return {x:p.x*mag+j(), y:p.y*mag+j(), z:p.z*mag+j()};
});
const BOOT_DURATION_MS = 1600;
let bootActive = true;
let bootStartTime = 0;
let bootGlow = 0;

const edges = [];
for(let i=0;i<N;i++){
  let dists = [];
  for(let j=0;j<N;j++){
    if(i===j) continue;
    const dx=pts[i].x-pts[j].x, dy=pts[i].y-pts[j].y, dz=pts[i].z-pts[j].z;
    dists.push([j, dx*dx+dy*dy+dz*dz]);
  }
  dists.sort((a,b)=>a[1]-b[1]);
  for(let k=0;k<3;k++){
    const j = dists[k][0];
    const key = i<j? i+'_'+j : j+'_'+i;
    if(!edges.find(e=>e.key===key)) edges.push({key, a:i, b:j});
  }
}

function rotate(p, ax, ay){
  let {x,y,z} = p;
  let cosA=Math.cos(ay), sinA=Math.sin(ay);
  let x1 = x*cosA + z*sinA;
  let z1 = -x*sinA + z*cosA;
  let cosB=Math.cos(ax), sinB=Math.sin(ax);
  let y1 = y*cosB - z1*sinB;
  let z2 = y*sinB + z1*cosB;
  return {x:x1,y:y1,z:z2};
}

function project(p, scale, dist){
  const f = dist/(dist - p.z*scale*0.02);
  return {x: cx + p.x*scale*f, y: cy + p.y*scale*f, s:f};
}
