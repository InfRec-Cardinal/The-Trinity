                                                                                  
                                                                       
export function firstReachObject(front, forward, right, obstacles, reach) {
  let best = null;
  const limit = reach.length + reach.tolerance;
  for (const w of [0, -reach.halfWidth / 2, reach.halfWidth / 2, -reach.halfWidth, reach.halfWidth]) {
    const origin = {x: front.x + right.x * w, z: front.z + right.z * w};
    for (const o of obstacles) {
      let enter = 0, exit = limit;
      for (const [axis, lo, hi] of [['x', o.minX, o.maxX], ['z', o.minZ, o.maxZ]]) {
        const v = forward[axis];
        if (Math.abs(v) < 1e-12) { if (origin[axis] < lo || origin[axis] > hi) {enter = Infinity; break;} }
        else { const a = (lo - origin[axis]) / v, b = (hi - origin[axis]) / v;
          enter = Math.max(enter, Math.min(a,b)); exit = Math.min(exit, Math.max(a,b)); }
      }
      if (enter <= exit + 1e-10 && enter <= limit + 1e-10 && (!best || enter < best.distance - 1e-10)) best = {id:o.id, distance:enter};
    }
  }
  if (!best) return {id:null, reachM:null, physicalContact:false, handGapM:null};
  return {id:best.id, reachM:best.distance, physicalContact:best.distance <= reach.length + 1e-10,
    handGapM:Math.max(0, best.distance - reach.length)};
}
export function judgeReach(hit, targetId, touched, tolerance=0.3) {
  const checks = {executedTouch:!!touched, firstObjectIsTarget:hit?.id===targetId,
    contactOrWithinTolerance:!!hit?.id && hit.handGapM <= tolerance + 1e-10};
  return {success:Object.values(checks).every(Boolean),checks};
}
