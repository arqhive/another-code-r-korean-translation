"""BMG 밖 텍스트(translation/ko/*.json 의 ko)를 유럽판 LANG/ENG 파일에 넣는다 → work/build/files/...
공통 형식: 개수(u32) + 레코드 위치 표(u32 × 개수) + 레코드들. 문자열 = u32 길이 + UTF-8 본문(끝 NUL).
- 일반(CHARA·ITEM·HISTORY·PUZZLE_TXT·GPMESS·ICOMB): 일본판에서 찾은 문자열 위치로 레코드 틀(숫자 4바이트 / 문자열)을
  만들고, 같은 틀로 유럽판 레코드를 읽어 문자열만 한국어로 바꾼다. 틀이 유럽판과 안 맞으면 멈춘다.
- MAIL 계열: 레코드 = 길이 3개 + 문자열 3개(보낸 사람·제목·본문 / BGM 이름·곡명·설명).
- MEMORY.dat: 개수 + (번호, 길이, 질문, 선택지 개수, 선택지(길이+바이트)…) + 끝 개수 두 개.
  유럽판은 끝 개수 두 개(0, 0)가 빠져 있어 파일 뒤를 읽는 약점이 있으므로 0 두 개를 붙인다.
한국어 문자열에는 태그(루비 등)가 없다. 한 덩어리에 NUL 로 나뉜 조각이 여럿이면 조각별 ko 를 NUL 로 잇는다."""
import json
import os
import struct
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export_text as E
import paths

JPR = paths.JP / 'files/REVOLUTION'
EUR = paths.EU / 'files/REVOLUTION/LANG/ENG'
OUT = paths.BUILD / 'files/REVOLUTION/LANG/ENG'
FILES = {  # json 이름 → (일본판 경로, 유럽판 경로, 형식)
    'CHARA.MESS': ('MESS/CHARA.MESS', 'MESS/CHARA.MESS', 'rec'),
    'ITEM.MESS': ('MESS/ITEM.MESS', 'MESS/ITEM.MESS', 'rec'),
    'HISTORY.MESS': ('MESS/HISTORY.MESS', 'MESS/HISTORY.MESS', 'rec'),
    'PUZZLE_TXT_003.MESS': ('MESS/PUZZLE_TXT_003.MESS', 'MESS/PUZZLE_TXT_003.MESS', 'rec'),
    'PUZZLE_TXT_008.MESS': ('MESS/PUZZLE_TXT_008.MESS', 'MESS/PUZZLE_TXT_008.MESS', 'rec'),
    'GPMESS_DATA.STR': ('MESS/GPMESS_DATA.STR', 'MESS/GPMESS_DATA.STR', 'rec'),
    'ICOMB.COMB': ('ITEM/ICOMB.COMB', 'ITEM/ICOMB.COMB', 'rec'),
    'MAIL.MESS': ('MESS/MAIL.MESS', 'MESS/MAIL.MESS', 'mail'),
    'PUZZLE_MAIL_003.MESS': ('MESS/PUZZLE_MAIL_003.MESS', 'MESS/PUZZLE_MAIL_003.MESS', 'mail'),
    'PUZZLE_MAIL_056.MESS': ('MESS/PUZZLE_MAIL_056.MESS', 'MESS/PUZZLE_MAIL_056.MESS', 'mail'),
    'MEMORY.dat': ('SCRIPT/MEMORY.dat', 'SCRIPT/MEMORY.dat', 'memory'),
}
SKIPPED = []
u32 = lambda d, p: struct.unpack('>I', d[p:p + 4])[0]


def ko_blocks(name):
    """일본판 문자열 본문 시작 위치(길이 칸 바로 뒤) → 한국어 바이트(조각은 NUL 로 이음, 끝 NUL 포함)"""
    j = json.load(open(paths.KO / (name + '.json'), encoding='utf-8'))
    parts = defaultdict(dict)
    for s in j['strings']:
        blk = s['block'] + 4 if 'block' in s else s['offset']
        parts[blk][s.get('part', 0)] = s['ko']
    return {b: b'\0'.join(p[k].encode('utf-8') for k in sorted(p)) + b'\0' for b, p in parts.items()}


def table(d):
    n = u32(d, 0)
    return n, [u32(d, 4 + 4 * i) for i in range(n)] + [len(d)]


def is_str(d, p, b):
    """p 에 u32 길이 + 문자열(끝 NUL, 태그 밖에 NUL 없음, 올바른 UTF-8)이 있으면 길이, 아니면 0"""
    if p + 4 > b: return 0
    L = u32(d, p)
    if not (1 <= L <= 0x4000 and p + 4 + L <= b): return 0
    t = d[p + 4:p + 4 + L]
    core = t.rstrip(b'\0')
    if t[-1] != 0 or not core or not E.valid_text(core): return 0
    i = 0
    while i < len(core):  # 태그 밖 NUL 이 있으면 문자열 아님(길이 칸 앞 숫자 오인 방지)
        if core[i] == 0x1A: i += core[i + 1]; continue
        if core[i] == 0: return 0
        i += 1
    return L


def tokens(d, a, b):
    """레코드 [a, b) → [('I', 위치) | ('S', 본문 위치, 길이)]"""
    out = []; p = a
    while p < b:
        L = is_str(d, p, b)
        if L:
            out.append(('S', p + 4, L)); p += 4 + L
        else:
            assert b - p >= 4, ('끝 자투리', p, b)
            out.append(('I', p)); p += 4
    return out


def rebuild(dj, de, ko):
    nj, oj = table(dj); ne, oe = table(de)
    assert nj == ne, ('레코드 수', nj, ne)
    out = bytearray(de[:4 + 4 * ne]); offs = []; n_ko = 0; used = set()
    for r in range(ne):
        tj = tokens(dj, oj[r], oj[r + 1]); te = tokens(de, oe[r], oe[r + 1])
        assert [x[0] for x in tj] == [x[0] for x in te], ('레코드 틀 불일치', r)
        rec = bytearray()
        for fj, fe in zip(tj, te):
            if fe[0] == 'I':
                rec += de[fe[1]:fe[1] + 4]
            else:
                new = ko.get(fj[1], de[fe[1]:fe[1] + fe[2]])
                if fj[1] in ko: n_ko += 1; used.add(fj[1])
                rec += struct.pack('>I', len(new)) + new
        offs.append(len(out)); out += rec
    for r, o in enumerate(offs):
        struct.pack_into('>I', out, 4 + 4 * r, o)
    SKIPPED.extend(sorted(set(ko) - used))  # 추출 때 숫자 칸을 문자열로 잘못 잡은 가짜 항목(실제 문자열은 바로 뒤에 있음)
    return bytes(out), n_ko


def rebuild_mail(de, ko_parts):
    ne, oe = table(de); out = bytearray(de[:4 + 4 * ne]); offs = []; n = 0
    for r in range(ne):
        a = oe[r]; lens = [u32(de, a + 4 * i) for i in range(3)]; p = a + 12; strs = []
        for L in lens:
            strs.append(de[p:p + L]); p += L
        assert p == oe[r + 1], ('메일 레코드', r)
        new = [ko_parts.get((r, k), s) for k, s in enumerate(strs)]; n += sum((r, k) in ko_parts for k in range(3))
        offs.append(len(out)); out += b''.join(struct.pack('>I', len(s)) for s in new) + b''.join(new)
    for r, o in enumerate(offs):
        struct.pack_into('>I', out, 4 + 4 * r, o)
    return bytes(out), n


def rebuild_memory(de, ko_list):
    n = u32(de, 0); p = 4; out = bytearray(de[:4]); k = 0
    for i in range(n):
        a, L = u32(de, p), u32(de, p + 4); q = de[p + 8:p + 8 + L]; p += 8 + L
        new = ko_list[i] if i < len(ko_list) else q; k += i < len(ko_list)
        out += struct.pack('>II', a, len(new)) + new
        c2 = u32(de, p); out += de[p:p + 4]; p += 4
        for _ in range(c2):
            v = u32(de, p); out += de[p:p + 4 + v]; p += 4 + v
    rest = de[p:]
    out += rest if len(rest) >= 8 else rest + b'\0' * (8 - len(rest))  # 빠진 끝 개수 두 개(0, 0) 보충
    return bytes(out), k


def main():
    res = {}
    for name, (jp, eu, kind) in FILES.items():
        dj = open(JPR / jp, 'rb').read(); de = open(EUR / eu, 'rb').read()
        j = json.load(open(paths.KO / (name + '.json'), encoding='utf-8'))
        if kind == 'rec':
            ko = ko_blocks(name)
            SKIPPED.clear(); out, n = rebuild(dj, de, ko)
            if SKIPPED: print(f'  {name}: 추출 때 잘못 잡힌 가짜 항목 {len(SKIPPED)}개 건너뜀(실제 문자열은 따로 들어 있음)')
        elif kind == 'mail':
            out, n = rebuild_mail(de, {(s['record'], s['part']): s['ko'].encode('utf-8') + b'\0' for s in j['strings']})
        else:
            out, n = rebuild_memory(de, [s['ko'].encode('utf-8') + b'\0' for s in sorted(j['strings'], key=lambda s: s['offset'])])
        (OUT / eu).parent.mkdir(parents=True, exist_ok=True)
        open(OUT / eu, 'wb').write(out)
        res[name] = (n, len(de), len(out))
    return res


if __name__ == '__main__':
    for k, v in main().items(): print(k, '넣음', v[0], '크기', v[1], '→', v[2])
