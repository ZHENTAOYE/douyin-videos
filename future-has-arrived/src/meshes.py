"""Small procedural mesh builders (numpy) for gl3d.Mesh: revolve, cylinder, box, tube."""
import math
import numpy as np


def _tri(pos, nrm, col, faces):
    return pos[faces].reshape(-1, 3), nrm[faces].reshape(-1, 3), col[faces].reshape(-1, 4)


def revolve(profile, segs=64, color=(1, 1, 1, 1), axis_dir=(0, 1, 0)):
    """profile: (N,2) of (radius, height) along the y axis -> triangles."""
    P = []
    N = []
    prof = np.asarray(profile, float)
    for k in range(segs + 1):
        a = 2 * math.pi * k / segs
        c, s = math.cos(a), math.sin(a)
        for i, (r, y) in enumerate(prof):
            P.append((r * c, y, r * s))
            # normal from profile tangent
            j0, j1 = max(0, i - 1), min(len(prof) - 1, i + 1)
            dr, dy = prof[j1, 0] - prof[j0, 0], prof[j1, 1] - prof[j0, 1]
            nr, ny = dy, -dr
            ln = math.hypot(nr, ny) + 1e-9
            N.append((nr / ln * c, ny / ln, nr / ln * s))
    P, N = np.array(P), np.array(N)
    C = np.tile(color, (len(P), 1))
    n = len(prof)
    F = []
    for k in range(segs):
        for i in range(n - 1):
            a, b = k * n + i, (k + 1) * n + i
            F += [(a, b, a + 1), (a + 1, b, b + 1)]
    return _tri(P, N, C, np.array(F))


def cylinder(p0, p1, r, segs=24, color=(1, 1, 1, 1), caps=True):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    ax = p1 - p0
    L = np.linalg.norm(ax)
    ax /= L
    tmp = np.array([1, 0, 0]) if abs(ax[0]) < 0.9 else np.array([0, 1, 0])
    u = np.cross(ax, tmp)
    u /= np.linalg.norm(u)
    v = np.cross(ax, u)
    P, N, F = [], [], []
    for k in range(segs + 1):
        a = 2 * math.pi * k / segs
        d = u * math.cos(a) + v * math.sin(a)
        P += [p0 + d * r, p1 + d * r]
        N += [d, d]
    for k in range(segs):
        a = 2 * k
        F += [(a, a + 2, a + 1), (a + 1, a + 2, a + 3)]
    if caps:
        base = len(P)
        P += [p0, p1]
        N += [-ax, ax]
        for k in range(segs):
            a = 2 * k
            P += [p0 + (u * math.cos(2 * math.pi * k / segs) + v * math.sin(2 * math.pi * k / segs)) * r]
            N += [-ax]
        for k in range(segs):
            F += [(base, base + 2 + k, base + 2 + (k + 1) % segs)]
    P, N = np.array(P), np.array(N)
    C = np.tile(color, (len(P), 1))
    return _tri(P, N, C, np.array(F))


def box(center, size, color=(1, 1, 1, 1)):
    c, s = np.asarray(center, float), np.asarray(size, float) / 2
    faces = [((1, 0, 0), [(1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)]),
             ((-1, 0, 0), [(-1, -1, 1), (-1, 1, 1), (-1, 1, -1), (-1, -1, -1)]),
             ((0, 1, 0), [(-1, 1, -1), (-1, 1, 1), (1, 1, 1), (1, 1, -1)]),
             ((0, -1, 0), [(-1, -1, 1), (-1, -1, -1), (1, -1, -1), (1, -1, 1)]),
             ((0, 0, 1), [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]),
             ((0, 0, -1), [(1, -1, -1), (-1, -1, -1), (-1, 1, -1), (1, 1, -1)])]
    P, N = [], []
    for n, q in faces:
        for i in (0, 1, 2, 0, 2, 3):
            P.append(c + np.array(q[i]) * s)
            N.append(n)
    P, N = np.array(P), np.array(N, float)
    return P, N, np.tile(color, (len(P), 1))


def prism(center, radius, height, sides=10, color=(1, 1, 1, 1)):
    P, N, C = cylinder(np.asarray(center) - [0, height / 2, 0], np.asarray(center) + [0, height / 2, 0], radius,
                       segs=sides, color=color)
    return P, N, C


def merge(*parts):
    P = np.concatenate([p[0] for p in parts])
    N = np.concatenate([p[1] for p in parts])
    C = np.concatenate([p[2] for p in parts])
    return P, N, C


def rotate(part, R, t=(0, 0, 0)):
    P, N, C = part
    return P @ R.T + np.asarray(t), N @ R.T, C


def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
