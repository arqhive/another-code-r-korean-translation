"""경로 키로 디스크 속 그림 하나를 읽는다(GPT 재작업 준비·반영, 현황판용).
키 = REVOLUTION 기준 경로 + 묶음 안 경로 + '#' + TPL 번호 또는 BRRES 텍스처 이름.
  예) 'LYT/002/NAME_AP030.arc/NAME_AP030/timg/NAME_AP030.tpl#0'
      'PUZZLE/Z050_01.acrarc/Z050_01.ARC/lyt/timg/plate01.tpl#0'   (묶음 안의 묶음)
      'MAP/A_M050_D.acrarc/A_M050_D.BRTEX#A0065_03D_COM_kanban'
판마다 파일 이름 대소문자가 달라서(일본판 .arc / 유럽판 .ARC) 디스크 파일은 대소문자를 무시하고 찾는다."""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gxtex
import paths
import u8

U8_MAGIC = b'\x55\xAA\x38\x2D'
ROOTS = {'jp': paths.JP, 'eu': paths.EU}


def _find_file(base, parts):
    """base 아래에서 parts 를 앞에서부터 대소문자 무시로 따라가 실제 파일을 찾는다 → (경로, 남은 parts)"""
    cur = base
    for i, p in enumerate(parts):
        if not os.path.isdir(cur): return None, None
        m = [x for x in os.listdir(cur) if x.lower() == p.lower()]
        if not m: return None, None
        cur = os.path.join(cur, m[0])
        if os.path.isfile(cur): return cur, parts[i + 1:]
    return None, None


def raw(region, key):
    """→ (텍스처를 담은 파일 자료, 이미지 이름/번호). region: 'jp' | 'eu' | 'build'(빌드 결과 우선, 없으면 유럽판)"""
    path, nm = key.rsplit('#', 1)
    parts = path.split('/')
    f = rest = None
    if region == 'build':
        f, rest = _find_file(str(paths.BUILD / 'files/REVOLUTION'), parts)
        region = 'eu'
    if f is None:
        f, rest = _find_file(str(ROOTS[region] / 'files/REVOLUTION'), parts)
    if f is None: return None, nm
    d = open(f, 'rb').read()
    while rest:   # 묶음(U8) 안으로
        fs = {k.lower(): v for k, v in u8.U8(d).files().items()}
        for j in range(len(rest), 0, -1):
            k = '/'.join(rest[:j]).lower()
            if k in fs:
                d = fs[k]; rest = rest[j:]; break
        else:
            return None, nm
    return d, nm


def info(region, key):
    """→ (w, h, 형식 번호, 자료, 팔레트) 또는 None"""
    d, nm = raw(region, key)
    if d is None: return None
    if d[:4] == b'\x00\x20\xaf\x30':
        for i, w, h, f, off, nb, pal in gxtex.tpl_images(d):
            if str(i) == nm: return w, h, f, d[off:off + nb], pal
        return None
    i = d.find(b'TEX0')
    while i >= 0:
        doff, noff = struct.unpack('>II', d[i + 0x10:i + 0x18])
        e = d.index(b'\0', i + noff)
        if d[i + noff:e].decode('ascii', 'replace') == nm:
            w, h, f = struct.unpack('>HHI', d[i + 0x1C:i + 0x24])
            return w, h, f, d[i + doff:i + doff + gxtex.size(w, h, f)], None
        i = d.find(b'TEX0', i + 4)
    return None


def get(region, key):
    """→ PIL RGBA 또는 None"""
    t = info(region, key)
    return gxtex.decode(t[3], t[0], t[1], t[2], t[4]) if t else None
