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
    """4x4 RGBA → 8바이트. 투명 픽셀(알파<128)이 있으면 3색+투명 모드.
    끝점 후보(주성분 양끝·밝기 극값 픽셀 쌍)를 모두 시험해 오차가 가장 작은 쌍을 고르고, 4색 모드는 최소제곱으로 다듬는다
    (주성분 양끝만 쓰던 방식은 가는 글자에서 글자 속에 얼룩이 생겼다, 10/31 타이틀 글씨)"""
    p = px.reshape(16, 4).astype(np.float64)
    tr = p[:, 3] < 128; op = p[~tr, :3]
    if len(op) == 0:
        return struct.pack('>HHI', 0, 0, 0xFFFFFFFF)
    c565 = lambda c: _c565(np.clip(np.round(c), 0, 255))
    cands = set()
    mean = op.mean(0)
    if len(op) > 1 and op.std() > 0:
        try:
            axis = np.linalg.eigh(np.cov((op - mean).T))[1][:, -1]
            t = (op - mean) @ axis
            cands.add((c565(mean + axis * t.max()), c565(mean + axis * t.min())))
        except Exception:
            pass
    order = np.argsort(op @ [0.299, 0.587, 0.114])
    for a in order[-3:]:
        for b in order[:3]:
            cands.add((c565(op[a]), c565(op[b])))

    def ev(v0, v1):
        if tr.any():
            if v0 > v1: v0, v1 = v1, v0
            e0, e1 = _e565(v0), _e565(v1)
            pal = np.stack([e0, e1, (e0 + e1) / 2])
            d = ((p[:, None, :3] - pal[None]) ** 2).sum(2); idx = d.argmin(1)
            err = d[np.arange(16), idx][~tr].sum(); idx[tr] = 3
        else:
            if v0 < v1: v0, v1 = v1, v0
            if v0 == v1:
                return ((op - _e565(v0)) ** 2).sum(), v0, v1, np.zeros(16, int)
            e0, e1 = _e565(v0), _e565(v1)
            pal = np.stack([e0, e1, (2 * e0 + e1) / 3, (e0 + 2 * e1) / 3])
            d = ((p[:, None, :3] - pal[None]) ** 2).sum(2); idx = d.argmin(1)
            err = d[np.arange(16), idx].sum()
        return err, v0, v1, idx

    best = min((ev(a, b) for a, b in cands), key=lambda r: r[0])
    if not tr.any():
        for _ in range(4):
            err, v0, v1, idx = best
            if v0 == v1: break
            w = np.array([1, 0, 2 / 3, 1 / 3])[idx]
            sol = np.linalg.lstsq(np.stack([w, 1 - w], 1), p[:, :3], rcond=None)[0]
            r = ev(c565(sol[0]), c565(sol[1]))
            if r[0] < best[0]: best = r
            else: break
    err, v0, v1, idx = best
    bits = 0
    for i in idx: bits = bits << 2 | int(i)
    return struct.pack('>HHI', v0, v1, bits)


_CACHE = None


def encode(img, f):
    """그림 → GX 텍스처 자료. 결과는 work/cache/gxenc 에 저장해 두고 같은 입력(이 파일 소스+형식+크기+픽셀)이면 재사용"""
    global _CACHE
    import hashlib, os
    a = np.asarray(img.convert('RGBA'), np.uint8)
    if _CACHE is None:
        import paths
        _CACHE = (paths.WORK / 'cache' / 'gxenc', hashlib.sha1(open(__file__, 'rb').read()).hexdigest()[:12])
        _CACHE[0].mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(f'{_CACHE[1]}|{f}|{a.shape}'.encode() + a.tobytes()).hexdigest()
    p = _CACHE[0] / key
    if p.exists():
        return p.read_bytes()
    out = _encode(a, f)
    p.write_bytes(out)
    return out


def _encode(a, f):
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
