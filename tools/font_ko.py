"""유럽판 영어 폰트(LANG/ENG/MESS)에 한글을 추가한다.
- 새 글자는 기존 칸 뒤, 새 시트부터 채운다(시트 규격·IA4 형식은 원본 그대로).
- 글자 폭(CWDH)은 하나뿐인 구역을 새 칸까지 늘리고, 글자 → 칸 대응은 기존 scan CMAP(0000~FFFF)에 합친다.
  (nw4r 은 범위가 맞는 첫 CMAP 에서 멈추므로 뒤에 새 CMAP 을 달면 안 읽힌다)
- 모양: 흰 글자 + 검은 1px 테두리(원본 영어 글자와 같은 방식). 자간은 원본처럼 보이는 폭 - 3.
사용: python tools/font_ko.py [글자 파일]   (없으면 KS X 1001 한글 2,350자 전부 + EXTRA 기호)"""
import os
import struct
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brfnt
import paths

FONT = 'C:/Windows/Fonts/malgunbd.ttf'
SRC = paths.EU / 'files/REVOLUTION/LANG/ENG/MESS'
DST = paths.BUILD / 'files/REVOLUTION/LANG/ENG/MESS'
# 폰트 파일 → (글꼴 크기, 한글 아랫선 = 기준선 + 이 값, 기호 자간 = 보이는 폭 + 이 값, 한글 고정 자간)
# 한글은 글자마다 보이는 폭으로 자간을 주면 '판'처럼 넓은 글자가 옆 글자에 붙어 보여서(사용자 지적 9/28)
# 글꼴처럼 모든 한글을 같은 폭으로 둔다. 값은 이전 평균 자간과 같게(A 15.8, B 16.2, B_16 15.1).
SPEC = {
    'FONT_A.BRFNT': (19, 1, -3, 16),
    'FONT_A_21.BRFNT': (19, 1, -3, 16),
    'FONT_B.BRFNT': (17, 1, -1, 16),
    'FONT_B_16.BRFNT': (15, 1, -1, 15),
}


def is_hangul(ch):
    return 0xAC00 <= ord(ch) <= 0xD7A3 or 0x3131 <= ord(ch) <= 0x318E


def ksx1001_hangul():
    out = []
    for hi in range(0xB0, 0xC9):
        for lo in range(0xA1, 0xFF):
            out.append(bytes([hi, lo]).decode('cp949'))
    return out


def render(ch, f, size, drop, adv=-3, fixed=None):
    """칸 크기 LA 이미지와 (left, glyph 폭, 자간)"""
    font = ImageFont.truetype(FONT, size)
    im = Image.new('RGBA', (f.cw, f.ch), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((1, f.base + drop), ch, font=font, fill=(255, 255, 255, 255),
                            anchor='ls', stroke_width=1, stroke_fill=(0, 0, 0, 255))
    r, g, b, a = im.split()
    la = Image.merge('LA', (r, a))
    bb = a.getbbox()
    if bb is None:  # 전각 공백: 한글 한 글자 폭의 빈칸
        return la, (0, 0, size - 2)
    vis = bb[2] - bb[0]
    left = f.widths()[f.charmap()[ord('A')]][0]  # 원본 A 의 left 를 따름
    return la, (left, min(bb[2], f.cw), fixed if fixed and is_hangul(ch) else vis + adv)


def add(name, chars):
    f = brfnt.load(SRC / name)
    size, drop, adv, fixed = SPEC[name]
    cm = f.charmap()
    new = [c for c in chars if ord(c) not in cm]
    start = len(f.sheets) * f.per_sheet
    nsheet = (len(new) + f.per_sheet - 1) // f.per_sheet
    sheets = [Image.new('LA', (f.sw, f.sh), (0, 0)) for _ in range(nsheet)]
    widths = []
    for k, ch in enumerate(new):
        la, w = render(ch, f, size, drop, adv, fixed)
        s, r = divmod(k, f.per_sheet); cy, cx = divmod(r, f.cols)
        sheets[s].paste(la, (cx * (f.cw + 1), cy * (f.ch + 1)))
        widths.append(w)
    f.sheets = list(f.sheets) + [brfnt.ia4_encode(s) for s in sheets]
    a, lst = f.cwdh[-1]
    lst = list(lst) + [(0, 0, 0)] * (start - (a + len(lst))) + widths
    f.cwdh[-1] = [a, lst]
    # scan CMAP 에 합치기(글자 코드 순 정렬)
    for sec in f.cmap:
        if sec[2] == 2:
            n = struct.unpack('>H', sec[4][:2])[0]
            pairs = [struct.unpack('>HH', sec[4][2 + i * 4:6 + i * 4]) for i in range(n)]
            pairs += [(ord(ch), start + k) for k, ch in enumerate(new)]
            pairs.sort()
            sec[4] = struct.pack('>H', len(pairs)) + b''.join(struct.pack('>HH', *p) for p in pairs)
            break
    else:
        raise SystemExit('scan CMAP 없음')
    out = f.build()
    DST.mkdir(parents=True, exist_ok=True)
    open(DST / name, 'wb').write(out)
    # 검증: 다시 읽어 새 글자 대응 확인
    g = brfnt.BRFNT(out); m = g.charmap(); w = g.widths()
    assert all(m[ord(ch)] == start + k for k, ch in enumerate(new))
    assert all(m[c] == v for c, v in cm.items())
    print(f'  {name}: +{len(new)}자, 시트 {len(f.sheets)}장, {os.path.getsize(SRC / name):,} → {len(out):,} 바이트')
    return sheets


EXTRA = '「」『』－＊　♪＋※○＜＞ㄱ⇔'  # 번역문에 쓰였지만 영어 폰트에 없는 기호


def main(charset=None):
    """charset: 넣을 글자를 담은 텍스트 파일(없으면 KS X 1001 한글 2,350자 + EXTRA)"""
    chars = ksx1001_hangul() + list(EXTRA)
    if charset:
        chars = sorted(set(open(charset, encoding='utf-8').read()) - set('\n\r'))
    for name in SPEC:
        add(name, chars)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)
