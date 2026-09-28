"""(조사용) 디스크 안 모든 이미지(TPL·BRRES TEX0·JPG)를 경로 키와 원본 해시로 모은다.
키 = 파일 경로(REVOLUTION 기준) + 묶음 안 경로 + '#' + 이미지 이름(TEX0) 또는 번호(TPL).
사용: import texscan; texscan.scan('jp') → {키: (해시, 종류, 자료 위치 정보)}"""
import hashlib
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gxtex
import paths
import u8

SKIP = ('.thp', '.brsar', '.brstm', '.bmg', '.brfnt', '.rel', '.mess', '.str')


def tex0_list(d):
    """BRRES 안 TEX0/PLT0 → [(이름, w, h, fmt, 자료, 팔레트 rgba 또는 None)]"""
    plts = {}; texs = []
    i = d.find(b'PLT0')
    while i >= 0:
        try:
            doff, noff, pf, pn = struct.unpack('>IIIH', d[i + 0x10:i + 0x1E])
            nm = _name(d, i + noff)
            vals = gxtex.np.frombuffer(d[i + doff:i + doff + 2 * pn], dtype='>u2').astype(gxtex.np.uint16)
            if pf == 0:
                g = (vals & 255).astype(gxtex.np.uint8); pal = gxtex.np.stack([g, g, g, (vals >> 8).astype(gxtex.np.uint8)], -1)
            elif pf == 1:
                pal = gxtex._565(vals)
            else:
                pal = gxtex._5a3(vals)
            plts[nm] = pal
        except Exception:
            pass
        i = d.find(b'PLT0', i + 4)
    i = d.find(b'TEX0')
    while i >= 0:
        try:
            doff, noff = struct.unpack('>II', d[i + 0x10:i + 0x18])
            w, h, f = struct.unpack('>HHI', d[i + 0x1C:i + 0x24])
            if f in gxtex.FMT and 0 < w <= 1024 and 0 < h <= 1024:
                nm = _name(d, i + noff)
                n = gxtex.size(w, h, f)
                texs.append((nm, w, h, f, d[i + doff:i + doff + n], plts.get(nm)))
        except Exception:
            pass
        i = d.find(b'TEX0', i + 4)
    return texs


def _name(d, p):
    e = d.index(b'\0', p)
    return d[p:e].decode('ascii', 'replace')


def images(d):
    """파일 자료 → [(이름, w, h, fmt, 원본 바이트, 팔레트)]  JPG 는 (이름 'jpg', 0, 0, 'jpg', 바이트, None)"""
    m = d[:4]
    if m == b'bres':
        return tex0_list(d)
    if m == b'\x00\x20\xaf\x30':
        out = []
        for idx, w, h, f, off, nb, pal in gxtex.tpl_images(d):
            out.append((str(idx), w, h, f, d[off:off + nb], pal))
        return out
    if m[:3] == b'\xff\xd8\xff':
        return [('jpg', 0, 0, 'jpg', d, None)]
    return []


def walk(prefix, d, out, keep):
    if d[:4] == b'\x55\xAA\x38\x2D':
        for k, v in u8.U8(d).files().items():
            walk(prefix + '/' + k, v, out, keep)
        return
    for nm, w, h, f, raw, pal in images(d):
        key = prefix + '#' + nm
        hsh = hashlib.sha1(raw + (pal.tobytes() if pal is not None else b'')).hexdigest()
        out[key] = (hsh, w, h, f)
        if keep is not None and keep(key, hsh):
            keep.store[key] = (w, h, f, raw, pal)


def scan(region, keep=None):
    base = (paths.JP if region == 'jp' else paths.EU) / 'files/REVOLUTION'
    out = {}
    for dp, _, fs in os.walk(base):
        for f in fs:
            if f.lower().endswith(SKIP): continue
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, base).replace(os.sep, '/')
            walk(rel, open(p, 'rb').read(), out, keep)
    return out


def to_png(w, h, f, raw, pal):
    import io
    from PIL import Image
    if f == 'jpg':
        return Image.open(io.BytesIO(raw)).convert('RGBA')
    return gxtex.decode(raw, w, h, f, pal)
