"""어나더 코드 R BMG(MESGbmg1, UTF-8) 읽기·쓰기.
구조: 헤더 0x20 + INF1(항목 8바이트: DAT1 안 오프셋 4 + 속성 4) + DAT1(0으로 끝나는 UTF-8 문자열).
태그는 0x1A, 다음 바이트가 태그 전체 길이(0x1A 포함).
메시지는 태그를 {1A:xx..} 형태의 글자로 바꾼 문자열로 다룬다."""
import re
import struct

TAG_RE = re.compile(r'\{1A:([0-9A-F]*)\}')


def _pad(b, n=0x20):
    return b + b'\0' * (-len(b) % n)


class BMG:
    def __init__(self, data):
        assert data[:8] == b'MESGbmg1', '어나더 코드 R BMG가 아님'
        self.hdr = bytearray(data[:0x20])
        nsec = struct.unpack('>I', data[0xC:0x10])[0]
        self.secs = []  # [(magic, body)]  INF1·DAT1 외 구역은 그대로 보존
        o = 0x20
        for _ in range(nsec):
            mg = data[o:o + 4]; sz = struct.unpack('>I', data[o + 4:o + 8])[0]
            self.secs.append([mg, data[o + 8:o + sz]])
            o += sz
        self.tail = data[o:]
        inf = self._sec(b'INF1'); dat = self._sec(b'DAT1')
        n, self.esize = struct.unpack('>HH', inf[:4])
        self.inf_extra = inf[4:8]
        self.entries = []  # [(오프셋, 속성 바이트)]
        for i in range(n):
            e = inf[8 + i * self.esize:8 + (i + 1) * self.esize]
            self.entries.append((struct.unpack('>I', e[:4])[0], e[4:]))
        self.inf_pad = inf[8 + n * self.esize:]
        self.dat = dat
        self.msgs = [self._decode(off) for off, _ in self.entries]

    def _sec(self, mg):
        return next(b for m, b in self.secs if m == mg)

    def _raw(self, off):
        d = self.dat; i = off; out = bytearray()
        while d[i] != 0:
            if d[i] == 0x1A:
                n = d[i + 1]; out += d[i:i + n]; i += n
            else:
                out.append(d[i]); i += 1
        return bytes(out)

    def _decode(self, off):
        raw = self._raw(off); s = []; i = 0; run = bytearray()
        while i < len(raw):
            if raw[i] == 0x1A:
                if run: s.append(run.decode('utf-8')); run = bytearray()
                n = raw[i + 1]; s.append('{1A:%s}' % raw[i + 1:i + n].hex().upper()); i += n
            else:
                run.append(raw[i]); i += 1
        if run: s.append(run.decode('utf-8'))
        return ''.join(s)

    @staticmethod
    def encode(s):
        out = bytearray(); p = 0
        for m in TAG_RE.finditer(s):
            out += s[p:m.start()].encode('utf-8'); out += b'\x1A' + bytes.fromhex(m.group(1)); p = m.end()
        out += s[p:].encode('utf-8')
        return bytes(out)

    def build(self, msgs=None, keep_layout=False):
        """msgs가 원본과 같고 keep_layout=True면 원본 DAT1을 그대로 쓴다(왕복 확인용).
        아니면 DAT1을 새로 짠다: 같은 문자열은 한 번만 넣고 원본처럼 오프셋 0 은 빈 문자열."""
        msgs = self.msgs if msgs is None else msgs
        if keep_layout and msgs == self.msgs:
            dat = self.dat; offs = [o for o, _ in self.entries]
        else:
            dat = bytearray(b'\0'); seen = {'': 0}; offs = []
            for m in msgs:
                if m not in seen:
                    seen[m] = len(dat); dat += self.encode(m) + b'\0'
                offs.append(seen[m])
            dat = bytes(dat)
        inf = struct.pack('>HH', len(msgs), self.esize) + self.inf_extra
        for (o, attr) in zip(offs, [a for _, a in self.entries]):
            inf += struct.pack('>I', o) + attr
        inf = inf + (self.inf_pad if keep_layout else b'')
        out = bytearray(self.hdr)
        for mg, body in self.secs:
            if mg == b'INF1': body = inf
            elif mg == b'DAT1': body = dat
            sec = _pad(mg + b'\0\0\0\0' + body)
            sec = sec[:4] + struct.pack('>I', len(sec)) + sec[8:]
            out += sec
        out += self.tail
        out[8:12] = struct.pack('>I', len(out))
        return bytes(out)


def load(path):
    return BMG(open(path, 'rb').read())
