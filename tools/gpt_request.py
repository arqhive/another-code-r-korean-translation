"""요청서.md 쓰기(gpt_prepare.py 가 부른다). 분류별 프롬프트 + 번호별 표."""
import json
import os

COMMON = """닌텐도 Wii 게임 「어나더 코드 R 기억의 문」의 그림 글씨를 한국어판으로 바꾸는 작업이야.
네가 만든 PNG를 내가 프로그램으로 줄이고 다시 인코딩해서 게임에 넣을 거라서, 아래 규칙을 반드시 지켜야 해.

[필수 규칙]
1. 결과는 반드시 PNG. JPG 금지.
2. 첨부한 원본과 가로세로 비율을 똑같이 맞춰. 크기는 원본의 2배 이상 크게 만들어.
3. 내가 "투명 배경"이라고 한 그림은 배경을 완전히 투명하게. 흰 배경·체크무늬·단색 배경 금지.
   "검정 바탕 흰 글씨"라고 한 그림은 바탕 전체를 순수한 검정(#000000), 글씨는 순수한 흰색(#FFFFFF)으로만.
   "불투명"이라고 한 그림은 원본의 배경(색·무늬)을 그대로 살려.
   "그림(가장자리 투명)"은 원본 그림(배경 포함)을 그대로 살리고 글자만 바꿔. 투명한 가장자리는 내가 맞춰 줄게.
4. 그림에 없는 것은 그리지 마. 테두리 상자, 받침 판, 배경 장식, 워터마크, 서명 금지.
5. 원본의 디자인을 최대한 따라 해: 서체 종류와 굵기, 글자 색, 외곽선·그림자, 정렬(가운데/왼쪽), 위아래 여백.
6. 한국어 맞춤법과 글자 모양을 정확하게. 받침이 빠지거나 획이 붙거나 깨지면 안 돼.
   다 만든 뒤에 글자를 한 자씩 확인하고, 틀렸으면 다시 만들어.
7. 내가 준 한국어 문구를 그대로 써. 띄어쓰기·문장부호·가운뎃점(·)도 바꾸지 마.
8. 원본에 있는 영어·숫자·기호는 그대로 둬.

이해했으면 "확인"이라고만 답하고, 내가 그림을 보낼 때까지 기다려."""

ONE = """첨부한 첫 번째 그림(원본)을 한국어로 다시 만들어 줘. {bg}, 게임 크기 {w}×{h}(비율 {ratio}).
- 문구: 「{ko}」
- 두 번째 그림은 지금 쓰는 한국어판이야. 문구는 이것과 똑같이, 디자인은 원본 수준으로."""

GROUPS = {
    '01_장소이름': ('장소 이름 띠', '방에 들어갈 때 화면 위에 뜨는 장소 이름이야. 어두운 바탕에 회색 고딕 글씨가 가운데에 한 줄로 있어. '
                  '실제 크기는 높이 30픽셀이라 아주 작아지니, 획이 너무 가늘지 않게 해. 바탕색과 글자 회색 밝기는 원본 그대로.'),
    '02_지도': ('지도 장소 이름', '지도 화면의 장소 이름 라벨이야(검정 바탕 흰 글씨). 원본처럼 굵은 고딕 한 줄. '
               '높이 15~30픽셀로 아주 작게 줄어드니 획을 굵게, 글자 사이를 조금 띄워. 글자가 바탕 칸을 꽉 채우도록.'),
    '03_인물소개': ('인물 소개 카드 이름', '인물 소개 카드의 이름이야. 따옴표(“ ”) 안 현지 이름 줄은 검정 바탕 흰 글씨, '
                  '이름 막대(NAME_john2·kelley)는 어두운 바탕 위 회색 글씨. 원본처럼 가운데 정렬.'),
    '05_DAS_메뉴': ('DAS 메뉴', 'DAS(게임 속 휴대 단말기) 화면의 메뉴 글씨·인물 이름·책 아이콘이야. 흰 글씨 마스크는 원본처럼 '
                   '깔끔한 고딕. 책 아이콘(서장·종장 등)은 투명 배경, 책 그림은 그대로 두고 표지 글자만 바꿔.'),
    '06_타이틀_시스템': ('타이틀·시스템', '게임 오버·타이틀 메뉴 글씨와 리모컨 스트랩 경고 화면이야. 스트랩 화면은 손·리모컨·아이콘·'
                      '「Nintendo」 표시는 그대로 두고 글자만 바꿔. 글자 색(회색·파랑·빨강 강조)과 위치도 원본대로.'),
    '08_3D배경_간판': ('3D 배경 간판', '3D 배경에 붙는 간판·안내판 텍스처야. 판 모양·색·무늬·조명은 그대로, 글자만 바꿔. '
                     '영어·숫자(방 번호 등)는 그대로.'),
    '01_장제목': ('장 제목', '장이 시작할 때 나오는 장 제목이야. 하늘색 바탕에 진회색 굵은 글씨, 흰 테두리. 빛번짐 마스크는 도구가 만드니 '
                '색 그림 한 장만 만들면 돼.'),
    '02_엔딩이름': ('엔딩 이름', '엔딩에서 나오는 인물 이름이야(검정 바탕 흰 글씨). 원본처럼 굵고 좁은 고딕(콘덴스) 한 줄.'),
    '03_오프닝자막': ('오프닝 자막', '오프닝 영상 위에 뜨는 날짜·장소 자막이야(검정 바탕 흰 글씨). 원본처럼 세리프(명조 계열) 한 줄, '
                   '가운데 정렬.'),
    '04_연구소안내판': ('연구소 층 안내판', '연구소 층 안내판 텍스처야. 판 디자인은 그대로, 칸 안 글자만 바꿔. 방 번호·영어 이름 약자는 그대로.'),
    '09_퍼즐_미번역': ('퍼즐 그림(아직 번역 안 됨)', '아직 한국어판이 없는 그림이라 참고 그림이 없어. 아래 표의 한국어 문구로 새로 만들어.'),
}


def _known():
    """번역 JSON의 짧은 한국어 조각(장소·인물 이름 등) — OCR 오독을 고치는 사전"""
    import glob
    import paths
    out = set()
    for f in glob.glob(glob.escape(str(paths.KO)) + '/*.json'):
        j = json.load(open(f, encoding='utf-8'))
        segs = [b['ko'] for m in j.get('messages', []) for b in m['boxes']] + [s['ko'] for s in j.get('strings', [])]
        for s in segs:
            for line in s.replace('\0', '\n').split('\n'):
                line = line.strip()
                if 1 < len(line) <= 24: out.add(line)
    return sorted(out)


def fix_ocr(t, known):
    """OCR 결과를 가장 비슷한 번역문으로 바꾼다(비슷한 게 없으면 그대로) → (문구, 고쳤는지)"""
    import difflib
    if not t: return t, False
    import re
    norm = lambda s: re.sub(r'[^0-9A-Za-z가-힣]', '', s)   # 글자·숫자만 비교(문장부호·공백 무시)
    digits = lambda s: re.sub(r'\D', '', s)
    if t in known: return t, False
    if any(norm(t) in k for k in fix_ocr.joined): return t, False   # 번역문 어딘가에 그대로 있으면 맞게 읽은 것
    # 글자를 잘못 읽은 경우만 고친다: 글자 수가 같고 숫자가 같은 후보 중 아주 비슷한 것
    # (낱말이 붙거나 빠지는 교정, 날짜·숫자 교정, 문장부호만 다른 경우는 고치지 않음)
    cand = [k for k in known if len(norm(k)) == len(norm(t)) and digits(k) == digits(t)]
    if not cand: return t, False
    best = max(cand, key=lambda k: difflib.SequenceMatcher(None, norm(t), norm(k)).ratio())
    if norm(best) == norm(t): return t, False
    r = difflib.SequenceMatcher(None, norm(t), norm(best)).ratio()
    if r < 0.75: return t, False
    # OCR 문자열의 글자 자리만 갈아 끼운다(문장부호·띄어쓰기는 그림에서 읽은 대로)
    rep = iter(norm(best)); out = ''.join(next(rep) if re.match(r'[0-9A-Za-z가-힣]', c) else c for c in t)
    return out, True


def _rel(p):
    return '`' + p.replace('/', '\\') + '`' if p else ''


def write(items, tas, path):
    gpt_dir = os.path.dirname(path)
    ocr = {}
    if os.path.exists(os.path.join(gpt_dir, '_ocr.json')):
        ocr = json.load(open(os.path.join(gpt_dir, '_ocr.json'), encoding='utf-8'))
    known = _known()
    import re
    fix_ocr.joined = [re.sub(r'[^0-9A-Za-z가-힣]', '', k) for k in known]
    n_gpt = sum(1 for i in items if i['kind'] != 'tool')
    o = ['# GPT 그림 재작업 요청서 (어나더 코드 R 한글 패치)\n',
         'GPT(ChatGPT 이미지 생성)에게 그림을 다시 그려 달라고 할 때 쓰는 프롬프트와 번호별 표입니다.',
         f'GPT 대상 **{n_gpt}장**(이미 번역한 그림 + 아직 번역 안 된 퍼즐 그림 7장)을 모두 준비했습니다. **필요한 것만 골라서 맡기면 됩니다.**\n',
         '## 폴더\n', '| 폴더 | 내용 |', '|---|---|',
         '| `work\\GPT\\원본\\` | GPT에 첨부할 원본(일본판, 유럽판 전용 그림은 유럽판). 작은 그림은 픽셀 그대로 키운 `_N배` 판입니다. |',
         '| `work\\GPT\\참고\\` | 지금 패치에 들어간 한글판(`_현재한글판`). 문구를 GPT에게 보여 줄 때 같이 첨부합니다. |',
         '| `work\\GPT\\결과\\` | **GPT가 만든 PNG를 여기에 저장합니다.** 표의 「저장할 이름」을 그대로 써 주세요. |',
         '| `work\\GPT\\비교\\` | 반영하면 원본 \\| 현재 \\| 반영 비교 시트가 생깁니다. |',
         '| `work\\GPT\\목록.json` | 번호 → 에셋 파일·게임 크기·종류(도구용) |\n',
         '결과를 저장한 뒤 `python tools/gpt_import.py`(또는 `python tools/gpt_import.py J01-001 N02`처럼 번호 지정)를 실행하면 '
         '게임 크기·형식에 맞춰 `tools/assets`에 넣고 비교 시트를 만듭니다. 빌드는 따로 합니다.',
         '- 투명 배경 그림은 GPT 그림의 내용 덩어리를 원본 덩어리 자리에 비율 유지로 맞춥니다. 배경이 흰색·단색으로 와도 귀퉁이 색을 지워 받습니다.',
         '- 검정 바탕 흰 글씨 그림은 밝기만 씁니다(색이 섞여 와도 흑백으로 바꿈).',
         '- 장소 이름 띠처럼 `*ap` 마스크 짝이 있는 그림은 새 색 그림에서 마스크를 자동으로 다시 만듭니다(일본판 짝에서 잰 값).',
         '- 「현재 문구」는 현재 한글판을 OCR로 읽은 **초안**입니다. 번역문에 있는 비슷한 문구로 고친 곳은 ✎ 표시가 있습니다. '
         '틀린 글자가 남아 있을 수 있으니 보내기 전에 참고 그림과 맞는지 확인해 주세요.\n',
         '---\n', '## 1. 맨 처음 한 번만 붙여 넣을 공통 규칙\n', '```', COMMON, '```\n', '---\n',
         '## 2. 그림 한 장 요청 틀\n',
         '첨부: 표의 「첨부(원본)」과 「참고(현재)」 두 장. 표의 값으로 `{ }` 칸을 채워 보냅니다.\n',
         '```', ONE, '```\n',
         '같은 분류를 여러 장 맡길 때는 "앞에서 만든 그림과 같은 서체·굵기로"라고 덧붙이면 모양이 통일됩니다.\n',
         '---\n', '## 3. 분류별 표\n']
    order = list(GROUPS)
    groups = {}
    for it in items: groups.setdefault(it['group'], []).append(it)
    for g in sorted(groups, key=lambda g: (order.index(g) if g in order else 99, g)):
        its = groups[g]
        title, desc = GROUPS.get(g, (g, ''))
        tool = [i for i in its if i['kind'] == 'tool']
        o.append(f'### {its[0]["id"][:3]} {title} ({len(its)}장)\n')
        if tool and len(tool) == len(its):
            o.append('대화창 이름표는 `tools/nameplate.py`가 이름(`tools/data/nameplates.json`)으로 직접 그립니다. **GPT 대상이 아닙니다.** '
                     '글꼴·굵기를 바꾸려면 도구 값을 고칩니다.\n')
            continue
        o.append(f'추가로 붙일 말: "{desc}"\n')
        if g.startswith('09_'):
            o.append('| 번호 | 그림 | 원문 | 한국어(번역안) | 게임 크기 | 배경 | 첨부(원본) | 저장할 이름 | 바뀌는 곳 |')
            o.append('|---|---|---|---|---|---|---|---|---|')
            for i in its:
                o.append(f"| {i['id']} | {i['name']} | {i['ja']} | {i['ko'].replace(chr(10), ' / ')} | {i['size'][0]}×{i['size'][1]} | "
                         f"{i['bg']} | {_rel(i['attach'])} | `{i['save_as']}` | {len(i['keys'])}곳(언어별 _UK 등 포함) |")
            o.append('')
            continue
        o.append('| 번호 | 그림 | 게임 크기 | 배경 | 현재 문구(OCR 초안) | 첨부(원본) | 참고(현재) | 저장할 이름 |')
        o.append('|---|---|---|---|---|---|---|---|')
        for i in its:
            raw = ' / '.join(x.strip() for x in ocr.get(i['id'] + '.png', '').split('\n') if x.strip())
            raw = re.sub(r"[\[\]\\|]|'$", '', raw).strip()   # OCR 찌꺼기 기호
            t, fixed = fix_ocr(raw, known)
            i['ko_hint'] = t
            t = (t.replace('|', '｜') + (' ✎' if fixed else '')) if t else '(읽지 못함)'
            o.append(f"| {i['id']} | {i['name']} | {i['size'][0]}×{i['size'][1]} | {i['bg']} | {t} | {_rel(i['attach'])} | "
                     f"{_rel(i.get('ref'))} | `{i['save_as']}` |")
        o.append('')
    o += ['---\n', '## 참고: GPT 없이 도구로 고칠 것\n',
          '### T 기계 이름 TAS → RAS (10장)\n',
          '유럽판 영어 그림이라 기계 이름이 **TAS**로 찍혀 있습니다(대사는 일본판 기준 RAS). 일본판 그림이 영어 RAS판이라 '
          '그대로 가져오면 됩니다. 빌드 도구에 "일본판 그림 그대로 쓰기" 목록을 추가하는 일이라 GPT는 필요 없습니다.\n',
          '| 번호 | 경로 |', '|---|---|']
    o += [f"| {t['id']} | `{t['key']}` |" for t in tas]
    o.append('')
    open(path, 'w', encoding='utf-8').write('\n'.join(o) + '\n')
