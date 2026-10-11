"""Wii 메뉴 디스크 채널 배너 opening.bnr 읽기·쓰기(「돌격!! 패미컴 워즈 VS」 한글 패치 도구 바탕, TPL 형식 일반화).
구조: 0x40 빈칸 + IMET(채널 이름 10개 언어, UTF-16BE) + U8(meta/banner.bin, icon.bin, sound.bin)
각 .bin = IMD5(32바이트: 'IMD5', 데이터 크기, 0*8, MD5) + LZ77(0x10) 압축 U8(arc/timg/*.tpl, arc/blyt, arc/anim)."""
import hashlib
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gxenc
import gxtex

LANGS = ['일본어', '영어', '독일어', '프랑스어', '스페인어', '이탈리아어', '네덜란드어', '중국어 간체', '중국어 번체', '한국어']


def u8_entries(d):
    """→ [(경로, 노드 번호, 데이터 오프셋, 크기)]"""
    root, hsz, doff = struct.unpack_from('>III', d, 4)
    n = struct.unpack_from('>I', d, root + 8)[0]
    st = root + n * 12
    out = []; path = []; ends = []
    for i in range(1, n):
        t, no, a, b = struct.unpack_from('>BxHII', d, root + i * 12)
        while ends and ends[-1] <= i:
            ends.pop(); path.pop()
        name = d[st + no:].split(b'\0')[0].decode()
        if t == 1:
            path.append(name); ends.append(b)
        else:
            out.append(('/'.join(path + [name]), i, a, b))
    return out


def lz77_dec(d):
    assert d[:4] == b'LZ77' and d[4] == 0x10
    d = d[4:]
    size = d[1] | d[2] << 8 | d[3] << 16; o = 4; out = bytearray()
    while len(out) < size:
        fl = d[o]; o += 1
        for b in range(8):
            if len(out) >= size: break
            if fl & (0x80 >> b):
                x = d[o] << 8 | d[o + 1]; o += 2
                ln = (x >> 12) + 3; disp = (x & 0xFFF) + 1
                for _ in range(ln): out.append(out[-disp])
            else:
                out.append(d[o]); o += 1
    return bytes(out)


def lz77_enc(src):
    out = bytearray(b'LZ77' + bytes([0x10]) + struct.pack('<I', len(src))[:3])
    table = {}
    i = 0; n = len(src)
    while i < n:
        flag_pos = len(out); out.append(0); flag = 0
        for b in range(8):
            if i >= n: break
            best_len = 0; best_d = 0
            key = src[i:i + 3]
            if len(key) == 3:
                for p in reversed(table.get(key, [])[-64:]):
                    dist = i - p
                    if dist > 4096: break
                    if dist < 2: continue  # 일부 해제기 호환(거리 1 회피)
                    ln = 3
                    while ln < 18 and i + ln < n and src[p + ln] == src[i + ln]:
                        ln += 1
                    if ln > best_len:
                        best_len, best_d = ln, dist
                        if ln == 18: break
            if best_len >= 3:
                flag |= 0x80 >> b
                x = ((best_len - 3) << 12) | (best_d - 1)
                out += bytes([x >> 8, x & 0xFF])
                for j in range(i, i + best_len):
                    table.setdefault(src[j:j + 3], []).append(j)
                i += best_len
            else:
                out.append(src[i])
                table.setdefault(key, []).append(i)
                i += 1
        out[flag_pos] = flag
    while len(out) % 4: out.append(0)
    return bytes(out)


def imd5(data):
    return b'IMD5' + struct.pack('>I', len(data)) + b'\0' * 8 + hashlib.md5(data).digest() + data


def bins(bnr):
    """→ {'meta/banner.bin': 해제한 U8, 'meta/icon.bin': …}"""
    i = bnr.find(b'\x55\xaa\x38\x2d'); u8 = bnr[i:]
    return {p: lz77_dec(u8[a + 32:a + b]) for p, _, a, b in u8_entries(u8) if p.endswith(('banner.bin', 'icon.bin'))}


def images(bnr):
    """→ [(bin 경로, U8 안 경로, PIL 이미지, 형식 번호)]"""
    out = []
    for bp, dec in bins(bnr).items():
        for path, _, a, b in u8_entries(dec):
            if path.endswith('.tpl'):
                for idx, w, h, f, off, nb, pal in gxtex.tpl_images(dec[a:a + b]):
                    out.append((bp, path, gxtex.decode(dec[a + off:a + off + nb], w, h, f, pal), f))
    return out


def names(bnr):
    o = 0x5C
    return [bnr[o + k * 0x54:o + (k + 1) * 0x54].decode('utf-16-be').split('\0') for k in range(10)]


def patch_tpl(tpl, img):
    tpl = bytearray(tpl)
    for idx, w, h, f, off, nb, pal in gxtex.tpl_images(bytes(tpl)):
        assert (w, h) == img.size, (w, h, img.size)
        tpl[off:off + nb] = gxenc.encode(img, f)[:nb]
        return bytes(tpl)


def patch_bin(binf, repl):
    """binf: IMD5+LZ77 U8, repl: {U8 내부 경로: PIL 이미지}"""
    dec = bytearray(lz77_dec(binf[32:]))
    for path, _, a, b in u8_entries(dec):
        if path in repl:
            dec[a:a + b] = patch_tpl(bytes(dec[a:a + b]), repl[path])
    assert lz77_dec(lz77_enc(bytes(dec))) == bytes(dec)
    return imd5(lz77_enc(bytes(dec)))


def rebuild_outer(u8, newdata):
    """바깥 U8: 노드·이름표 그대로, 파일 데이터만 교체(32바이트 정렬)"""
    root, hsz, doff = struct.unpack_from('>III', u8, 4)
    head = bytearray(u8[:doff])
    ents = u8_entries(u8)
    body = bytearray(); o = doff
    for path, node, a, b in ents:
        data = newdata.get(path, u8[a:a + b])
        struct.pack_into('>II', head, root + node * 12 + 4, o + len(body), len(data))
        body += data
        while len(body) % 32: body.append(0)
    return bytes(head + body)


def set_names(bnr, names):
    """IMET 채널 이름 칸(0x5C부터 10개 언어 × 0x54바이트 UTF-16BE) 교체 후 헤더 MD5(0~0x600, 해시 칸 0) 갱신.
    names: {칸 번호: 문자열}  (0 일본어, 1 영어, … 9 한국어)"""
    b = bytearray(bnr)
    assert b[0x40:0x44] == b'IMET'
    for slot, s in names.items():
        raw = s.encode('utf-16-be')
        assert len(raw) < 0x54, (slot, s)
        o = 0x5C + slot * 0x54
        b[o:o + 0x54] = raw.ljust(0x54, b'\0')
    b[0x5F0:0x600] = bytes(16)
    b[0x5F0:0x600] = hashlib.md5(bytes(b[:0x600])).digest()
    return bytes(b)


def patch_bnr(bnr, banner_repl, icon_repl):
    i = bnr.find(b'\x55\xaa\x38\x2d')
    u8 = bnr[i:]
    ents = {p: u8[a:a + b] for p, _, a, b in u8_entries(u8)}
    new = {}
    if banner_repl: new['meta/banner.bin'] = patch_bin(ents['meta/banner.bin'], banner_repl)
    if icon_repl: new['meta/icon.bin'] = patch_bin(ents['meta/icon.bin'], icon_repl)
    return bnr[:i] + rebuild_outer(u8, new)
