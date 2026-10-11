"""GPT 그림 재작업 준비: work/GPT/ 에 요청 묶음을 만든다(돌격 패미컴 워즈 VS 방식).
  원본/  GPT에 첨부할 원본(일본판, 일본판에 없으면 유럽판). 작은 그림은 픽셀 그대로 키운 _N배 판도 둔다.
  참고/  지금 패치에 들어간 한글판(_현재한글판)
  결과/  GPT가 만든 PNG를 「저장할 이름」으로 저장하는 곳
  비교/  gpt_import.py 가 원본 | 현재 | 반영 비교 시트를 만드는 곳
  목록.json  번호 → 에셋 파일·게임 크기·종류·마스크 짝·자동 마스크 값
  요청서.md  GPT 프롬프트와 번호별 표
재작업 단위는 에셋 PNG(tools/assets) 하나. 후리가나 띠·*ap 마스크 짝·장 제목 빛 마스크는 도구가 만들어서 대상이 아니다.
사용: python tools/gpt_prepare.py"""
import json
import math
import os
import re
import shutil
import sys

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gpt_request
import paths
import texread

GPT = paths.WORK / 'GPT'
JPA = paths.ASSETS / 'jp'
EUA = paths.ASSETS / 'eu_only'
RUBY = re.compile(r'(NAME_\w+?r(ap)?|\w*ruby\w*|TITLE_text02(ap)?)$')
GRAY = {0, 1, 2, 3}   # I4·I8·IA4·IA8 = 흰 글씨 마스크
LANGS = ('UK', 'ES', 'FR', 'GE', 'IT')

# 아직 번역 안 된 그림(10/10 전수 조사): 유럽판 퍼즐은 일본어 기본 그림을 두고 언어별 _UK 등을 바꿔 끼운다 → 둘 다 바꾼다
NEW = [
    ('N01', '헌사', 'PUZZLE/Z008.acrarc/Z008.ARC/lyt/timg/TITLE_text10.tpl#0',
     '이 이야기를, 천국의 엄마와\n줄리엣 레이크에서 만난\n많은 사람에게 바친다.', 'この物語を、天国のママと／ジュリエット・レイクで出会った／多くの人たちに捧げる。'),
    ('N02', 'pH판_알칼리성', 'PUZZLE/Z050_0{n}.acrarc/Z050_0{n}.ARC/lyt/timg/plate01.tpl#0', '알칼리성', 'アルカリ性'),
    ('N03', 'pH판_산성', 'PUZZLE/Z050_0{n}.acrarc/Z050_0{n}.ARC/lyt/timg/plate02.tpl#0', '산성', '酸性'),
    ('N04', 'pH판_강산성', 'PUZZLE/Z050_0{n}.acrarc/Z050_0{n}.ARC/lyt/timg/plate03.tpl#0', '강산성', '強酸性'),
    ('N05', 'pH판_중성', 'PUZZLE/Z050_0{n}.acrarc/Z050_0{n}.ARC/lyt/timg/plate04.tpl#0', '중성', '中性'),
    ('N06', '하나', 'PUZZLE/Z057.acrarc/Z057.ARC/lyt/timg/z057_text03.tpl#0', '하나!!', 'いちっ!!'),
    ('N07', '둘', 'PUZZLE/Z057.acrarc/Z057.ARC/lyt/timg/z057_text04.tpl#0', '둘!!', 'にっ!!'),
]
# 유럽판 영어 그림이라 기계 이름이 TAS(대사는 일본판 기준 RAS) — GPT 없이 일본판 그림으로 바꾸면 됨
TAS = [
    'ITEM/061.brres#RAS3', 'ITEM/109.brres#RAS_plus', 'MAP/E_R110_N.acrarc/E_R110_N.BRTEX#RAS_plusa',
    'LYT/005/Interrupt_E_R040_07.ARC/Interrupt_E_R040_07/timg/Interrupt_E_R040_02_07.tpl#0',
    'LYT/ITEM/GET_061.ARC/ITEM_061_1/timg/ITEM_061_1.tpl#0',
    'PUZZLE/Z071.acrarc/Z071.ARC/lyt/timg/RAS_text08.tpl#0', 'PUZZLE/Z071.acrarc/Z071.ARC/lyt/timg/RAS_text08ap.tpl#0',
    'PUZZLE/Z071.acrarc/Z071.ARC/lyt/timg/RAS_text13.tpl#0', 'PUZZLE/Z071.acrarc/Z071.ARC/lyt/timg/RAS_text13ap.tpl#0',
    'PUZZLE/Z081.acrarc/Z081.BRTEX#memo_n']


def stem(png):
    return os.path.basename(png)[:-4].split('_', 1)[1]


def bg_kind(img, fmt):
    if fmt in GRAY: return '검정 바탕 흰 글씨'
    a = np.asarray(img)[..., 3]
    if a.min() >= 250: return '불투명'
    # 대부분 불투명한 그림(DAS 책 아이콘 등)은 그림째 맞추고 투명 모양은 기존 것을 쓴다
    return '투명' if (a < 250).mean() >= 0.5 else '그림(가장자리 투명)'


def scale_for(w, h):
    return min(4, max(1, math.ceil(512 / max(w, h))))


def text_mask(img, thr):
    c = np.asarray(img.convert('RGB'), float); bg = np.median(c.reshape(-1, 3), 0)
    return (np.sqrt(((c - bg) ** 2).sum(-1)) > thr).astype('uint8') * 255


def make_ap(img, p):
    """색 그림 → 글자 마스크(굵게 부풀림 + 흐림). p = {'thr', 'r', 'blur'}"""
    m = Image.fromarray(text_mask(img, p['thr']))
    if p['r']: m = m.filter(ImageFilter.MaxFilter(2 * p['r'] + 1))
    if p['blur']: m = m.filter(ImageFilter.GaussianBlur(p['blur']))
    return Image.merge('RGBA', [m, m, m, Image.new('L', m.size, 255)])


def fit_ap(color, ap):
    """일본판 짝에서 「색 그림 → 마스크」 값을 찾는다. 맞는 값이 없으면 None(마스크는 그대로 둠)"""
    want = np.asarray(ap.convert('L'), float)
    best = None
    for thr in (30, 50, 80):
        for r in range(0, 5):
            for blur in (0, 0.7):
                p = {'thr': thr, 'r': r, 'blur': blur}
                err = np.abs(np.asarray(make_ap(color, p).convert('L'), float) - want).mean() / 255
                if best is None or err < best[0]: best = (err, p)
    return dict(best[1], err=round(best[0], 4)) if best[0] < 0.06 else None


def save_pair(it, orig, cur):
    """원본(첨부용)·현재 한글판 저장, 파일 이름 기록"""
    base = f"{it['id']}_{it['name']}"
    w, h = orig.size; n = scale_for(w, h)
    it['attach'] = f'원본/{base}_원본_{w}x{h}.png'; orig.save(GPT / it['attach'])
    if n > 1:
        it['attach'] = f'원본/{base}_원본_{n}배_{w * n}x{h * n}.png'
        orig.resize((w * n, h * n), Image.NEAREST).save(GPT / it['attach'])
    if cur is not None:
        it['ref'] = f'참고/{base}_현재한글판.png'; cur.save(GPT / it['ref'])
        if n > 1:
            it['ref'] = f'참고/{base}_현재한글판_{n}배.png'
            cur.resize((cur.width * n, cur.height * n), Image.NEAREST).save(GPT / it['ref'])
    it['save_as'] = f'{base}.png'


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    paths.ensure_extracted()
    for d in ('원본', '참고'):
        if (GPT / d).exists(): shutil.rmtree(GPT / d)
    for d in ('원본', '참고', '결과', '비교'):
        (GPT / d).mkdir(parents=True, exist_ok=True)
    items = []
    # J: 일본판 그림 대응 에셋
    idx = json.load(open(JPA / '_목록.json', encoding='utf-8'))
    by = {stem(e['png']): e for e in idx}
    for e in idx:
        nm = stem(e['png']); cat = e['png'].split('/')[0]
        if RUBY.search(nm) or (nm.endswith('ap') and nm[:-2] in by): continue
        if cat == '09_퍼즐': continue   # N 번호(퍼즐 미번역 그림)가 반영되며 생긴 에셋 — 아래 N 에서 다룸
        t = texread.info('jp', e['jp_paths'][0])
        fmt = t[2] if t else None
        kind = 'tool' if cat.startswith('04_') else ('mask' if fmt in GRAY else 'color')
        it = {'id': f"J{cat[:2]}-{os.path.basename(e['png'])[:3]}", 'name': nm, 'group': cat, 'kind': kind,
              'asset': 'jp/' + e['png'], 'size': e['size'], 'fmt': fmt, 'keys': e['jp_paths']}
        orig = texread.get('jp', e['jp_paths'][0]); cur = Image.open(JPA / e['png']).convert('RGBA')
        it['bg'] = bg_kind(orig, fmt)
        if nm + 'ap' in by and kind != 'tool':
            ape = by[nm + 'ap']; it['ap_asset'] = 'jp/' + ape['png']
            it['ap_fit'] = fit_ap(orig, texread.get('jp', ape['jp_paths'][0]))
        save_pair(it, orig, cur); items.append(it)
    # E: 유럽판 전용 그림
    for e in json.load(open(EUA / '_목록.json', encoding='utf-8'))['items']:
        if not (EUA / e['png']).exists(): continue
        cat = e['png'].split('/')[0]; t = texread.info('eu', e['eu_path']); fmt = t[2] if t else None
        orig = texread.get('eu', e['eu_path']); cur = Image.open(EUA / e['png']).convert('RGBA')
        it = {'id': f"E{cat[:2]}-{os.path.basename(e['png'])[:3]}", 'name': stem(e['png']), 'group': cat,
              'kind': 'mask' if fmt in GRAY else 'color', 'asset': 'eu_only/' + e['png'], 'size': e['size'], 'fmt': fmt,
              'keys': [e['eu_path']], 'bg': bg_kind(orig, fmt)}
        if cat.startswith('01_'): it['note'] = '빛 마스크(*ap)는 빌드가 자동으로 만듦'
        save_pair(it, orig, cur); items.append(it)
    # E04: 연구소 층 안내판(유럽판 전용 묶음 3개, insert_tex.eu_only 가 직접 넣음 — 목록에 없음)
    dck = [f'LANG/ENG/LYT/000/DC_R130_R100_{nm}.ARC/DC_R130_R100_{nm}/timg/DC_R130_02.tpl#0' for nm in ('IN', 'OUT', 'loop')]
    t = texread.info('eu', dck[0]); orig = texread.get('eu', dck[0])
    it = {'id': 'E04-001', 'name': 'DC_R130_02_연구소안내판', 'group': '04_연구소안내판', 'kind': 'color',
          'asset': 'eu_only/04_연구소안내판/DC_R130_02.png', 'size': [t[0], t[1]], 'fmt': t[2], 'keys': dck,
          'bg': bg_kind(orig, t[2]), 'note': '204호 강조·「어나더」 제어실 칸 없음(영어판 전용 상태)'}
    save_pair(it, orig, Image.open(EUA / '04_연구소안내판/DC_R130_02.png').convert('RGBA')); items.append(it)
    # N: 아직 번역 안 된 퍼즐 그림
    for nid, name, key, ko, ja in NEW:
        keys = [key.format(n=n) for n in range(1, 8)] if '{n}' in key else [key]
        allk = []
        for k in keys:
            allk.append(k)
            for lg in LANGS:
                v = k.replace('.tpl#', f'_{lg}.tpl#')
                if texread.info('eu', v): allk.append(v)
        t = texread.info('jp', keys[0]); orig = texread.get('jp', keys[0])
        it = {'id': nid, 'name': name, 'group': '09_퍼즐_미번역', 'kind': 'mask' if t[2] in GRAY else 'color',
              'asset': f'jp/09_퍼즐/{nid}_{os.path.basename(keys[0]).split(".")[0]}.png', 'size': [t[0], t[1]], 'fmt': t[2],
              'keys': allk, 'bg': bg_kind(orig, t[2]), 'ko': ko, 'ja': ja, 'new': True}
        save_pair(it, orig, None); items.append(it)
    # B: Wii 메뉴 디스크 채널 배너(opening.bnr). 원본은 일본판(같은 구성의 일본어 로고), 참고는 게임 안 한글 타이틀 로고
    import bnrpack
    jbn = {os.path.basename(p): im for _, p, im, f in bnrpack.images(open(paths.JP / 'files/opening.bnr', 'rb').read())}
    ref_logo = Image.open(JPA / '06_타이틀_시스템/009_TITLE_logo03.png').convert('RGBA')
    ref = Image.new('RGBA', ref_logo.size, (0, 0, 0, 255)); ref.alpha_composite(ref_logo)
    for bid, name, tpl, fmt, note in (
            ('B01', 'Banner_logo03', 'Banner_logo03.tpl', 1, 'Wii 메뉴 채널 배너 로고. 기본(232×59)과 언어별 5장(464×117)에 모두 들어감'),
            ('B02', 'Icon_logo02', 'Icon_logo02.tpl', 0, 'Wii 메뉴 채널 아이콘 로고(124×40, 아주 작음). 기본과 언어별 5장에 모두 들어감')):
        orig = jbn[tpl]
        it = {'id': bid, 'name': name, 'group': '10_채널배너', 'kind': 'mask', 'asset': f'banner/{bid}_{name}.png',
              'size': list(orig.size), 'fmt': fmt, 'keys': [f'files/opening.bnr {name}*'], 'bg': '검정 바탕 흰 글씨',
              'note': note, 'new': False}
        save_pair(it, orig, None)
        it['ref'] = f'참고/{bid}_{name}_게임속한글타이틀로고.png'; ref.save(GPT / it['ref'])
        items.append(it)
    tas = [{'id': f'T{i + 1:02d}', 'key': k} for i, k in enumerate(TAS)]
    gpt_request.write(items, tas, GPT / '요청서.md')   # 현재 문구 초안(ko_hint)도 채운다
    json.dump({'items': items, 'tas': tas}, open(GPT / '목록.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    kinds = {}
    for it in items: kinds[it['kind']] = kinds.get(it['kind'], 0) + 1
    print('항목', len(items), kinds, '마스크 짝', sum(1 for i in items if 'ap_asset' in i),
          '자동 마스크 맞음', sum(1 for i in items if i.get('ap_fit')))


if __name__ == '__main__':
    main()
