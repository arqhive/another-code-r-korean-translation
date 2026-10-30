"""타이틀 「버튼을 눌러 주세요」(LYT/TITLE.ARC TITLE_text01 + ap 마스크)를 글꼴로 직접 그린다.
일본판 구조: 색 그림 = 짙은 청록 바탕 + 위→아래 흰색→회색 그라데이션 글자, 마스크 = 글자를 1~2px 부풀린 모양
(게임에서 색 × 마스크 → 바탕색이 글자 테두리가 됨). GPT 그림에서 마스크를 뽑으면 테두리가 들쭉날쭉해서(10/11 사용자 지적)
4배 크기로 그려 줄이는 방식으로 매끈하게 만든다.
글꼴은 나눔스퀘어라운드 ExtraBold 19px·자간 3·테두리 1.5px(10/11, 일본판 둥근 고딕과 비슷).
사용: python tools/title_text.py [글꼴 파일] [자간(px)] [테두리(px)]   → tools/assets/jp/06_타이틀_시스템 의 TITLE_text01·ap PNG 갱신"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths

TEXT = '버튼을 눌러 주세요'
W, H, SS = 224, 24, 4
BG = (43, 64, 65)
TOP, BOTTOM = (255, 255, 255), (186, 190, 190)   # 일본판 글자 위·아래 색


def render(font_path, spacing=3.0, stroke=1.5, size=19):
    """크기 19 = 일본판 글자 세로 범위(2~22행)와 같음"""
    f = ImageFont.truetype(font_path, size * SS)
    # 글자마다 놓아 자간을 준다
    xs = []; x = 0
    for ch in TEXT:
        xs.append(x)
        x += f.getlength(ch) + spacing * SS
    total = x - spacing * SS
    bb = f.getbbox('가', anchor='ls')
    base = (H * SS + (bb[3] - bb[1])) // 2 - bb[3] // 1
    x0 = (W * SS - total) / 2
    txt = Image.new('L', (W * SS, H * SS), 0); d = ImageDraw.Draw(txt)
    out = Image.new('L', (W * SS, H * SS), 0); do = ImageDraw.Draw(out)
    for ch, x in zip(TEXT, xs):
        d.text((x0 + x, base), ch, font=f, fill=255, anchor='ls')
        do.text((x0 + x, base), ch, font=f, fill=255, anchor='ls', stroke_width=round(stroke * SS), stroke_fill=255)
    # 색 그림: 바탕 + 그라데이션 글자(글자 높이 범위에서 위→아래)
    ys = np.nonzero(np.asarray(txt).max(1))[0]; y0, y1 = ys.min(), ys.max()
    # 그라데이션은 4줄 단위로 같은 색: 게임 압축(CMPR)이 4×4 칸마다 색 둘만 쓰므로, 한 칸 안에서 글자색이 바뀌면
    # 글자 속에 얼룩이 생긴다(10/31 사용자 지적). 칸 가운데 줄 값을 쓴다
    band = (np.arange(H * SS) // (4 * SS)) * 4 * SS + 2 * SS
    t = np.clip((band - y0) / max(1, y1 - y0), 0, 1)[:, None, None]
    grad = (np.array(TOP) * (1 - t) + np.array(BOTTOM) * t) * np.ones((1, W * SS, 1))
    a = np.asarray(txt, float)[..., None] / 255
    col = np.array(BG) * (1 - a) + grad * a
    color = Image.fromarray(col.astype('uint8'), 'RGB').resize((W, H), Image.LANCZOS).convert('RGBA')
    m = out.resize((W, H), Image.LANCZOS)
    # 글자 둘레 1px 는 테두리를 꽉 채운다: 글자가 그림 위쪽에 붙은 곳(「요」의 ㅇ 위)은 테두리가 반투명으로 남아
    # 끊겨 보였다(10/31 사용자 지적)
    core = np.asarray(txt.resize((W, H), Image.BOX)) > 60
    ring = np.asarray(Image.fromarray((core * 255).astype('uint8')).filter(ImageFilter.MaxFilter(3))) > 0
    m = Image.fromarray(np.where(ring, 255, np.asarray(m)).astype('uint8'))
    mask = Image.merge('RGBA', [m, m, m, Image.new('L', (W, H), 255)])
    return color, mask


def assets():
    idx = json.load(open(paths.ASSETS / 'jp/_목록.json', encoding='utf-8'))
    c = next(e['png'] for e in idx if e['png'].endswith('_TITLE_text01.png'))
    a = next(e['png'] for e in idx if e['png'].endswith('_TITLE_text01ap.png'))
    return paths.ASSETS / 'jp' / c, paths.ASSETS / 'jp' / a


if __name__ == '__main__':
    font = sys.argv[1] if len(sys.argv) > 1 else str(paths.TOOLS / 'fonts/NanumSquareRoundEB.ttf')
    sp = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
    st = float(sys.argv[3]) if len(sys.argv) > 3 else 1.5
    c, m = render(font, sp, st)
    pc, pa = assets(); c.save(pc); m.save(pa)
    print('저장:', pc.name, pa.name)
