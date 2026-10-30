# 장소 이름 띠 그리기 (python tools/place_names_draw.py 는 모듈: draw(문구) → (색 그림, 투명도)) — 문구는 tools/data/place_names.json
# - 투명도: 8배로 그려 면적 평균(BOX)으로 줄임(힌팅 없음 → 삐침 없음)
# - 글자마다 가로 위치를 1/4px 단위로, 줄 전체 세로 위치도 1/4px 단위로 골라 반투명 픽셀이 가장 적게(획이 픽셀 경계에 맞게)
# - 색 그림: 줄마다 고른 글자색(일본판 실측 세로 밝기)만, 가장자리 어둡게 처리 없음
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

W, H, SS = 420, 30, 8
TOP, BOT = 4, 26
BG = (10, 10, 29)
FP = 'C:/Windows/Fonts/NotoSansKR-VF.ttf'
YK = [4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26]
GK = [248, 250, 238, 238, 218, 213, 193, 193, 172, 168, 160, 152]


def font(size, wt):
    f = ImageFont.truetype(FP, size); f.set_variation_by_axes([wt]); return f


def fit(wt):
    for s in range(100, 400):
        f = font(s, wt); b = f.getbbox('한')
        if b[3] - b[1] >= (BOT - TOP + 1) * SS: return f, b


def blur_score(a):
    return float(np.minimum(a, 1 - a).sum())   # 반투명일수록 큼


def glyph(ch, f, ref, dx, dy):
    w = int(f.getlength(ch)) + 4 * SS
    m = Image.new('L', (w, H * SS), 0); ImageDraw.Draw(m).text((2 * SS + dx, TOP * SS - ref[1] + dy), ch, font=f, fill=255)
    return m


def coverage(text, wt=400, cx=210, faint=0):
    f, ref = fit(wt)
    total = f.getlength(text)
    x0 = cx * SS - total / 2
    best_dy = None
    for dy in (0, 2, 4, 6):                      # 1/4px 단위
        big = Image.new('L', (W * SS, H * SS), 0)
        for i, ch in enumerate(text):
            if ch == ' ': continue
            px = x0 + f.getlength(text[:i])
            base = int(px // SS) * SS
            best = None
            for dx in (0, 2, 4, 6):
                g = glyph(ch, f, ref, (px - base) + dx, dy)
                a = np.asarray(g.resize((g.width // SS, H), Image.BOX), float) / 255
                sc = blur_score(a)
                if best is None or sc < best[0]: best = (sc, g)
            g = best[1]
            big.paste(Image.composite(Image.new('L', g.size, 255), Image.new('L', g.size, 0), g), (base - 2 * SS, 0), g)
        a = np.asarray(big.resize((W, H), Image.BOX), float) / 255
        sc = blur_score(a)
        if best_dy is None or sc < best_dy[0]: best_dy = (sc, a)
    a = best_dy[1]
    if faint: a = np.where(a < faint, 0, a)
    return a


def draw(text, wt=400, fix=None):
    a = coverage(text, wt)
    a8 = (a * 255).round().astype(np.uint8)
    for (x, y, v) in (fix or []): a8[y, x] = v
    cm = Image.fromarray(a8)
    g = np.interp(np.arange(H), YK, GK)[:, None]
    col = np.stack([g, g, g + 1], -1) * np.ones((1, W, 1))
    near = np.asarray(cm.filter(ImageFilter.MaxFilter(3))) > 0
    rgb = np.where(near[..., None], col, np.array(BG, float))
    img = Image.fromarray(np.dstack([rgb.round().clip(0, 255), np.full((H, W), 255)]).astype(np.uint8), 'RGBA')
    return img, Image.merge('RGBA', [cm, cm, cm, Image.new('L', cm.size, 255)])
