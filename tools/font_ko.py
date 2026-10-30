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

SRC = paths.EU / 'files/REVOLUTION/LANG/ENG/MESS'
DST = paths.BUILD / 'files/REVOLUTION/LANG/ENG/MESS'
# 글꼴(10/11 사용자 결정): 일본판 FONT_A 는 둥근 손글씨풍 → 둘기마요(굵게), FONT_B 는 둥근 고딕 → G마켓 산스 Bold(처음엔 나눔고딕).
# 저장소 tools/fonts 에 있으면 그것, 없으면 사용자 글꼴 폴더. 글꼴에 없는 기호는 맑은 고딕 Bold 로 채운다.
FONT_DIR = paths.TOOLS / 'fonts'
USER_FONTS = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft/Windows/Fonts')
FALLBACK = 'C:/Windows/Fonts/malgunbd.ttf'


def font_file(name):
    for d in (FONT_DIR, USER_FONTS, 'C:/Windows/Fonts'):
        p = os.path.join(d, name)
        if os.path.exists(p): return p
    raise SystemExit(f'글꼴 {name} 이 없습니다. tools/fonts 나 Windows 글꼴로 설치하세요.')


# 폰트 파일 → (글꼴, 글꼴 크기, 한글 아랫선 = 기준선 + 이 값, 기호 자간 = 보이는 폭 + 이 값, 한글 고정 자간)
# 한글은 글자마다 보이는 폭으로 자간을 주면 '판'처럼 넓은 글자가 옆 글자에 붙어 보여서(사용자 지적 9/28)
# 글꼴처럼 모든 한글을 같은 폭으로 둔다. 크기는 한글 높이를 이전 맑은 고딕(19·17·15)과 비슷하게 맞춤.
SPEC = {
    # 대사창(FONT_A)·아이템 창(FONT_B)은 10/11 폭 시험판에서 잰 한계 안에서 키움(사용자 요청):
    #   대사창 한계(▼ 앞) ≈ 555, 가장 넓은 줄 442 → 자간 19 로 494 / 아이템 창 한계(스크롤바 앞) ≈ 245, 206 → 자간 17 로 219
    #   (한계는 자간 17·16 일 때 폰트 단위. 대사창은 3줄, 아이템 창은 7줄까지 보임)
    #   단 둘기마요는 손글씨라 글자 높이 범위가 커서 칸(23×27)에 여백까지 들어가는 최대가 20(21=27행·22=28행은 잘림)
    'FONT_A.BRFNT': ('dovemayo_bold.otf', 20, 1, -3, 18),
    'FONT_A_21.BRFNT': ('dovemayo_bold.otf', 20, 1, -3, 17),   # 쓰이는 곳 미확인 — 그대로
    # FONT_B 계열은 G마켓 산스 Bold(10/11 사용자 요청, 나눔고딕에서 바꿈). 글자가 넓어 18은 400여 자가 칸(21폭) 끝에 닿아 17
    'FONT_B.BRFNT': ('GmarketSansBold.otf', 17, 1, -1, 17),
    'FONT_B_16.BRFNT': ('GmarketSansBold.otf', 14, 1, -1, 15),
}
# 둘기마요의 낫표는 칸 위쪽에 붙어 옆 글자와 겹쳐 보여서(『기억 → 「키억」처럼) 맑은 고딕으로 그린다(10/11 비교)
USE_FALLBACK = {'dovemayo_bold.otf': set('「」『』'), 'dovemayo.otf': set('「」『』')}
_cmaps = {}


def has_glyph(path, ch):
    if ch in USE_FALLBACK.get(os.path.basename(path), ()): return False
    if path not in _cmaps:
        from fontTools.ttLib import TTFont
        _cmaps[path] = set(TTFont(path, fontNumber=0).getBestCmap())
    return ord(ch) in _cmaps[path]


def is_hangul(ch):
    return 0xAC00 <= ord(ch) <= 0xD7A3 or 0x3131 <= ord(ch) <= 0x318E


def ksx1001_hangul():
    out = []
    for hi in range(0xB0, 0xC9):
        for lo in range(0xA1, 0xFF):
            out.append(bytes([hi, lo]).decode('cp949'))
    return out


# 칸 안 여백: 글자가 칸 끝에 닿으면 게임이 칸을 늘이고 줄일 때 끝 픽셀이 잘리거나 옆 칸과 섞여
# 앞뒤가 깎이고 위아래가 어긋나 보인다(10/11 FONT_B 17px 사용자 제보). 왼쪽 2px 안쪽에 그리고 left 로 위치를 되돌린다.
PAD_X = 2
PAD_Y = 2   # 아래 여백: 가장 아래로 내려가는 한글이 칸 밑에서 이만큼 떨어지게 기준선을 올린다


def render(ch, f, size, drop, adv=-3, fixed=None, path=FALLBACK):
    """칸 크기 LA 이미지와 (left, glyph 폭, 자간)"""
    font = ImageFont.truetype(path if has_glyph(path, ch) else FALLBACK, size)
    shift = PAD_X
    lb, _, rb, _ = font.getbbox(ch, anchor='ls', stroke_width=1)
    if shift + rb > f.cw - 1: shift = f.cw - 1 - rb   # 넓은 글자는 오른쪽 여백이 남도록 덜 민다
    if shift + lb < 1: shift = 1 - lb                 # 왼쪽으로 크게 삐져나오는 글자(둘기마요 「다」 등)는 더 안쪽에
    y = f.base + drop
    if is_hangul(ch) and OPTICAL.get(os.path.basename(path)):
        # 받침 없이 가로 모음으로 끝나는 글자(요·효·교 등)는 기준선에서 끝나 작은 크기에서 떠 보임 → 조금 내림
        if font.getbbox(ch, anchor='ls')[3] <= OPTICAL[os.path.basename(path)][0]:
            y += OPTICAL[os.path.basename(path)][1]
    im = Image.new('RGBA', (f.cw, f.ch), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((shift, y), ch, font=font, fill=(255, 255, 255, 255),
                            anchor='ls', stroke_width=1, stroke_fill=(0, 0, 0, 255))
    r, g, b, a = im.split()
    la = Image.merge('LA', (r, a))
    bb = a.getbbox()
    if bb is None:  # 전각 공백: 한글 한 글자 폭의 빈칸
        return la, (0, 0, size - 2)
    if bb[2] >= f.cw: CLIPPED.append(ch)
    vis = bb[2] - bb[0]
    if not hasattr(f, 'a_left'): f.a_left = f.widths()[f.charmap()[ord('A')]][0]   # A 를 다시 그리기 전 원본 값
    left = f.a_left - (shift - 1)  # 원본 A 의 left 를 따르되, 안쪽으로 민 만큼 되돌림
    return la, (left, min(bb[2] + 1, f.cw), fixed if fixed and is_hangul(ch) else vis + adv)


def squeeze(ch, f, size, drop, adv, path):
    """칸보다 넓은 글자를 원래 크기로 그린 뒤 가로만 칸에 맞게 줄인다(높이·기준선은 그대로)"""
    font = ImageFont.truetype(path if has_glyph(path, ch) else FALLBACK, size)
    big = Image.new('RGBA', (f.cw * 3, f.ch), (0, 0, 0, 0))
    ImageDraw.Draw(big).text((f.cw, f.base + drop), ch, font=font, fill=(255, 255, 255, 255),
                             anchor='ls', stroke_width=1, stroke_fill=(0, 0, 0, 255))
    bb = big.split()[3].getbbox()
    ink = big.crop((bb[0], 0, bb[2], f.ch))
    tw = min(ink.width, f.cw - 2)
    ink = ink.resize((tw, f.ch), Image.LANCZOS)
    im = Image.new('RGBA', (f.cw, f.ch), (0, 0, 0, 0)); im.alpha_composite(ink, (1, 0))
    r, g, b, a = im.split()
    if not hasattr(f, 'a_left'): f.a_left = f.widths()[f.charmap()[ord('A')]][0]
    return Image.merge('LA', (r, a)), (f.a_left, tw + 1, tw + adv)


CLIPPED = []
# 글꼴 →(아래 끝이 기준선 + 이 값 이하인 한글이면, 이만큼 내림). 사용자 지적 10/11 「요가 떠 보임」(나눔고딕)
OPTICAL = {'NanumGothic-Bold.ttf': (1, 1)}


def fit_drop(f, size, drop, path, chars):
    """가장 아래로 내려가는 한글이 칸 밑에서 PAD_Y 이상 떨어지도록 drop 을 줄인다(위로도 1px 여백 확인)"""
    font = ImageFont.truetype(path, size)
    while True:
        lo, hi = f.ch, 0
        for ch in chars:
            bb = font.getbbox(ch, anchor='ls', stroke_width=1)
            lo = min(lo, f.base + drop + bb[1]); hi = max(hi, f.base + drop + bb[3])
        if hi <= f.ch - PAD_Y or lo <= 1: return drop, lo, hi
        drop -= 1


def add(name, chars):
    f = brfnt.load(SRC / name)
    fname, size, drop, adv, fixed = SPEC[name]
    path = font_file(fname)
    cm = f.charmap()
    new = [c for c in chars if ord(c) not in cm]
    drop, top, bottom = fit_drop(f, size, drop, path, [c for c in new if is_hangul(c)])
    CLIPPED.clear()
    start = len(f.sheets) * f.per_sheet
    nsheet = (len(new) + f.per_sheet - 1) // f.per_sheet
    sheets = [Image.new('LA', (f.sw, f.sh), (0, 0)) for _ in range(nsheet)]
    widths = []
    for k, ch in enumerate(new):
        la, w = render(ch, f, size, drop, adv, fixed, path)
        s, r = divmod(k, f.per_sheet); cy, cx = divmod(r, f.cols)
        sheets[s].paste(la, (cx * (f.cw + 1), cy * (f.ch + 1)))
        widths.append(w)
    # 원본에 있던 영문·숫자·기호(REDRAW)는 칸 번호를 그대로 두고 그 칸에 새 글꼴로 덮어 그린다.
    # (0x20~0x7E·0xA0~0xFF 는 칸 번호가 이어지는 direct CMAP 이라 글자 하나만 새 칸으로 돌릴 수 없음)
    redraw = [c for c in REDRAW if ord(c) in cm]
    decoded = {}
    for ch in redraw:
        g = cm[ord(ch)]; s, r = divmod(g, f.per_sheet); cy, cx = divmod(r, f.cols)
        if s not in decoded: decoded[s] = brfnt.ia4_decode(f.sheets[s], f.sw, f.sh)
        sz = size
        n0 = len(CLIPPED); la, w = render(ch, f, sz, drop, adv, fixed, path)
        if len(CLIPPED) > n0:   # 넓은 글자(W 등): 크기를 줄이면 높이가 낮아져 소문자처럼 보여서(10/30 「Wii」 제보) 가로만 좁힌다
            del CLIPPED[n0:]
            la, w = squeeze(ch, f, sz, drop, adv, path)
        # 「보이는 폭 + adv」는 I·1·l 같은 얇은 글자에서 0에 가까워져 다음 글자에 덮인다(10/30 비교) → 글꼴 본래 간격 이상으로
        nat = round(ImageFont.truetype(path if has_glyph(path, ch) else FALLBACK, sz).getlength(ch))
        w = (w[0], w[1], max(w[2], nat - 2) + REDRAW_EXTRA.get(fname, 0))
        x0, y0 = cx * (f.cw + 1), cy * (f.ch + 1)
        # 칸 오른쪽·아래 1px 틈까지 지운다(원본 「[」「]」 등은 틈까지 그려져 있어 새 글자 밑에 선으로 남았음, 10/30 제보)
        decoded[s].paste(Image.new('LA', (f.cw + 1, f.ch + 1), (0, 0)), (x0, y0))
        decoded[s].paste(la, (x0, y0))
        for sec in f.cwdh:
            if sec[0] <= g < sec[0] + len(sec[1]): sec[1][g - sec[0]] = w
    f.sheets = [brfnt.ia4_encode(decoded[i]) if i in decoded else sh for i, sh in enumerate(f.sheets)]
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
    print(f'  {name}: +{len(new)}자, 시트 {len(f.sheets)}장, {os.path.getsize(SRC / name):,} → {len(out):,} 바이트'
          f' (한글 세로 {top}~{bottom - 1} / 칸 {f.ch}, drop {drop}, 오른쪽 끝에 닿는 글자 {len(CLIPPED)}개 {"".join(CLIPPED[:10])})')
    return sheets


EXTRA = '「」『』－＊　♪＋※○＜＞ㄱ⇔'  # 번역문에 쓰였지만 영어 폰트에 없는 기호
# 원본 영어 글자를 한글과 같은 글꼴로 다시 그릴 글자(10/30 사용자 요청). 공백은 원래 폭 그대로 둔다(사용자 결정).
REDRAW = ''.join(chr(c) for c in range(0x21, 0x7F)) + '…·×'
# 다시 그린 영문의 간격 추가: 둘기마요는 「보이는 폭 − 3」이면 「DAS의」처럼 뒤 한글에 붙어 보여서(10/30 제보) 2px 넓힘
REDRAW_EXTRA = {'dovemayo_bold.otf': 2}


def cache_key(name, chars):
    """폰트 결과가 달라질 수 있는 입력 전부(이 파일·brfnt.py 소스, 글꼴 파일, 원본 폰트, 글자 목록, 설정)"""
    import hashlib
    h = hashlib.sha1()
    for p in (__file__, brfnt.__file__, font_file(SPEC[name][0]), FALLBACK, SRC / name):
        h.update(open(p, 'rb').read())
    h.update(repr((SPEC[name], ''.join(chars))).encode())
    return h.hexdigest()[:16]


def main(charset=None):
    """charset: 넣을 글자를 담은 텍스트 파일(없으면 KS X 1001 한글 2,350자 + EXTRA)
    결과는 work/cache/font 에 두고 입력이 같으면 다시 그리지 않는다(빌드 시간 단축)."""
    import shutil
    chars = ksx1001_hangul() + list(EXTRA)
    if charset:
        chars = sorted(set(open(charset, encoding='utf-8').read()) - set('\n\r'))
    cdir = paths.WORK / 'cache' / 'font'; cdir.mkdir(parents=True, exist_ok=True)
    for name in SPEC:
        c = cdir / f'{name}.{cache_key(name, chars)}'
        if c.exists():
            DST.mkdir(parents=True, exist_ok=True); shutil.copyfile(c, DST / name)
            print(f'  {name}: 캐시 사용(입력 같음)')
            continue
        add(name, chars)
        shutil.copyfile(DST / name, c)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)
