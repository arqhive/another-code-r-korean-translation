"""BRLYT 창(pane) 목록 읽기·위치 수정. pan1/pic1/txt1/wnd1/bnd1 공통 머리:
+8 flags, +9 origin, +A alpha, +C 이름[16], +1C 사용자정보[8], +24 이동 xyz, +30 회전 xyz, +3C 크기 xy, +44 폭·높이 (float)"""
import struct

KINDS = (b'pan1', b'pic1', b'txt1', b'wnd1', b'bnd1')


def panes(d):
    """[(오프셋, 종류, 이름, (x, y, z), (sx, sy), (w, h))]"""
    out = []; o = struct.unpack('>H', d[0xC:0xE])[0]; n = struct.unpack('>H', d[0xE:0x10])[0]
    for _ in range(n):
        mg = d[o:o + 4]; sz = struct.unpack('>I', d[o + 4:o + 8])[0]
        if mg in KINDS:
            nm = d[o + 0xC:o + 0x1C].split(b'\0')[0].decode('ascii', 'replace')
            out.append((o, mg.decode(), nm, struct.unpack('>3f', d[o + 0x24:o + 0x30]),
                        struct.unpack('>2f', d[o + 0x3C:o + 0x44]), struct.unpack('>2f', d[o + 0x44:o + 0x4C])))
        o += sz
    return out


def set_pos(d, name, x=None, y=None, w=None, h=None):
    d = bytearray(d)
    for o, k, nm, t, s, wh in panes(d):
        if nm == name:
            if x is not None: struct.pack_into('>f', d, o + 0x24, x)
            if y is not None: struct.pack_into('>f', d, o + 0x28, y)
            if w is not None: struct.pack_into('>f', d, o + 0x44, w)
            if h is not None: struct.pack_into('>f', d, o + 0x48, h)
            return bytes(d)
    raise KeyError(name)


def textures(d):
    """txl1 텍스처 이름 목록"""
    o = d.find(b'txl1'); n = struct.unpack('>H', d[o + 8:o + 10])[0]; base = o + 12; out = []
    for i in range(n):
        no = struct.unpack('>I', d[base + i * 8:base + i * 8 + 4])[0]
        out.append(d[base + no:d.index(b'\0', base + no)].decode('ascii'))
    return out


def materials(d):
    """mat1 → [첫 텍스처 번호 또는 None]"""
    o = d.find(b'mat1'); n = struct.unpack('>H', d[o + 8:o + 10])[0]; out = []
    for i in range(n):
        mo = o + struct.unpack('>I', d[o + 12 + i * 4:o + 16 + i * 4])[0]
        flags = struct.unpack('>I', d[mo + 0x3C:mo + 0x40])[0]
        out.append(struct.unpack('>H', d[mo + 0x40:mo + 0x42])[0] if flags & 0xF else None)
    return out


def pic_texture(d):
    """pic1 창 이름 → 첫 텍스처 이름"""
    tx = textures(d); ms = materials(d); out = {}
    for o, k, nm, t, s, wh in panes(d):
        if k == 'pic1':
            mi = struct.unpack('>H', d[o + 0x5C:o + 0x5E])[0]
            ti = ms[mi] if mi < len(ms) else None
            out[nm] = tx[ti] if ti is not None and ti < len(tx) else None
    return out
