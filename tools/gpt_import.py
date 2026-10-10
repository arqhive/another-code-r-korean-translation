"""GPT 재작업 결과 반영: work/GPT/결과/<번호>_<이름>.png → tools/assets 의 해당 에셋(게임 크기·형식에 맞춤).
- 이미 게임 크기와 같은 그림은 그대로 쓴다(검정 바탕 흰 글씨는 흑백으로만 바꿈).
- 글자 그림(투명 배경·검정 바탕 흰 글씨): GPT 그림의 내용 덩어리를 잘라 높이를 현재 한글판(새 그림은 원본) 덩어리에 맞추고
  그 가운데에 놓는다. 칸보다 넓으면 칸 안으로 줄인다.
- 불투명 그림(간판·띠 등): 전체를 게임 크기로 줄인다(비율이 다르면 가운데를 잘라 맞춤).
- 투명 배경인데 GPT가 배경을 채워 보냈으면 테두리 색을 배경으로 보고 지운다.
- *ap 마스크 짝이 있는 그림은 새 색 그림에서 마스크를 다시 만든다(gpt_prepare 가 일본판 짝에서 잰 값).
- 새 그림(N 번호, 아직 번역 안 된 퍼즐 그림)은 tools/assets/jp/09_퍼즐/ 에 만들고 _목록.json 에 넣는다.
- 바꾸기 전 에셋은 work/GPT/이전_assets/ 에 한 번 남기고, work/GPT/비교/<번호>.png 에 원본 | 이전 | 반영 시트를 만든다.
빌드는 따로 한다(python tools/build.py).
사용: python tools/gpt_import.py            (결과 폴더 전부)
      python tools/gpt_import.py J01-001 N02 (번호 지정)"""
import json
import os
import shutil
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gpt_prepare
import gxtex
import paths

GPT = paths.WORK / 'GPT'


def content_box(img, mask_like):
    """내용 덩어리 상자: 마스크류는 밝기, 그 외는 알파 기준"""
    a = np.asarray(img.convert('L') if mask_like else img.getchannel('A'))
    ys, xs = np.nonzero(a > 40)
    if not len(xs): return (0, 0, img.width, img.height)
    return (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)


def drop_background(img):
    """배경이 채워진 그림 → 테두리 중앙값 색을 투명하게"""
    a = np.asarray(img.convert('RGBA')).astype(float)
    if a[..., 3].min() < 250: return img
    edge = np.concatenate([a[0, :, :3], a[-1, :, :3], a[:, 0, :3], a[:, -1, :3]])
    bg = np.median(edge, 0)
    d = np.sqrt(((a[..., :3] - bg) ** 2).sum(-1))
    a[..., 3] = np.clip((d - 12) * 8, 0, 255)
    return Image.fromarray(a.astype('uint8'), 'RGBA')


def fit_text(gpt, w, h, box, mask_like):
    """GPT 그림 내용을 (w,h) 캔버스의 box 높이에 맞춰 box 가운데에 놓는다"""
    src = gpt.crop(content_box(gpt, mask_like))
    bx0, by0, bx1, by1 = box
    k = (by1 - by0) / src.height
    if src.width * k > w - 2: k = (w - 2) / src.width
    nw, nh = max(1, round(src.width * k)), max(1, round(src.height * k))
    src = src.resize((nw, nh), Image.LANCZOS)
    cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
    x = int(round(min(max(cx - nw / 2, 1), w - nw - 1))); y = int(round(min(max(cy - nh / 2, 0), h - nh)))
    canvas = Image.new('RGBA', (w, h), (0, 0, 0, 255) if mask_like else (0, 0, 0, 0))
    if mask_like:
        canvas.paste(src.convert('L').convert('RGBA'), (x, y))
    else:
        canvas.alpha_composite(src, (x, y))
    return canvas


def fit_full(gpt, w, h):
    r, rr = gpt.width / gpt.height, w / h
    if abs(r - rr) / rr > 0.02:   # 비율이 다르면 가운데를 잘라 맞춤
        if r > rr:
            nw = round(gpt.height * rr); gpt = gpt.crop(((gpt.width - nw) // 2, 0, (gpt.width - nw) // 2 + nw, gpt.height))
        else:
            nh = round(gpt.width / rr); gpt = gpt.crop((0, (gpt.height - nh) // 2, gpt.width, (gpt.height - nh) // 2 + nh))
    return gpt.resize((w, h), Image.LANCZOS)


def as_mask(img):
    g = img.convert('L')
    return Image.merge('RGBA', [g, g, g, Image.new('L', g.size, 255)])


def sheet(it, orig, prev, new, out):
    F = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 13)
    n = gpt_prepare.scale_for(*new.size)
    ims = [(lab, im.resize((im.width * n, im.height * n), Image.NEAREST)) for lab, im in
           (('원본', orig), ('이전', prev), ('반영', new)) if im is not None]
    W = max(im.width for _, im in ims) + 20; H = sum(im.height + 26 for _, im in ims) + 24
    s = Image.new('RGB', (W, H), (70, 70, 85)); d = ImageDraw.Draw(s)
    d.text((6, 4), f"{it['id']} {it['name']} ({it['size'][0]}×{it['size'][1]})", font=F, fill=(255, 255, 255)); y = 24
    for lab, im in ims:
        d.text((6, y), lab, font=F, fill=(220, 220, 230)); y += 18
        chk = Image.new('RGBA', im.size, (110, 110, 125, 255))
        for yy in range(0, im.height, 16):
            for xx in range((yy // 16) % 2 * 16, im.width, 32):
                ImageDraw.Draw(chk).rectangle([xx, yy, xx + 15, yy + 15], fill=(140, 140, 155, 255))
        chk.alpha_composite(im); s.paste(chk.convert('RGB'), (10, y)); y += im.height + 8
    s.save(out)


def main(ids):
    sys.stdout.reconfigure(encoding='utf-8')
    lst = json.load(open(GPT / '목록.json', encoding='utf-8'))
    items = {it['id']: it for it in lst['items']}
    results = sorted(f for f in os.listdir(GPT / '결과') if f.lower().endswith('.png'))
    done = []
    for f in results:
        iid = f.split('_')[0]
        if ids and iid not in ids: continue
        it = items.get(iid)
        if it is None: print('  모르는 번호:', f); continue
        if it['kind'] == 'tool': print('  도구가 그리는 그림이라 건너뜀:', f); continue
        w, h = it['size']; mask_like = it['bg'] == '검정 바탕 흰 글씨'
        gpt = Image.open(GPT / '결과' / f).convert('RGBA')
        asset = paths.ASSETS / it['asset']
        prev = Image.open(asset).convert('RGBA') if asset.exists() else None
        orig = Image.open(GPT / it['attach']).convert('RGBA')
        if orig.size != (w, h): orig = orig.resize((w, h), Image.NEAREST)   # _N배 첨부본 → 게임 크기
        if gpt.size == (w, h):   # 이미 게임 크기로 맞춰 온 그림은 그대로(마스크만 흑백으로)
            new = as_mask(gpt) if mask_like else gpt
        elif it['bg'] == '불투명':
            new = fit_full(gpt, w, h).convert('RGBA')
            new.putalpha(255)
        elif it['bg'] == '그림(가장자리 투명)':   # 그림째 맞추고 투명 모양은 이전(없으면 원본) 것
            new = fit_full(gpt, w, h).convert('RGBA')
            new.putalpha((prev if prev is not None else orig).getchannel('A'))
        else:
            if not mask_like: gpt = drop_background(gpt)
            ref = prev if prev is not None else orig
            new = fit_text(gpt, w, h, content_box(ref, mask_like), mask_like)
            if mask_like: new = as_mask(new)
        if prev is not None:
            bk = GPT / '이전_assets' / (iid + '.png')
            if not bk.exists():
                bk.parent.mkdir(exist_ok=True); shutil.copy2(asset, bk)
        asset.parent.mkdir(parents=True, exist_ok=True)
        new.save(asset)
        if it.get('ap_asset') and it.get('ap_fit'):
            gpt_prepare.make_ap(new, it['ap_fit']).save(paths.ASSETS / it['ap_asset'])
        if it.get('new'):
            add_new(it)
        sheet(it, orig, prev, new, GPT / '비교' / (iid + '.png'))
        done.append(iid)
    print(f'반영 {len(done)}장:', ' '.join(done))
    if done: print('비교 시트: work/GPT/비교/  · 빌드: python tools/build.py')


def add_new(it):
    """새 그림을 일본판 대응 목록(_목록.json)에 넣는다(insert_tex 가 언어별 _UK 등 모든 자리에 넣음)"""
    p = gpt_prepare.JPA / '_목록.json'
    idx = json.load(open(p, encoding='utf-8'))
    png = it['asset'].split('/', 1)[1]
    idx = [e for e in idx if e['png'] != png]
    idx.append({'png': png, 'size': it['size'], 'format': gxtex.NAME.get(it['fmt'], str(it['fmt'])), 'jp_paths': it['keys']})
    json.dump(idx, open(p, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main(set(sys.argv[1:]))
