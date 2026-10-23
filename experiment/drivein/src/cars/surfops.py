"""Surface operations on a marching-cubes body: exact level-set cuts along analytic curves, face labelling by
priority rules, per-label inset (panel gaps, glass, lamp recesses) with generated side walls.
"""
import numpy as np
from carlib import normalize, Parts

class CutSurface:
    def __init__(self, V, F, N, normal_fn=None):
        self.V = V.copy(); self.F = F.copy(); self.N = N.copy()
        self.fns = {}          # name -> fn(V, N) -> per-vertex values
        self.vals = {}         # name -> per-vertex exact values
        self.normal_fn = normal_fn

    def add_fn(self, name, fn):
        self.fns[name] = fn
        self.vals[name] = np.asarray(fn(self.V, self.N), float)

    def cut(self, name, offset=0.0, iters=6):
        """Split along fns[name] == offset (exact on edges, refined by regula falsi)."""
        fn = self.fns[name]
        V, F, N = self.V, self.F, self.N
        g = self.vals[name] - offset
        g = np.where(np.abs(g) < 1e-9, 1e-9, g)
        nV = len(V)
        pos = g > 0
        fp = pos[F]; cnt = fp.sum(1)
        cross = (cnt == 1) | (cnt == 2)
        if not cross.any():
            return
        Fk = F[~cross]; Fc = F[cross]; pc = fp[cross]; cc = cnt[cross]
        lonely = np.where((cc == 1)[:, None], pc, ~pc)
        k = np.argmax(lonely, 1); r = np.arange(len(Fc))
        a = Fc[r, k]; b = Fc[r, (k + 1) % 3]; c = Fc[r, (k + 2) % 3]
        E = np.concatenate([np.sort(np.stack([a, b], 1), 1), np.sort(np.stack([a, c], 1), 1)])
        key = E[:, 0] * nV + E[:, 1]
        ukey, inv = np.unique(key, return_inverse=True)
        e0 = ukey // nV; e1 = ukey % nV
        g0 = g[e0]; g1 = g[e1]
        lo = np.zeros(len(ukey)); hi = np.ones(len(ukey)); glo = g0.copy(); ghi = g1.copy()
        t = glo / (glo - ghi)
        for _ in range(iters):
            P = V[e0] + t[:, None] * (V[e1] - V[e0])
            Nn = normalize(N[e0] + t[:, None] * (N[e1] - N[e0]))
            gt = np.asarray(fn(P, Nn), float) - offset
            same = np.sign(gt) == np.sign(glo)
            lo = np.where(same, t, lo); glo = np.where(same, gt, glo)
            hi = np.where(same, hi, t); ghi = np.where(same, ghi, gt)
            den = glo - ghi
            t = np.where(np.abs(den) > 1e-12, lo + (hi - lo) * glo / np.where(np.abs(den) > 1e-12, den, 1), 0.5 * (lo + hi))
            t = np.clip(t, lo, hi)
        newV = V[e0] + t[:, None] * (V[e1] - V[e0])
        newN = normalize(N[e0] + t[:, None] * (N[e1] - N[e0]))
        if self.normal_fn is not None:
            newN = self.normal_fn(newV)
        ids = nV + np.arange(len(ukey))
        p = ids[inv[:len(Fc)]]; q = ids[inv[len(Fc):]]
        T = np.concatenate([np.stack([a, p, q], 1), np.stack([p, b, c], 1), np.stack([p, c, q], 1)])
        self.V = np.concatenate([V, newV]); self.N = np.concatenate([N, newN])
        self.F = np.concatenate([Fk, T])
        for nm, f2 in self.fns.items():
            if nm == name:
                self.vals[nm] = np.concatenate([self.vals[nm], np.full(len(newV), offset)])
            else:
                self.vals[nm] = np.concatenate([self.vals[nm], np.asarray(f2(newV, newN), float)])

    def face_vals(self):
        fm = {k: v[self.F].mean(1) for k, v in self.vals.items()}
        fm['c'] = self.V[self.F].mean(1)
        fn = normalize(self.N[self.F].mean(1))
        fm['n'] = fn
        return fm

def build_labelled(cs, labels, rules, default, col_fn=None, parts=None, node='body'):
    """labels: name -> dict(mat, depth=0, wall='trim_black', wall_col=0.35, raise=0)
    rules: list of (label_name, fn(fm)->bool mask) in priority order (first match wins).
    Adds meshes to parts (node). Returns parts and per-face label array."""
    fm = cs.face_vals()
    nF = len(cs.F)
    names = list(labels.keys())
    lab = np.full(nF, names.index(default))
    done = np.zeros(nF, bool)
    for lname, rule in rules:
        m = rule(fm) & ~done
        lab[m] = names.index(lname); done |= m
    parts = parts or Parts()
    V, F, N = cs.V, cs.F, cs.N
    depth_of = np.array([labels[n].get('depth', 0.0) for n in names])
    COL = col_fn(V, N) if col_fn else np.ones((len(V), 3))
    # group meshes
    for li, ln in enumerate(names):
        m = lab == li
        if not m.any() or labels[ln].get('skip'):
            continue
        Fm = F[m]
        used = np.unique(Fm)
        remap = -np.ones(len(V), np.int64); remap[used] = np.arange(len(used))
        d = depth_of[li]
        Vl = V[used] - N[used] * d
        col = COL[used] * labels[ln].get('col', 1.0)
        Fl = remap[Fm]; Nl = N[used]
        if labels[ln].get('nfn'):          # optional shading-normal override for a label (e.g. matte arch liners)
            Nl = labels[ln]['nfn'](Vl, Nl)
        if labels[ln].get('dec') and len(Fl) > 200:
            # hidden/dark areas (underside, wheel wells): border-preserving decimation, attributes re-sampled by nearest
            from carlib import decimate_fqmr
            from scipy.spatial import cKDTree
            V2, F2 = decimate_fqmr(Vl, Fl, max(100, int(len(Fl) * labels[ln]['dec'])), preserve_border=True)
            idx = cKDTree(Vl).query(V2)[1]
            Vl, Fl, Nl, col = V2, F2, Nl[idx], col[idx]
        parts.add(node, Vl, Fl, labels[ln]['mat'], N=Nl, COL=np.c_[col, np.ones(len(col))])
    # walls along edges between labels with different depth
    E = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    EL = np.tile(lab, 3)
    key = E[:, 0] * len(V) + E[:, 1]
    rkey = E[:, 1] * len(V) + E[:, 0]
    order = np.argsort(key); sk = key[order]
    pos = np.searchsorted(sk, rkey)
    pos = np.clip(pos, 0, len(sk) - 1)
    has = sk[pos] == rkey
    other = order[pos]
    idx = np.where(has)[0]
    la = EL[idx]; lb = EL[other[idx]]
    da = depth_of[la]; db = depth_of[lb]
    sel = da < db - 1e-6    # this half-edge belongs to shallower label a, neighbour b deeper
    idx = idx[sel]; la = la[sel]; lb = lb[sel]
    if len(idx):
        u = E[idx, 0]; v = E[idx, 1]
        dA = depth_of[la][:, None]; dB = depth_of[lb][:, None]
        pu_t = V[u] - N[u] * dA; pv_t = V[v] - N[v] * dA
        pu_b = V[u] - N[u] * dB; pv_b = V[v] - N[v] * dB
        n = len(idx)
        for wm in set(labels[names[l]].get('wall', 'trim_black') for l in lb):
            ws = np.array([labels[names[l]].get('wall', 'trim_black') == wm for l in lb])
            k = ws.sum()
            Vw = np.concatenate([pu_t[ws], pv_t[ws], pv_b[ws], pu_b[ws]])
            i = np.arange(k)
            Fw = np.concatenate([np.stack([i, i + k, i + 2 * k], 1), np.stack([i, i + 2 * k, i + 3 * k], 1)])
            # orient toward the deeper region: -cross(N, e)
            e = (V[v] - V[u])[ws]; Nm = normalize(N[u] + N[v])[ws]
            want = -np.cross(Nm, e)
            fnrm = np.cross(Vw[Fw[:, 1]] - Vw[Fw[:, 0]], Vw[Fw[:, 2]] - Vw[Fw[:, 0]])
            wq = np.concatenate([want, want])
            flip = np.einsum('ij,ij->i', fnrm, wq) < 0
            Fw[flip] = Fw[flip][:, ::-1]
            wc = np.array([labels[names[l]].get('wall_col', 0.4) for l in lb])[ws]
            colw = np.concatenate([wc, wc, wc * 0.6, wc * 0.6])
            parts.add(node, Vw, Fw, wm, COL=np.c_[np.repeat(colw[:, None], 3, 1), np.ones(len(colw))], flat=True)
    return parts, lab
