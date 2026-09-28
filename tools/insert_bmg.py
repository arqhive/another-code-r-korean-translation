"""translation/ko/*.BMG.json 의 ko 를 유럽판 LANG/ENG/MESS/*.BMG 에 넣는다 → work/build/files/.../*.BMG
메시지마다:
- 유럽판 대화창 수·화자 순서가 일본판과 같으면 유럽판 구조를 쓰고 창마다 한국어를 넣는다.
- 다르면 일본판 메시지 구조(루비 태그 제거)를 가져와 넣는다(같은 엔진이라 태그 호환).
- 유럽판 메시지가 비어 있으면(미사용 더미) 건드리지 않는다.
창 안에서는 글이 있는 줄(태그 밖 줄바꿈으로 나눈 줄) 순서대로 한국어 줄을 넣는다. 첫 글 조각에 한 줄을 통째로
넣고 나머지 글 조각은 비운다. 한국어 줄이 더 많으면 마지막 글 줄(태그 포함)을 복제해 늘린다.
화자 태그(종류 000D)는 게임 내부 키라서 그대로 둔다."""
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmg
import export_text as E
import paths

TAG = re.compile(r'(\{1A:[0-9A-F]*\})')
SRC = paths.EU / 'files/REVOLUTION/LANG/ENG/MESS'
JPS = paths.JP / 'files/REVOLUTION/MESS'
OUT = paths.BUILD / 'files/REVOLUTION/LANG/ENG/MESS'


def tag_bytes(t):
    return bytes.fromhex(t[4:-1])


def is_ruby(t):
    b = tag_bytes(t); return b[1] == 0xFF and b[2:4] == b'\x00\x02'


def is_break(t):
    b = tag_bytes(t); return b[1] == 0 and b[2:4] == b'\x00\x01'


def speaker(t):
    b = tag_bytes(t)
    if b[1] == 0 and b[2:4] == b'\x00\x0d':
        return b[4:].lstrip(bytes(range(0x20))).split(b'\0')[0].decode('utf-8', 'replace')


def tokens(s):
    """문자열 → [태그 | '\\n' | 글]"""
    out = []
    for p in TAG.split(s):
        if not p: continue
        if TAG.fullmatch(p): out.append(p); continue
        parts = p.split('\n')
        for i, q in enumerate(parts):
            if i: out.append('\n')
            if q: out.append(q)
    return out


def boxes(toks):
    """토큰 → 대화창(넘김 태그까지 포함) 목록"""
    out = []; cur = []
    for t in toks:
        cur.append(t)
        if TAG.fullmatch(t) and is_break(t):
            out.append(cur); cur = []
    if cur: out.append(cur)
    return out


def has_text(toks):
    return any(not TAG.fullmatch(t) and t != '\n' and t.strip() for t in toks)


def text_boxes(bx):
    return [b for b in bx if has_text(b)]


def box_speaker(b):
    for t in b:
        if TAG.fullmatch(t):
            s = speaker(t)
            if s: return s


def fill_box(b, ko_lines):
    """대화창 토큰에 한국어 줄들을 넣는다"""
    lines = [[]]
    for t in b:
        if t == '\n': lines.append([])
        else: lines[-1].append(t)
    idx = [i for i, ln in enumerate(lines) if has_text(ln)]
    # 한국어 줄이 더 많으면 마지막 글 줄을 복제
    while len(idx) < len(ko_lines):
        last = idx[-1]; lines.insert(last + 1, list(lines[last])); idx.append(last + 1)
    for n, i in enumerate(idx):
        ln = lines[i]
        txt = [k for k, t in enumerate(ln) if not TAG.fullmatch(t)]
        head = next(k for k in txt if ln[k].strip())
        for k in txt:
            ln[k] = (ko_lines[n] if n < len(ko_lines) else '') if k == head else ''
    return [t for ln in lines for t in ln + ['\n']][:-1]


def strip_ruby(toks):
    return [t for t in toks if not (TAG.fullmatch(t) and is_ruby(t))]


def build_msg(eu_msg, jp_msg, ko_boxes, stats):
    eb = boxes(tokens(eu_msg))
    etb = text_boxes(eb)
    if not etb:
        stats['유럽판 빈 메시지(유지)'] += 1
        return eu_msg
    same = len(etb) == len(ko_boxes) and all(box_speaker(b) == k['speaker'] for b, k in zip(etb, ko_boxes))
    if same:
        base = eb; stats['유럽판 구조'] += 1
    else:
        base = boxes(strip_ruby(tokens(jp_msg))); stats['일본판 구조'] += 1
    tb = [i for i, b in enumerate(base) if has_text(b)]
    assert len(tb) == len(ko_boxes), (len(tb), len(ko_boxes))
    for i, k in zip(tb, ko_boxes):
        base[i] = fill_box(base[i], k['ko'].split('\n'))
    return ''.join(t for b in base for t in b)


def main(only=None):
    stats = Counter(); OUT.mkdir(parents=True, exist_ok=True)
    for fn in sorted(os.listdir(paths.KO)):
        if not fn.endswith('.BMG.json'): continue
        name = fn[:-5]
        if only and name not in only: continue
        if not (SRC / name).exists():
            stats['유럽판에 파일 없음'] += 1; continue
        j = json.load(open(paths.KO / fn, encoding='utf-8'))
        eb = bmg.load(SRC / name); jb = bmg.load(JPS / name)
        msgs = list(eb.msgs)
        for m in j['messages']:
            msgs[m['id']] = build_msg(eb.msgs[m['id']], jb.msgs[m['id']], m['boxes'], stats)
        out = eb.build(msgs)
        assert bmg.BMG(out).msgs == msgs
        open(OUT / name, 'wb').write(out)
    return stats


if __name__ == '__main__':
    print(main(sys.argv[1:] or None))
