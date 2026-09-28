"""일본판 원문과 번역을 나란히 담은 대조본을 만든다 → work/text_full/*.json (게임 데이터라 커밋하지 않음)
일본판에서 원문을 다시 뽑고, translation/ko 의 번역(ko)을 같은 위치 키로 합친다.
대조본의 ko 를 고친 뒤 python tools/ko_import.py 로 translation/ko 에 되돌려 넣는다.
원문 구조:
- BMG: 메시지 번호 → 대화창(종류 0001 태그로 넘김) 단위. 대화창마다 화자(종류 000D 태그의 이름)·본문·루비.
- 그 밖(.MESS / GPMESS_DATA.STR / SCRIPT/MEMORY.dat / ITEM/ICOMB.COMB): 0x1A 태그를 포함한 UTF-8 문자열을
  파일 위치(오프셋)와 함께 뽑는다.
태그 구조: 1A, 길이(1A 포함), 그룹(1), 종류(2), 자료. 루비 = 그룹 FF 종류 0002, 자료 = 덮는 글자 수(1) + 읽기."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmg
import paths

JPR = paths.JP / 'files/REVOLUTION'
OUT = paths.WORK / 'text_full'
JP_CHAR = re.compile('[぀-ヿ一-鿿！-～　-〿]')
OTHER = ['MESS/CHARA.MESS', 'MESS/ITEM.MESS', 'MESS/MAIL.MESS', 'MESS/HISTORY.MESS',
         'MESS/PUZZLE_MAIL_003.MESS', 'MESS/PUZZLE_MAIL_056.MESS', 'MESS/PUZZLE_TXT_003.MESS',
         'MESS/PUZZLE_TXT_008.MESS', 'MESS/GPMESS_DATA.STR', 'SCRIPT/MEMORY.dat', 'ITEM/ICOMB.COMB',
         '../../sys/main.dol']  # main.dol: 아이템 획득 문구·장 이름·장소 이름·DAS 화면 등(u32 길이 + 본문)


def tag_info(t):
    """태그 바이트(길이 바이트부터) → (그룹, 종류, 자료)"""
    return t[1], int.from_bytes(t[2:4], 'big'), t[4:]


def split_msg(m):
    """BMG 메시지(문자열 표현) → 대화창 목록"""
    raw = bmg.BMG.encode(m)
    boxes = []; cur = bytearray(); i = 0
    while i < len(raw):
        if raw[i] == 0x1A:
            n = raw[i + 1]; t = raw[i:i + n]
            cur += t; i += n
            g, k, _ = tag_info(t[1:])
            if g == 0 and k == 1:
                boxes.append(bytes(cur)); cur = bytearray()
            continue
        cur.append(raw[i]); i += 1
    if cur: boxes.append(bytes(cur))
    return boxes


def split_lines(raw):
    """태그 안의 0x0A 는 건드리지 않고 줄바꿈으로 나눈다"""
    out = []; cur = bytearray(); i = 0
    while i < len(raw):
        if raw[i] == 0x1A:
            n = raw[i + 1]; cur += raw[i:i + n]; i += n
        elif raw[i] == 0x0A:
            out.append(bytes(cur)); cur = bytearray(); i += 1
        else:
            cur.append(raw[i]); i += 1
    out.append(bytes(cur))
    return out


def box_json(raw):
    lines = []; rubies = []; speakers = []
    for ln in split_lines(raw):
        s, r, sp = plain_all(ln)
        speakers += sp
        s = s.strip('\0')
        if s.strip():
            rubies += [[s[p:p + c], rd] for c, rd, p in r]
            lines.append(s)
    if not lines:
        return None
    d = {'speaker': speakers[0] if speakers else None, 'text': '\n'.join(lines)}
    if rubies: d['ruby'] = rubies
    return d


def plain_all(raw):
    """태그가 섞인 바이트 → (본문, [(덮는 글자 수, 읽기, 본문 안 위치)], 화자 목록)"""
    text = ''; ruby = []; spk = []; i = 0; run = bytearray()
    while i < len(raw):
        if raw[i] == 0x1A:
            text += run.decode('utf-8', 'replace'); run = bytearray()
            n = raw[i + 1]; g, k, data = tag_info(raw[i + 1:i + n]); i += n
            if g == 0xFF and k == 2 and data:
                ruby.append((data[0], data[1:].decode('utf-8', 'replace'), len(text)))
            elif g == 0 and k == 0xD:
                nm = data.lstrip(bytes(range(0x20))).split(b'\0')[0].decode('utf-8', 'replace')
                if nm: spk.append(nm)
            continue
        run.append(raw[i]); i += 1
    text += run.decode('utf-8', 'replace')
    return text, ruby, spk


def export_bmg(p):
    b = bmg.load(p); msgs = []
    for idx, m in enumerate(b.msgs):
        boxes = [x for x in (box_json(r) for r in split_msg(m)) if x]
        if boxes: msgs.append({'id': idx, 'boxes': boxes})
    return {'file': os.path.relpath(p, JPR).replace(os.sep, '/'), 'type': 'bmg', 'count': len(b.msgs), 'messages': msgs}


def valid_text(t):
    """태그가 온전하고, 태그 밖이 제어 문자(줄바꿈·NUL 구분 제외) 없는 UTF-8 인지"""
    i = 0; run = bytearray()
    while i < len(t):
        if t[i] == 0x1A:
            if i + 1 >= len(t) or t[i + 1] < 5 or i + t[i + 1] > len(t): return False
            i += t[i + 1]; continue
        if t[i] < 0x20 and t[i] not in (0x0A, 0x00): return False
        if t[i]: run.append(t[i])
        i += 1
    try:
        bytes(run).decode('utf-8')
    except UnicodeDecodeError:
        return False
    return True


def scan_strings(d):
    """4바이트 길이(빅엔디언) + 본문(끝 NUL) 문자열을 찾는다 → [(본문 시작, 길이)]"""
    out = []; i = 0; n = len(d)
    while i + 4 < n:
        L = int.from_bytes(d[i:i + 4], 'big')
        if 1 <= L <= 0x4000 and i + 4 + L <= n:
            t = d[i + 4:i + 4 + L].rstrip(b'\0')
            if t and valid_text(t) and JP_CHAR.search(plain_all(t)[0]):
                out.append((i + 4, L)); i += 4 + L; continue
        i += 1
    return out


def split_nul(t, base):
    """태그 안의 00 은 건드리지 않고 NUL 로 나눈다 → [(시작 위치, 바이트)]"""
    out = []; st = 0; i = 0
    while i < len(t):
        if t[i] == 0x1A:
            i += t[i + 1]; continue
        if t[i] == 0:
            out.append((base + st, t[st:i])); st = i + 1
        i += 1
    out.append((base + st, t[st:]))
    return [x for x in out if x[1]]


def export_mail(rel):
    """MAIL 계열: 개수 + 레코드 위치 표. 레코드 = 길이 3개(u32) + 문자열 3개(끝 NUL).
    MAIL = 보낸 사람·제목·본문, PUZZLE_MAIL_056 = BGM 이름·곡명·설명."""
    d = open(JPR / rel, 'rb').read(); items = []
    n = int.from_bytes(d[:4], 'big')
    for k in range(n):
        a = int.from_bytes(d[4 + k * 4:8 + k * 4], 'big')
        lens = [int.from_bytes(d[a + i * 4:a + i * 4 + 4], 'big') for i in range(3)]
        o = a + 12
        for part, L in enumerate(lens):
            s, r, _ = plain_all(d[o:o + L].rstrip(b'\0'))
            it = {'offset': o, 'record': k, 'part': part, 'text': s}
            rb = [[s[p:p + c], rd] for c, rd, p in r]
            if rb: it['ruby'] = rb
            items.append(it); o += L
    return {'file': rel, 'type': 'mail', 'strings': items}


def export_other(rel):
    if '_MAIL' in rel or rel.endswith('/MAIL.MESS'):
        return export_mail(rel)
    """길이 한 덩어리(block) 안에 NUL 로 나뉜 문자열이 여럿일 수 있다(MAIL: 제목·보낸 사람·본문 등)"""
    d = open(JPR / rel, 'rb').read(); items = []
    for a, L in scan_strings(d):
        for k, (o, t) in enumerate(split_nul(d[a:a + L], a)):
            s, r, _ = plain_all(t)
            it = {'offset': o, 'block': a - 4, 'part': k, 'text': s}
            rb = [[s[p:p + c], rd] for c, rd, p in r]
            if rb: it['ruby'] = rb
            items.append(it)
    return {'file': rel.replace('../../', ''), 'type': 'strings', 'strings': items}


def key_of(j, m=None, bi=None, s=None):
    if j['type'] == 'bmg': return (m['id'], bi)
    if 'record' in s: return ('r', s['record'], s['part'])
    return ('b', s.get('block', s['offset'] - 4), s.get('part', 0))


def merge_ko(j, name):
    """translation/ko 의 번역을 합친다. 원문 쪽에 없는 번역 항목(추출 때 놓쳐 손으로 더한 것)은 뒤에 붙인다."""
    p = paths.KO / name
    if not p.exists(): return j
    k = json.load(open(p, encoding='utf-8'))
    if j['type'] == 'bmg':
        ko = {(m['id'], bi): b for m in k['messages'] for bi, b in enumerate(m['boxes'])}
        for m in j['messages']:
            for bi, b in enumerate(m['boxes']):
                if (m['id'], bi) in ko: b['ko'] = ko[(m['id'], bi)]['ko']
    else:
        ko = {key_of(k, s=s): s for s in k['strings']}
        have = set()
        for s in j['strings']:
            kk = key_of(j, s=s); have.add(kk)
            if kk in ko: s['ko'] = ko[kk]['ko']
        for kk, s in ko.items():
            if kk not in have: j['strings'].append(dict(s, text=''))
    return j


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    paths.ensure_extracted()
    stats = []
    for p in sorted(JPR / 'MESS' / f for f in os.listdir(JPR / 'MESS') if f.endswith('.BMG')):  # glob 금지: 폴더 이름 [Wii] 대괄호
        j = export_bmg(p)
        nb = sum(len(m['boxes']) for m in j['messages'])
        nc = sum(len(b['text']) for m in j['messages'] for b in m['boxes'])
        stats.append((j['file'], len(j['messages']), nb, nc))
        j = merge_ko(j, os.path.basename(p) + '.json')
        json.dump(j, open(OUT / (os.path.basename(p) + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for rel in OTHER:
        j = export_other(rel)
        nc = sum(len(s['text']) for s in j['strings'])
        stats.append((rel, len(j['strings']), 0, nc))
        j = merge_ko(j, os.path.basename(rel) + '.json')
        json.dump(j, open(OUT / (os.path.basename(rel) + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return stats


if __name__ == '__main__':
    st = main()
    for s in st: print(*s, sep='\t')
    print('합계 글자', sum(s[3] for s in st))
