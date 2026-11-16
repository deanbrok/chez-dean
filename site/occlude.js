// A small uniform grid over the static room triangles, so "is anything in the way?" costs microseconds instead of
// a full raycast through every triangle of the room (used for hover/click picking and for hiding rings behind things).
import * as THREE from 'three';

export function buildGrid(meshes, cell = 0.3) {
  let total = 0;
  for (const m of meshes) { const g = m.geometry; total += (g.index ? g.index.count : g.attributes.position.count) / 3; }
  const T = new Float32Array(total * 9);
  const v = new THREE.Vector3(), box = new THREE.Box3();
  let k = 0;
  for (const m of meshes) {
    m.updateWorldMatrix(true, false);
    const g = m.geometry, pos = g.attributes.position, idx = g.index, n = idx ? idx.count : pos.count;
    for (let i = 0; i < n; i++) {
      v.fromBufferAttribute(pos, idx ? idx.getX(i) : i).applyMatrix4(m.matrixWorld);
      T[k++] = v.x; T[k++] = v.y; T[k++] = v.z; box.expandByPoint(v);
    }
  }
  box.expandByScalar(0.01);
  const o = box.min, nx = Math.max(1, Math.ceil((box.max.x - o.x) / cell)), ny = Math.max(1, Math.ceil((box.max.y - o.y) / cell)), nz = Math.max(1, Math.ceil((box.max.z - o.z) / cell));
  const NC = nx * ny * nz, cnt = new Uint32Array(NC + 1);
  const range = (t, out) => {
    let x0 = Infinity, y0 = Infinity, z0 = Infinity, x1 = -Infinity, y1 = -Infinity, z1 = -Infinity;
    for (let j = 0; j < 3; j++) {
      const a = T[t * 9 + j * 3], b = T[t * 9 + j * 3 + 1], c = T[t * 9 + j * 3 + 2];
      if (a < x0) x0 = a; if (a > x1) x1 = a; if (b < y0) y0 = b; if (b > y1) y1 = b; if (c < z0) z0 = c; if (c > z1) z1 = c;
    }
    out[0] = Math.max(0, Math.floor((x0 - o.x) / cell)); out[1] = Math.min(nx - 1, Math.floor((x1 - o.x) / cell));
    out[2] = Math.max(0, Math.floor((y0 - o.y) / cell)); out[3] = Math.min(ny - 1, Math.floor((y1 - o.y) / cell));
    out[4] = Math.max(0, Math.floor((z0 - o.z) / cell)); out[5] = Math.min(nz - 1, Math.floor((z1 - o.z) / cell));
  };
  const r = new Int32Array(6);
  for (let t = 0; t < total; t++) {
    range(t, r);
    for (let z = r[4]; z <= r[5]; z++) for (let y = r[2]; y <= r[3]; y++) for (let x = r[0]; x <= r[1]; x++) cnt[(z * ny + y) * nx + x + 1]++;
  }
  for (let c = 0; c < NC; c++) cnt[c + 1] += cnt[c];
  const items = new Uint32Array(cnt[NC]), fill = cnt.slice(0, NC);
  for (let t = 0; t < total; t++) {
    range(t, r);
    for (let z = r[4]; z <= r[5]; z++) for (let y = r[2]; y <= r[3]; y++) for (let x = r[0]; x <= r[1]; x++) items[fill[(z * ny + y) * nx + x]++] = t;
  }
  const stamp = new Uint32Array(total); let query = 0;

  // Moller-Trumbore, both faces; returns t or -1
  function tri(t, ox, oy, oz, dx, dy, dz) {
    const b = t * 9;
    const ax = T[b], ay = T[b + 1], az = T[b + 2];
    const e1x = T[b + 3] - ax, e1y = T[b + 4] - ay, e1z = T[b + 5] - az, e2x = T[b + 6] - ax, e2y = T[b + 7] - ay, e2z = T[b + 8] - az;
    const px = dy * e2z - dz * e2y, py = dz * e2x - dx * e2z, pz = dx * e2y - dy * e2x;
    const det = e1x * px + e1y * py + e1z * pz; if (det > -1e-9 && det < 1e-9) return -1;
    const inv = 1 / det, sx = ox - ax, sy = oy - ay, sz = oz - az;
    const u = (sx * px + sy * py + sz * pz) * inv; if (u < 0 || u > 1) return -1;
    const qx = sy * e1z - sz * e1y, qy = sz * e1x - sx * e1z, qz = sx * e1y - sy * e1x;
    const w = (dx * qx + dy * qy + dz * qz) * inv; if (w < 0 || u + w > 1) return -1;
    return (e2x * qx + e2y * qy + e2z * qz) * inv;
  }

  // true if a static triangle lies on the ray between near and far
  function blocked(origin, dir, far, near = 0.0) {
    query = (query + 1) >>> 0; if (query === 0) { stamp.fill(0); query = 1; }
    const ox = origin.x, oy = origin.y, oz = origin.z, dx = dir.x, dy = dir.y, dz = dir.z;
    // clip the segment to the grid
    let t0 = near, t1 = far;
    for (const [oo, dd, lo, hi] of [[ox, dx, box.min.x, box.max.x], [oy, dy, box.min.y, box.max.y], [oz, dz, box.min.z, box.max.z]]) {
      if (Math.abs(dd) < 1e-12) { if (oo < lo || oo > hi) return false; continue; }
      let a = (lo - oo) / dd, b = (hi - oo) / dd; if (a > b) [a, b] = [b, a];
      t0 = Math.max(t0, a); t1 = Math.min(t1, b); if (t0 > t1) return false;
    }
    // 3D DDA through the cells
    const sx = ox + dx * t0, sy = oy + dy * t0, sz = oz + dz * t0;
    let cx = Math.min(nx - 1, Math.max(0, Math.floor((sx - o.x) / cell)));
    let cy = Math.min(ny - 1, Math.max(0, Math.floor((sy - o.y) / cell)));
    let cz = Math.min(nz - 1, Math.max(0, Math.floor((sz - o.z) / cell)));
    const stx = dx > 0 ? 1 : -1, sty = dy > 0 ? 1 : -1, stz = dz > 0 ? 1 : -1;
    const tdx = Math.abs(cell / dx), tdy = Math.abs(cell / dy), tdz = Math.abs(cell / dz);
    let tmx = Math.abs(dx) < 1e-12 ? Infinity : ((o.x + (cx + (dx > 0 ? 1 : 0)) * cell) - ox) / dx;
    let tmy = Math.abs(dy) < 1e-12 ? Infinity : ((o.y + (cy + (dy > 0 ? 1 : 0)) * cell) - oy) / dy;
    let tmz = Math.abs(dz) < 1e-12 ? Infinity : ((o.z + (cz + (dz > 0 ? 1 : 0)) * cell) - oz) / dz;
    for (let guard = 0; guard < 4096; guard++) {
      const c = (cz * ny + cy) * nx + cx;
      for (let i = cnt[c], e = cnt[c + 1]; i < e; i++) {
        const t = items[i]; if (stamp[t] === query) continue; stamp[t] = query;
        const h = tri(t, ox, oy, oz, dx, dy, dz);
        if (h > near && h < far) return true;
      }
      const tn = Math.min(tmx, tmy, tmz);
      if (tn > t1) return false;
      if (tn === tmx) { cx += stx; tmx += tdx; if (cx < 0 || cx >= nx) return false; }
      else if (tn === tmy) { cy += sty; tmy += tdy; if (cy < 0 || cy >= ny) return false; }
      else { cz += stz; tmz += tdz; if (cz < 0 || cz >= nz) return false; }
    }
    return false;
  }
  return { blocked, triangles: total, cells: NC };
}
