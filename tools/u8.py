"""U8 묶음(55AA382D, 무압축) 읽기·쓰기.
노드 12바이트: 종류(1) 이름 오프셋(3) + 파일: 자료 위치·크기 / 폴더: 부모 번호·끝 번호.
entries 는 원본 순서의 [종류, 이름, 자료 또는 (부모, 끝)] 목록. 파일 자료만 바꿔 다시 쓴다."""
import struct


def _al(n, a=0x20):
    return n + (-n % a)


class U8:
    def __init__(self, d):
        assert d[:4] == b'\x55\xAA\x38\x2D'
        root, hsize, dstart = struct.unpack('>III', d[4:16])
        self.pad10 = d[16:32]
        n = struct.unpack('>I', d[root + 8:root + 12])[0]
        st = root + n * 12
        self.entries = []
        self.orig_pos = {}  # 파일 노드 번호 → 원본 (위치, 크기). 앞쪽이 안 바뀌었으면 원본 위치를 그대로 쓴다
        self.dstart = dstart; self.orig_len = len(d)
        self.names_raw = d[st:root + hsize]
        for i in range(n):
            t, no, a, b = struct.unpack('>BxHII', d[root + i * 12:root + i * 12 + 12])
            no |= d[root + i * 12 + 1] << 16
            nm = d[st + no:d.index(b'\0', st + no)].decode('ascii')
            self.entries.append([t, nm, (a, b) if t else d[a:a + b], no])
            if not t: self.orig_pos[i] = (a, b)
        self.gap = d[root + hsize:dstart]
        last = max([struct.unpack('>I', d[root + i * 12 + 4:root + i * 12 + 8])[0] + struct.unpack('>I', d[root + i * 12 + 8:root + i * 12 + 12])[0]
                    for i in range(n) if not d[root + i * 12]] or [dstart])
        self.endpad = len(d) > last  # 원본이 끝을 0x20 경계까지 채웠는지

    def files(self):
        """{경로: 자료}"""
        out = {}; stack = []
        for i, (t, nm, v, _) in enumerate(self.entries):
            while stack and i >= stack[-1][1]: stack.pop()
            if t:
                if i: stack.append((nm, v[1]))
            else:
                out['/'.join([s for s, _ in stack] + [nm])] = v
        return out

    def replace(self, path, data):
        stack = []
        for i, e in enumerate(self.entries):
            while stack and i >= stack[-1][1]: stack.pop()
            if e[0]:
                if i: stack.append((e[1], e[2][1]))
            elif '/'.join([s for s, _ in stack] + [e[1]]) == path:
                e[2] = data; return
        raise KeyError(path)

    def build(self):
        root = 0x20
        hsize = len(self.entries) * 12 + len(self.names_raw)
        dstart = self.dstart
        out = bytearray(dstart); pos = dstart; blobs = []
        nodes = bytearray(); same = True
        for i, (t, nm, v, no) in enumerate(self.entries):
            if t:
                a, b = v
            else:
                oa, ob = self.orig_pos[i]
                pos = oa if same and oa >= pos else _al(pos)
                same = same and pos == oa and len(v) == ob
                a, b = pos, len(v); blobs.append((pos, v)); pos += len(v)
            nodes += struct.pack('>I', (t << 24) | no) + struct.pack('>II', a, b)
        out[0:32] = b'\x55\xAA\x38\x2D' + struct.pack('>III', root, hsize, dstart) + self.pad10
        out[root:root + hsize] = nodes + self.names_raw
        out[root + hsize:root + hsize + len(self.gap)] = self.gap
        out += b'\0' * (pos - len(out))
        for p, v in blobs: out[p:p + len(v)] = v
        if self.endpad: out += b'\0' * (_al(len(out)) - len(out))
        if not blobs: out = out[:self.orig_len]  # 빈 묶음(R010 등)은 자료 시작 전에 끝남
        return bytes(out)


def load(p):
    return U8(open(p, 'rb').read())


def from_files(files, pad10=b'\0' * 16):
    """{경로: 자료} (순서 유지) → 새 U8 바이트. 폴더는 경로에서 만든다. 자료는 0x20 경계."""
    tree = {}
    for p, v in files.items():
        node = tree; parts = p.split('/')
        for d in parts[:-1]:
            node = node.setdefault(d, {})
        node[parts[-1]] = v
    ents = [[1, '', 0, 0]]; names = bytearray(b'\0')

    def walk(node, parent):
        for nm, v in node.items():
            no = len(names); names.extend(nm.encode('ascii') + b'\0')
            if isinstance(v, dict):
                i = len(ents); ents.append([1, nm, parent, 0, no]); walk(v, i); ents[i][3] = len(ents)
            else:
                ents.append([0, nm, v, 0, no])
    walk(tree, 0); ents[0][3] = len(ents)
    root = 0x20; hsize = len(ents) * 12 + len(names); dstart = _al(root + hsize)
    out = bytearray(dstart); nodes = bytearray(); pos = dstart; blobs = []
    for e in ents:
        no = e[4] if len(e) > 4 else 0
        if e[0]:
            a, b = e[2], e[3]
        else:
            pos = _al(pos); a, b = pos, len(e[2]); blobs.append((pos, e[2])); pos += len(e[2])
        nodes += struct.pack('>III', (e[0] << 24) | no, a, b)
    out[0:32] = b'\x55\xAA\x38\x2D' + struct.pack('>III', root, hsize, dstart) + pad10
    out[root:root + hsize] = nodes + names
    out += b'\0' * (pos - len(out))
    for p, v in blobs: out[p:p + len(v)] = v
    out += b'\0' * (_al(len(out)) - len(out))
    return bytes(out)
