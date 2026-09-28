"""BRFNT(RFNT 0104) 읽기·쓰기. 구역 순서: FINF, TGLP, CWDH…, CMAP…
포인터(FINF→TGLP/CWDH/CMAP, 각 구역의 다음 포인터)는 파일 절대 위치이며 구역 헤더 8바이트 뒤를 가리킨다."""
import struct


def _al(n, a):
    return n + (-n % a)


class BRFNT:
    def __init__(self, d):
        assert d[:4] == b'RFNT'
        self.head = d[4:8]  # BOM + 버전
        self.nsec_hdr = d[0xC:0x10]
        f = 0x18
        (self.ftype, self.linefeed, self.alt, self.dleft, self.dglyph, self.dchar, self.enc,
         p_tglp, p_cwdh, p_cmap, self.height, self.width, self.ascent, self.fpad) = struct.unpack('>BbHbBbBIIIBBBB', d[f:f + 0x18])
        t = p_tglp
        (self.cw, self.ch, self.base, self.maxw, self.sheet_size, nsheet, self.fmt, self.cols, self.rows,
         self.sw, self.sh, p_sheet) = struct.unpack('>BBbBIHHHHHHI', d[t:t + 0x18])
        self.sheets = [d[p_sheet + i * self.sheet_size:p_sheet + (i + 1) * self.sheet_size] for i in range(nsheet)]
        self.cwdh = []  # [first, [(left, glyphw, charw), …]]
        p = p_cwdh
        while p:
            a, b, nxt = struct.unpack('>HHI', d[p:p + 8])
            self.cwdh.append([a, [struct.unpack('>bBb', d[p + 8 + i * 3:p + 11 + i * 3]) for i in range(b - a + 1)]])
            p = nxt
        self.cmap = []  # [lo, hi, 방식, 자료(bytes)]
        p = p_cmap
        while p:
            lo, hi, typ, pad, nxt = struct.unpack('>HHHHI', d[p:p + 12])
            sz = struct.unpack('>I', d[p - 4:p])[0]
            self.cmap.append([lo, hi, typ, pad, d[p + 12:p - 8 + sz]])
            p = nxt

    # ---- 글자 → 칸 번호 ----
    def charmap(self):
        m = {}
        for lo, hi, typ, _, body in self.cmap:
            if typ == 0:
                base = struct.unpack('>H', body[:2])[0]
                for c in range(lo, hi + 1): m[c] = base + c - lo
            elif typ == 1:
                for c in range(lo, hi + 1):
                    g = struct.unpack('>H', body[(c - lo) * 2:(c - lo) * 2 + 2])[0]
                    if g != 0xFFFF: m[c] = g
            else:
                n = struct.unpack('>H', body[:2])[0]
                for i in range(n):
                    c, g = struct.unpack('>HH', body[2 + i * 4:6 + i * 4]); m[c] = g
        return m

    def widths(self):
        w = {}
        for a, lst in self.cwdh:
            for i, x in enumerate(lst): w[a + i] = x
        return w

    @property
    def per_sheet(self):
        return self.cols * self.rows

    def build(self):
        out = bytearray(0x10)
        # FINF
        finf_pos = 0x10
        out += b'\0' * 0x20
        # TGLP: 시트 자료는 0x20 경계(원본과 같게 TGLP 헤더 바로 뒤, 0x60)
        tglp_pos = len(out)
        sheet_pos = _al(tglp_pos + 0x20, 0x20)
        tglp_end = sheet_pos + self.sheet_size * len(self.sheets)
        tglp = struct.pack('>BBbBIHHHHHHI', self.cw, self.ch, self.base, self.maxw, self.sheet_size, len(self.sheets),
                           self.fmt, self.cols, self.rows, self.sw, self.sh, sheet_pos)
        out += b'TGLP' + struct.pack('>I', tglp_end - tglp_pos) + tglp
        out += b'\0' * (sheet_pos - len(out))
        for s in self.sheets: out += s
        # CWDH
        cw_pos = []
        for i, (a, lst) in enumerate(self.cwdh):
            pos = len(out); cw_pos.append(pos)
            body = struct.pack('>HHI', a, a + len(lst) - 1, 0) + b''.join(struct.pack('>bBb', *x) for x in lst)
            sec = bytearray(b'CWDH' + struct.pack('>I', 0) + body)
            sec += b'\0' * (-len(sec) % 4)
            sec[4:8] = struct.pack('>I', len(sec))
            out += sec
        for i in range(len(cw_pos) - 1):
            out[cw_pos[i] + 12:cw_pos[i] + 16] = struct.pack('>I', cw_pos[i + 1] + 8)
        # CMAP
        cm_pos = []
        for lo, hi, typ, pad, body in self.cmap:
            pos = len(out); cm_pos.append(pos)
            sec = bytearray(b'CMAP' + struct.pack('>I', 0) + struct.pack('>HHHHI', lo, hi, typ, pad, 0) + body)
            sec += b'\0' * (-len(sec) % 4)
            sec[4:8] = struct.pack('>I', len(sec))
            out += sec
        for i in range(len(cm_pos) - 1):
            out[cm_pos[i] + 16:cm_pos[i] + 20] = struct.pack('>I', cm_pos[i + 1] + 8)
        out[finf_pos:finf_pos + 0x20] = b'FINF' + struct.pack('>I', 0x20) + struct.pack(
            '>BbHbBbBIIIBBBB', self.ftype, self.linefeed, self.alt, self.dleft, self.dglyph, self.dchar, self.enc,
            tglp_pos + 8, cw_pos[0] + 8, cm_pos[0] + 8, self.height, self.width, self.ascent, self.fpad)
        out[0:0x10] = b'RFNT' + self.head + struct.pack('>I', len(out)) + self.nsec_hdr
        out[0xE:0x10] = struct.pack('>H', 2 + len(cw_pos) + len(cm_pos))
        return bytes(out)


def load(p):
    return BRFNT(open(p, 'rb').read())


# ---- IA4 시트 ↔ 이미지(8x8 타일, 바이트 상위 4비트 = 알파, 하위 4비트 = 밝기) ----
def ia4_decode(data, w, h):
    from PIL import Image
    im = Image.new('LA', (w, h)); px = im.load(); i = 0
    for ty in range(0, h, 4):
        for tx in range(0, w, 8):
            for y in range(4):
                for x in range(8):
                    b = data[i]; i += 1
                    px[tx + x, ty + y] = ((b & 15) * 17, (b >> 4) * 17)
    return im


def ia4_encode(im):
    im = im.convert('LA'); w, h = im.size; px = im.load(); out = bytearray()
    for ty in range(0, h, 4):
        for tx in range(0, w, 8):
            for y in range(4):
                for x in range(8):
                    l, a = px[tx + x, ty + y]
                    out.append(((a + 8) // 17) << 4 | ((l + 8) // 17))
    return bytes(out)
