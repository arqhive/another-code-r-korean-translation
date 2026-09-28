"""GX 텍스처 인코더: I4·I8·IA4·IA8·RGB565·RGB5A3·RGBA8·CMPR (죄와 벌 2 gxenc.py 기반, 형식 추가)
encode(RGBA 이미지, fmt) → 바이트.  크기는 블록 배수로 0 채움."""
import struct

import numpy as np

import gxtex


def _blocks(a, bw, bh):
    """(H, W, C) → 블록 순서 (nby, nbx, bh, bw, C), 모자라면 0 채움"""
    h, w = a.shape[:2]
    H = (h + bh - 1) // bh * bh; W = (w + bw - 1) // bw * bw
    p = np.zeros((H, W) + a.shape[2:], a.dtype); p[:h, :w] = a
    return p.reshape(H // bh, bh, W // bw, bw, *a.shape[2:]).swapaxes(1, 2)


def _lum(a):
    return (a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114 + 0.5).astype(np.uint8)


def _c565(c):
    return (int(c[0]) >> 3) << 11 | (int(c[1]) >> 2) << 5 | (int(c[2]) >> 3)


def _e565(v):
    r = (v >> 11) & 31; g = (v >> 5) & 63; b = v & 31
    return np.array([r << 3 | r >> 2, g << 2 | g >> 4, b << 3 | b >> 2], np.float32)


def _cmpr_block(px):
    """4x4 RGBA → 8바이트. 투명 픽셀(알파<128)이 있으면 3색+투명 모드"""
    p = px.reshape(16, 4).astype(np.float32)
    tr = p[:, 3] < 128; op = p[~tr, :3]
    if len(op) == 0:
        return struct.pack('>HHI', 0, 0, 0xFFFFFFFF)
    mean = op.mean(0)
    cov = np.cov((op - mean).T) if len(op) > 1 and op.std() > 0 else np.eye(3)
    try:
        axis = np.linalg.eigh(cov)[1][:, -1]
    except Exception:
        axis = np.ones(3) / 3 ** .5
    t = (op - mean) @ axis
    v0, v1 = _c565(np.clip(mean + axis * t.max(), 0, 255)), _c565(np.clip(mean + axis * t.min(), 0, 255))
    if tr.any():
        if v0 > v1: v0, v1 = v1, v0
        e0, e1 = _e565(v0), _e565(v1)
        pal = np.stack([e0, e1, (e0 + e1) / 2])
        idx = ((p[:, None, :3] - pal[None]) ** 2).sum(2).argmin(1); idx[tr] = 3
    else:
        if v0 < v1: v0, v1 = v1, v0
        if v0 == v1:
            return struct.pack('>HHI', v0, v1, 0)
        e0, e1 = _e565(v0), _e565(v1)
        pal = np.stack([e0, e1, (2 * e0 + e1) / 3, (e0 + 2 * e1) / 3])
        idx = ((p[:, None, :3] - pal[None]) ** 2).sum(2).argmin(1)
    bits = 0
    for i in idx: bits = bits << 2 | int(i)
    return struct.pack('>HHI', v0, v1, bits)


def encode(img, f):
    a = np.asarray(img.convert('RGBA'), np.uint8)
    if f == 14:
        b = _blocks(a, 8, 8); out = bytearray()
        for by in range(b.shape[0]):
            for bx in range(b.shape[1]):
                for sy, sx in ((0, 0), (0, 4), (4, 0), (4, 4)):
                    out += _cmpr_block(b[by, bx, sy:sy + 4, sx:sx + 4])
        return bytes(out)
    bw, bh, bpp = gxtex.FMT[f]
    b = _blocks(a, bw, bh).astype(np.uint32)
    L = _lum(b.astype(np.float32)).astype(np.uint32); A = b[..., 3]
    if f == 0:
        v = L >> 4; return ((v[..., 0::2] << 4) | v[..., 1::2]).astype(np.uint8).tobytes()
    if f == 1:
        return L.astype(np.uint8).tobytes()
    if f == 2:
        return (((A >> 4) << 4) | (L >> 4)).astype(np.uint8).tobytes()
    if f == 3:
        return ((A << 8) | L).astype('>u2').tobytes()
    if f == 4:
        return ((b[..., 0] >> 3) << 11 | (b[..., 1] >> 2) << 5 | (b[..., 2] >> 3)).astype('>u2').tobytes()
    if f == 5:
        op = A >= 0xE0
        v1 = 0x8000 | (b[..., 0] >> 3) << 10 | (b[..., 1] >> 3) << 5 | (b[..., 2] >> 3)
        v0 = (A >> 5) << 12 | (b[..., 0] >> 4) << 8 | (b[..., 1] >> 4) << 4 | (b[..., 2] >> 4)
        return np.where(op, v1, v0).astype('>u2').tobytes()
    if f == 6:
        out = bytearray()
        for by in range(b.shape[0]):
            for bx in range(b.shape[1]):
                blk = b[by, bx].reshape(16, 4).astype(np.uint8)
                out += np.stack([blk[:, 3], blk[:, 0]], 1).tobytes() + np.stack([blk[:, 1], blk[:, 2]], 1).tobytes()
        return bytes(out)
    raise ValueError(f'인코딩 미지원 형식 {f}')
