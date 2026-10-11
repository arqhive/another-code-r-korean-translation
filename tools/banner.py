"""Wii 메뉴 디스크 채널 배너(files/opening.bnr) 한글화.
- 채널 이름: 10개 언어 칸 모두 한국어(게임처럼 본체 언어와 관계없이 한국어).
- 배너 로고(Banner_logo03, 기본 232×59 + 언어별 _UK·_FR·_GE·_ES·_IT 464×117)와
  아이콘 로고(Icon_logo02, 기본 + 언어별 124×40)는 tools/assets/banner/ 의 한글 그림이 있으면 모든 자리에 크기를 맞춰 넣는다.
  (유럽판은 본체 언어에 따라 언어별 그림을 고른다. 기본 그림은 일본어 로고 그대로였다.)
그림은 검정 바탕 흰 글씨(I8·I4, 밝기만 씀). GPT 요청은 gpt_prepare.py 의 B01·B02."""
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bnrpack
import gxtex
import paths

CHANNEL_NAME = '어나더 코드: R 기억의 문'   # 원문 アナザーコード：Ｒ　記憶の扉
ASSETS = paths.ASSETS / 'banner'
LOGOS = {'meta/banner.bin': ('Banner_logo03', 'B01_Banner_logo03.png'),
         'meta/icon.bin': ('Icon_logo02', 'B02_Icon_logo02.png')}


def fit(img, w, h):
    """검정 바탕 흰 글씨 그림을 비율 유지로 (w,h) 가운데에"""
    g = img.convert('L'); k = min(w / g.width, h / g.height)
    g = g.resize((max(1, round(g.width * k)), max(1, round(g.height * k))), Image.LANCZOS)
    c = Image.new('L', (w, h), 0); c.paste(g, ((w - g.width) // 2, (h - g.height) // 2))
    return Image.merge('RGBA', [c, c, c, Image.new('L', (w, h), 255)])


def main():
    src = open(paths.EU / 'files/opening.bnr', 'rb').read()
    bins = bnrpack.bins(src)
    repl = {}; n = 0
    for bp, (stem, png) in LOGOS.items():
        if not (ASSETS / png).exists(): continue
        img = Image.open(ASSETS / png)
        r = {}
        for path, _, a, b in bnrpack.u8_entries(bins[bp]):
            if os.path.basename(path).startswith(stem) and path.endswith('.tpl'):
                w, h = next(gxtex.tpl_images(bins[bp][a:a + b]))[1:3]
                r[path] = fit(img, w, h); n += 1
        repl[bp] = r
    out = bnrpack.patch_bnr(src, repl.get('meta/banner.bin'), repl.get('meta/icon.bin')) if repl else src
    out = bnrpack.set_names(out, {k: CHANNEL_NAME for k in range(10)})
    dst = paths.BUILD / 'files/opening.bnr'
    dst.parent.mkdir(parents=True, exist_ok=True)
    open(dst, 'wb').write(out)
    return {'채널 이름': CHANNEL_NAME, '로고 그림 자리': n}


if __name__ == '__main__':
    print(main())
