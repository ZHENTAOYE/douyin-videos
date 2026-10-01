"""Procedural chip die-shot texture (floorplan of CPU / GPU / cache / IO blocks with thin-film colours)."""
import os
import numpy as np, cv2
from gfx import fbm_2d
from config import BUILD

N = 4096


def _palette(rng):
    # thin-film interference colours seen in real die photos
    pals = [(0.42, 0.30, 0.62), (0.22, 0.45, 0.42), (0.62, 0.50, 0.26), (0.28, 0.35, 0.62),
            (0.55, 0.32, 0.40), (0.36, 0.52, 0.30), (0.62, 0.42, 0.22), (0.30, 0.26, 0.46)]
    return np.array(pals[rng.integers(len(pals))], np.float32) * rng.uniform(0.75, 1.15)


def _split(rng, x0, y0, x1, y1, depth, out):
    w, h = x1 - x0, y1 - y0
    if depth == 0 or (w < 380 and h < 380) or (depth < 3 and rng.random() < 0.18):
        out.append((x0, y0, x1, y1))
        return
    if w > h * (0.7 + 0.6 * rng.random()):
        m = int(x0 + w * rng.uniform(0.3, 0.7))
        _split(rng, x0, y0, m, y1, depth - 1, out)
        _split(rng, m, y0, x1, y1, depth - 1, out)
    else:
        m = int(y0 + h * rng.uniform(0.3, 0.7))
        _split(rng, x0, y0, x1, m, depth - 1, out)
        _split(rng, x0, m, x1, y1, depth - 1, out)


def thin_film(T):
    ph = np.array([0.0, 0.33, 0.67], np.float32)
    c = 0.5 + 0.5 * np.cos(2 * np.pi * (T[..., None] * 1.6 + ph))
    lum = c.mean(axis=-1, keepdims=True)
    c = lum + (c - lum) * 0.55          # muted
    return 0.16 + 0.55 * c


def make_die():
    path = f'{BUILD}/cache/die.npy'
    if os.path.exists(path):
        return np.load(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rng = np.random.default_rng(12)
    yy, xx = np.mgrid[0:N, 0:N]
    m = 150      # IO ring margin
    blocks = []
    _split(rng, m, m, N - m, N - m, 6, blocks)
    T = 0.45 * fbm_2d(N, N, 900, seed=7, octaves=3)
    lum = np.full((N, N), 0.55, np.float32)
    fine = fbm_2d(N, N, 2.5, seed=4, octaves=2)
    med = fbm_2d(N, N, 24, seed=5, octaves=3)
    for (x0, y0, x1, y1) in blocks:
        g = 7
        x0g, y0g, x1g, y1g = x0 + g, y0 + g, x1 - g, y1 - g
        if x1g <= x0g or y1g <= y0g:
            continue
        kind = rng.choice(['sram', 'logic', 'array', 'analog'], p=[0.3, 0.42, 0.2, 0.08])
        sub = (slice(y0g, y1g), slice(x0g, x1g))
        T[sub] += rng.uniform(-0.12, 0.25)
        X, Y = xx[sub] - x0g, yy[sub] - y0g
        if kind == 'sram':
            p = int(rng.integers(3, 5))
            pat = 0.62 + 0.20 * (((X // p) + (Y // p)) % 2) + 0.12 * ((Y % (p * 24)) < 2)
            pat = pat + 0.10 * ((X % (p * 40)) < 3)
        elif kind == 'logic':
            rows = int(rng.integers(5, 8))
            dens = 0.55 + 0.45 * med[sub]
            pat = 0.42 + 0.38 * (Y % rows < rows - 1) * (fine[sub] < dens) + 0.12 * fine[sub]
        elif kind == 'array':
            nx, ny = int(rng.integers(2, 6)), int(rng.integers(2, 5))
            cw, ch = (x1g - x0g) / nx, (y1g - y0g) / ny
            cx, cy = (X % cw) / cw, (Y % ch) / ch
            # identical sub-blocks: an inner cache stripe + logic body
            inner = ((cx > 0.04) & (cx < 0.96) & (cy > 0.04) & (cy < 0.96)).astype(np.float32)
            cache = ((cy > 0.08) & (cy < 0.32)).astype(np.float32)
            pat = 0.35 + inner * (0.35 + 0.18 * cache * (((X // 3) + (Y // 3)) % 2) + 0.12 * (((X % cw).astype(int) // 5) % 2))
        else:
            pat = 0.38 + 0.4 * fbm_2d(y1g - y0g, x1g - x0g, 30, seed=int(rng.integers(999)), octaves=3)
        lum[sub] = pat
    img = thin_film(T) * lum[..., None] * 1.25
    # routing channels between blocks read as thin bright lines
    edges = np.zeros((N, N), np.float32)
    for (x0, y0, x1, y1) in blocks:
        cv2.rectangle(edges, (int(x0 + 3), int(y0 + 3)), (int(x1 - 3), int(y1 - 3)), 1.0, 2)
    img = img * (1 - 0.45 * edges[..., None]) + np.array([0.80, 0.70, 0.50], np.float32) * (0.45 * edges[..., None])
    grid = ((xx % 256) < 2) | ((yy % 256) < 2)
    img[grid] = img[grid] * 0.75 + np.array([0.70, 0.60, 0.42], np.float32) * 0.25
    ring = (xx < m) | (yy < m) | (xx >= N - m) | (yy >= N - m)
    img[ring] = np.array([0.12, 0.11, 0.10], np.float32)
    dist = np.minimum.reduce([xx, yy, N - 1 - xx, N - 1 - yy])
    pad = ring & (((xx + 20) % 64) < 40) & (((yy + 20) % 64) < 40) & (dist > 30) & (dist < 110)
    img[pad] = np.array([0.78, 0.68, 0.46], np.float32)
    img = cv2.GaussianBlur(img, (0, 0), 0.6)
    img = np.clip(img, 0, 1).astype(np.float32)
    np.save(path, img)
    return img
