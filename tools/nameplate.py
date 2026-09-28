"""대화창 화자 이름표(LYT/WIN.ARC <이름>.tpl + <이름>ap.tpl)를 2배 해상도(200x40)로 새로 그려 넣는다.
- 원본 100x20 을 돌핀 고해상도에서 늘리면 뭉개지고, 가는 글씨 마스크(ap)는 테두리가 없어 흐려 보였다.
- 일본판 방식: 색 텍스처(배경색 + 밝은 글씨) × 굵게 부풀린 마스크 → 글자 둘레에 배경색 테두리.
- 창 크기(100x20)는 그대로 두고 텍스처만 2배로 키운다(TPL 새로 만듦).
이름: tools/data/nameplates.json, 배경색·글자색: tools/assets/jp/04_대화창_이름표 의 같은 이름 그림에서 추출."""
import json
import os
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gxenc
import gxtex
import paths
import u8

SRC = paths.ASSETS / 'jp/04_대화창_이름표'
FONT = 'C:/Windows/Fonts/malgunbd.ttf'
W, H = 200, 40
TEXT_H = 27   # 한글 글자 높이(원본 14px × 2 정도)
STROKE = 3    # 마스크 테두리 두께


def make_tpl(orig, img, fmt):
    """원본 TPL 머리(필터 등)를 유지하고 크기·자료만 바꾼 단일 이미지 TPL"""
    ih = struct.unpack('>I', orig[0xC:0x10])[0]
    hdr = bytearray(orig[ih:ih + 0x24])
    struct.pack_into('>HHII', hdr, 0, img.height, img.width, fmt, 0x40)
    out = bytearray(b'\x00\x20\xaf\x30' + struct.pack('>III', 1, 0xC, 0x14) + b'\0' * 4)
    out += hdr; out += b'\0' * (0x40 - len(out)); out += gxenc.encode(img, fmt)
    return bytes(out)


def fit_font(text):
    size = 30
    while True:
        f = ImageFont.truetype(FONT, size)
        bb = f.getbbox(text, stroke_width=STROKE)
        if bb[2] - bb[0] <= W - 8 or size <= 16: return f
        size -= 1


def render(text, bg, fg):
    f = fit_font(text)
    bb = f.getbbox('가')
    tb = f.getbbox(text, stroke_width=STROKE)
    x = (W - (tb[2] - tb[0])) // 2 - tb[0]; y = (H - (bb[3] - bb[1])) // 2 - bb[1]
    col = Image.new('RGBA', (W, H), tuple(bg) + (255,))
    ImageDraw.Draw(col).text((x, y), text, font=f, fill=tuple(fg) + (255,))
    ap = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    ImageDraw.Draw(ap).text((x, y), text, font=f, fill=(255, 255, 255, 255), stroke_width=STROKE, stroke_fill=(255, 255, 255, 255))
    return col, ap


def colors(png):
    g = np.asarray(Image.open(png).convert('RGB')).reshape(-1, 3).astype(int)
    L = g.mean(1)
    return np.median(g, 0).astype(int), g[L >= np.percentile(L, 97)].mean(0).astype(int)


def main(arc_path=None):
    arc_path = arc_path or paths.BUILD / 'files/REVOLUTION/LANG/ENG/LYT/WIN.ARC'
    names = json.load(open(paths.DATA / 'nameplates.json', encoding='utf-8'))['names']
    pngs = {f.split('_', 1)[1][:-4]: f for f in os.listdir(SRC) if f.endswith('.png')}
    a = u8.load(arc_path); files = a.files(); n = 0
    for base, ko in names.items():
        kc = f'WIN/timg/{base}.tpl'; ka = f'WIN/timg/{base}ap.tpl'
        if kc not in files or ka not in files: continue
        bg, fg = colors(SRC / pngs[base])
        col, ap = render(ko, bg, fg)
        fc = next(gxtex.tpl_images(files[kc]))[3]; fa = next(gxtex.tpl_images(files[ka]))[3]
        files[kc] = make_tpl(files[kc], col, fc); files[ka] = make_tpl(files[ka], ap, fa)
        n += 1
    open(arc_path, 'wb').write(u8.from_files(files))
    return n


if __name__ == '__main__':
    print('이름표', main())
