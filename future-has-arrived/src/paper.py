"""Procedural aged-paper texture (generated once, cached)."""
import os
import numpy as np, cv2
from gfx import fbm_2d
from config import BUILD

PW, PH = 2112, 1188


def make_paper():
    path = f'{BUILD}/cache/paper.npy'
    if os.path.exists(path):
        return np.load(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rng = np.random.default_rng(5)
    h, w = PH, PW
    base = np.array([0.80, 0.70, 0.52], np.float32)
    n1 = fbm_2d(h, w, 420, seed=1, octaves=5)
    n2 = fbm_2d(h, w, 60, seed=2, octaves=4)
    n3 = fbm_2d(h, w, 6, seed=3, octaves=2)
    lum = 0.93 + 0.16 * (n1 - 0.5) + 0.07 * (n2 - 0.5) + 0.05 * (n3 - 0.5)

    # paper fibres
    fib = np.zeros((h, w), np.float32)
    for _ in range(9000):
        x, y = rng.integers(0, w), rng.integers(0, h)
        ang = rng.normal(0, 0.6) + (np.pi / 2 if rng.random() < 0.3 else 0)
        L = rng.integers(8, 70)
        x2, y2 = int(x + L * np.cos(ang)), int(y + L * np.sin(ang))
        cv2.line(fib, (int(x), int(y)), (x2, y2), float(rng.choice([-1, 1]) * rng.uniform(0.3, 1.0)), 1, cv2.LINE_AA)
    fib = cv2.GaussianBlur(fib, (0, 0), 0.8)
    lum += 0.035 * fib

    img = base[None, None, :] * lum[..., None]

    # stains: soft rings that darken / brown the paper
    brown = np.array([0.62, 0.45, 0.25], np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    for _ in range(6):
        cx, cy = rng.uniform(0, w), rng.uniform(0, h)
        r0 = rng.uniform(80, 320)
        rx, ry = r0 * rng.uniform(0.8, 1.3), r0 * rng.uniform(0.8, 1.3)
        d = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
        wob = (fbm_2d(h, w, 90, seed=int(rng.integers(1000)), octaves=3) - 0.5) * 0.25
        d = d + wob
        ring = np.exp(-((d - 1.0) / 0.05) ** 2) * 0.30 + np.clip(1 - d, 0, 1) * 0.14
        k = rng.uniform(0.15, 0.4)
        img = img * (1 - k * ring[..., None]) + brown * (k * ring[..., None]) * 0.85

    # foxing spots
    fox = np.zeros((h, w), np.float32)
    for _ in range(140):
        cv2.circle(fox, (int(rng.integers(0, w)), int(rng.integers(0, h))), int(rng.integers(1, 7)),
                   float(rng.uniform(0.2, 0.8)), -1, cv2.LINE_AA)
    fox = cv2.GaussianBlur(fox, (0, 0), 2.2)
    img = img * (1 - 0.35 * fox[..., None]) + brown * 0.6 * (0.35 * fox[..., None])

    # aged, slightly burnt edges
    edge = np.minimum.reduce([xx, w - 1 - xx, yy, h - 1 - yy])
    edge = edge + (fbm_2d(h, w, 50, seed=9, octaves=4) - 0.5) * 90
    e = np.clip(1 - edge / 170, 0, 1) ** 1.6
    img = img * (1 - 0.55 * e[..., None]) + np.array([0.35, 0.22, 0.10], np.float32) * (0.4 * e[..., None])

    # faint vertical fold
    fold_x = int(w * 0.52)
    fold = np.exp(-((xx - fold_x) / 3.0) ** 2) * 0.10 - np.exp(-((xx - fold_x - 5) / 6.0) ** 2) * 0.05
    img = img * (1 - fold[..., None])

    img = np.clip(img, 0, 1).astype(np.float32)
    np.save(path, img)
    return img
