"""한글화 이미지(tools/assets/jp/<분류>/<파일>.png, 일본판 그림 대응)를 유럽판에 넣는다.
방식
- 레이아웃 묶음(LYT/…): 일본판 묶음을 통째로 가져와 한국어 이미지를 크기 조정 없이 넣고, 유럽판 자리
  (영어 폴더에 같은 이름 묶음이 있으면 그곳, 없으면 공용)에 쓴다. GPT 이미지가 일본판 크기·배치에 맞춰져 있고,
  유럽판은 영어에 맞춰 레이아웃을 바꿔 둔 곳이 많아서(A 버튼 위치, 인물 카드 B 창 삭제, 지도 말풍선 폭 등)
  일본판 레이아웃을 쓰는 편이 정확하다. 두 판 묶음의 차이는 라벨 이미지·레이아웃·일부 애니메이션뿐임을 확인함.
- 3D 배경(MAP/*.acrarc 안 BRRES): 유럽판 공용 파일의 같은 텍스처 자리에 같은 크기로 넣는다.
- 후리가나 띠(NAME_*r·*ruby·TITLE_text02 등)는 한국어에 필요 없으므로 투명하게 비운다.
- 유럽판 전용 그림(장 제목·엔딩 이름·오프닝 자막 등)은 tools/assets/eu_only 에서 eu_only() 가 넣는다.
- 참고: 일본판 퍼즐 Z008 글씨 그림은 유럽판에 없다(유럽판은 PUZZLE_TXT_008.MESS 텍스트로 표시)."""
import json
import os
import re
import struct
import sys
from collections import Counter, defaultdict

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gxenc
import gxtex
import paths
import u8

JPR = paths.JP / 'files/REVOLUTION'
EUR = paths.EU / 'files/REVOLUTION'
OUT = paths.BUILD / 'files/REVOLUTION'
GPT = paths.ASSETS / 'jp'
# 유럽판 레이아웃을 그대로 써야 하는 묶음: 일본판은 오프닝 자막이 영상에 박혀 있어 레이아웃에 자막 창이 없음
# (일본판 묶음을 쓰면 opTEXT 자막이 통째로 사라짐, 9/28 v0.1.3 사용자 확인)
EU_LAYOUT = {'LYT/MOV/TITLE_LOGO.ARC'}
# 일본판 묶음을 쓰되 이 레이아웃 파일만 유럽판 것으로: 설정 화면은 일본판이 「ルビ表示」(후리가나 표시) 줄을 포함한 세 줄,
# 유럽판은 그 줄을 화면 밖(y -310)으로 빼고 두 줄. 한글엔 후리가나가 없어 유럽판 배치를 쓴다(10/11 사용자 제보).
EU_LAYOUT_FILES = {'LANG/ENG/LYT/MENU.ARC': ['MENU/blyt/DAS_OPTION_top.brlyt']}
RUBY = re.compile(r'(NAME_\w+?r(ap)?|\w*ruby\w*|TITLE_text02(ap)?)\.png$')


def split_key(key):
    """'LYT/TITLE.ARC/TITLE/timg/x.tpl#0' → ('LYT/TITLE.ARC', 'TITLE/timg/x.tpl', 0)"""
    path, idx = key.split('#')
    idx = int(idx) if idx.isdigit() else idx  # TPL = 번호, BRRES TEX0 = 이름
    low = path.lower()
    # 디스크 파일 = 먼저 나오는 묶음(퍼즐 'X.acrarc/X.ARC/…' 는 .acrarc 가 파일, 안쪽 .ARC 는 묶음 안 묶음)
    hits = [(p, ext) for ext in ('.arc/', '.acrarc/') for p in [low.find(ext)] if p >= 0]
    if hits:
        p, ext = min(hits)
        return path[:p + len(ext) - 1], path[p + len(ext):], idx
    return path, None, idx


def tpl_image(tpl, idx):
    for i, w, h, f, off, nb, pal in gxtex.tpl_images(tpl):
        if i == idx:
            return w, h, f, off, nb, pal
    raise KeyError(idx)


def tex0_find(d, name):
    """BRRES 안 이름이 name 인 TEX0 → (자료 절대 위치, w, h, fmt)"""
    i = d.find(b'TEX0')
    while i >= 0:
        doff, noff = struct.unpack('>II', d[i + 0x10:i + 0x18])
        if d[i + noff:d.index(b'\0', i + noff)].decode('ascii', 'replace') == name:
            w, h, f = struct.unpack('>HHI', d[i + 0x1C:i + 0x24])
            return i + doff, w, h, f
        i = d.find(b'TEX0', i + 4)
    raise KeyError(name)


def eu_target(f):
    """일본판 묶음 경로 → 유럽판에 쓸 경로(영어 폴더 우선, 대소문자 무시)"""
    for base in ('LANG/ENG/', ''):
        d = EUR / base / os.path.dirname(f)
        if d.is_dir():
            m = [x for x in os.listdir(d) if x.lower() == os.path.basename(f).lower()]
            if m: return base + os.path.dirname(f) + '/' + m[0]
    return None


def image_for(png):
    img = Image.open(GPT / png).convert('RGBA')
    if RUBY.search(os.path.basename(png)):
        return Image.new('RGBA', img.size, (0, 0, 0, 0)), True
    return img, False


def replace_tex(data, inner, i, img, st, same_size, fit=False):
    """fit=True: 크기가 다르면 비율을 유지해 칸 안으로 줄인 뒤 가운데에 둔다(언어별 _UK 등 크기가 다른 자리)"""
    tpl = bytearray(data)
    if isinstance(i, str):
        eo, ew, eh, efm = tex0_find(bytes(tpl), i); en = gxtex.size(ew, eh, efm)
    else:
        ew, eh, efm, eo, en, epal = tpl_image(bytes(tpl), i)
    if efm in (8, 9, 10):
        st['팔레트 형식(미처리)'] += 1; return data
    if (img.width, img.height) != (ew, eh):
        if fit:
            k = min(ew / img.width, eh / img.height, 1)
            img = img.resize((max(1, round(img.width * k)), max(1, round(img.height * k))), Image.LANCZOS)
        elif same_size: raise ValueError(f'{inner}: 크기 다름 {img.size} ≠ {(ew, eh)}')
        c = Image.new('RGBA', (ew, eh), (0, 0, 0, 0)); c.paste(img, ((ew - img.width) // 2, (eh - img.height) // 2)); img = c
    tpl[eo:eo + en] = gxenc.encode(img, efm)[:en]
    return bytes(tpl)


# 유럽판 묶음에만 있는 파일 중 한국어로 채울 것: 파일 이름 → GPT 이미지(같은 뜻의 일본판 그림 번역본)
EXTRA_FILL = {
    'ENG_s_banner.tpl': '06_타이틀_시스템/006_s_banner.png',  # 세이브 배너(언어별 5개 → 모두 한국어)
    'FRA_s_banner.tpl': '06_타이틀_시스템/006_s_banner.png',
    'GER_s_banner.tpl': '06_타이틀_시스템/006_s_banner.png',
    'ITA_s_banner.tpl': '06_타이틀_시스템/006_s_banner.png',
    'SPA_s_banner.tpl': '06_타이틀_시스템/006_s_banner.png',
    'strapA.tpl': '06_타이틀_시스템/005_4_3strapA.png',        # STRAP_4_3 의 유럽판 이름(640x480, 일본판 640x456 가운데)
    'CHARA_34nap.tpl': '05_DAS_메뉴/005_CHARA_04nap2.png',     # Greg 이름표(일본판 CHARA_04nap2 グレッグ)
}


def merge_eu_only(tgt, a, st):
    """일본판 묶음을 쓴 경우, 유럽판 묶음에만 있는 파일을 합친다(없으면 게임이 찾다가 멈춤: 세이브 배너 등).
    합친 파일 중 EXTRA_FILL 에 있는 것은 한국어 그림으로 채운다. 나머지(DAS 배경 장식 영어·오프닝 자막)는 그대로."""
    if not (EUR / tgt).exists(): return a.build()
    e = u8.load(EUR / tgt).files(); f = a.files()
    extra = [k for k in e if k not in f]
    if not extra: return a.build()
    files = dict(f)
    for k in extra:
        v = e[k]; nm = os.path.basename(k)
        if nm in EXTRA_FILL:
            v = replace_tex(v, k, 0, Image.open(GPT / EXTRA_FILL[nm]).convert('RGBA'), st, False)
            st['유럽판 전용 파일 한국어로 채움'] += 1
        files[k] = v
    st['유럽판 전용 파일 합침'] += len(extra)
    return u8.from_files(files)


# 일본판 그림을 그대로 쓸 곳: 유럽판 영어 그림은 기계 이름이 TAS 인데 대사는 일본판 기준 RAS(10/10 전수 조사).
# 일본판 같은 자리 그림이 영어 RAS 판이라 그걸 유럽판 형식으로 다시 넣는다.
# 10/30 사용자 결정: 영상에도 TRUE ANOTHER SYSTEM 이 박혀 있어 기계 이름을 TAS 로 통일 → 쓰지 않음(USE_JP_IMAGE=False).
USE_JP_IMAGE = False
JP_IMAGE = [
    'ITEM/061.brres#RAS3', 'ITEM/109.brres#RAS_plus', 'MAP/E_R110_N.acrarc/E_R110_N.BRTEX#RAS_plusa',
    'LYT/005/Interrupt_E_R040_07.ARC/Interrupt_E_R040_07/timg/Interrupt_E_R040_02_07.tpl#0',
    'LYT/ITEM/GET_061.ARC/ITEM_061_1/timg/ITEM_061_1.tpl#0',
    'PUZZLE/Z071.acrarc/Z071.ARC/lyt/timg/RAS_text08.tpl#0', 'PUZZLE/Z071.acrarc/Z071.ARC/lyt/timg/RAS_text08ap.tpl#0',
    'PUZZLE/Z071.acrarc/Z071.ARC/lyt/timg/RAS_text13.tpl#0', 'PUZZLE/Z071.acrarc/Z071.ARC/lyt/timg/RAS_text13ap.tpl#0',
    'PUZZLE/Z081.acrarc/Z081.BRTEX#memo_n',
    'OBJ/ATC_013/ATC_013_base.brres#RAS3']   # 10/30 제보: 3D 장치 모형 글자 TAS(ITEM/061 과 같은 그림의 사본)


def jp_image_use():
    """JP_IMAGE 자리마다 일본판 그림을 읽어 빌드 결과(없으면 유럽판) 파일의 같은 자리에 넣는다"""
    import texread
    st = Counter()
    for key in (JP_IMAGE if USE_JP_IMAGE else []):
        img = texread.get('jp', key)
        f, inner, i = split_key(key)
        if img is None or not ((OUT / f).exists() or (EUR / f).exists()):
            raise SystemExit(f'일본판 그림 넣기 실패: {key}')
        src = OUT / f if (OUT / f).exists() else EUR / f
        d = open(src, 'rb').read()
        if inner is None:
            d = replace_tex(d, f, i, img, st, True)
        else:
            a = u8.U8(d)
            if inner in a.files():
                a.replace(inner, replace_tex(a.files()[inner], inner, i, img, st, True))
            elif not replace_nested(a, inner, i, img, st):
                raise SystemExit(f'일본판 그림 넣기 실패(묶음 안 대응 없음): {key}')
            d = a.build()
        (OUT / f).parent.mkdir(parents=True, exist_ok=True)
        open(OUT / f, 'wb').write(d)
        st['일본판 그림 사용'] += 1
    return st


def replace_nested(a, inner, i, img, st):
    """inner 가 묶음 안 묶음 경로면(예: 'Z050_01.ARC/lyt/timg/plate01.tpl') 안쪽 U8 을 고쳐 다시 넣는다. 대소문자 무시."""
    files = a.files()
    for p, v in files.items():
        if v[:4] == b'\x55\xAA\x38\x2D' and inner.lower().startswith(p.lower() + '/'):
            sub = u8.U8(v); rest = inner[len(p) + 1:].lower()
            real = next((k for k in sub.files() if k.lower() == rest), None)
            if real is None: return False
            sub.replace(real, replace_tex(sub.files()[real], real, i, img, st, False, fit=True))
            a.replace(p, sub.build())
            return True
    return False


def main():
    idx = json.load(open(GPT / '_목록.json', encoding='utf-8'))
    st = Counter(); rep = defaultdict(list); arcs = {}  # 유럽판 쓸 경로 → U8
    for it in idx:
        img, ruby = image_for(it['png'])
        if ruby: st['후리가나 띠 비움'] += 1
        for key in it['jp_paths']:
            f, inner, i = split_key(key)
            tgt = eu_target(f) if inner else None
            if tgt is None:
                st['유럽판 대응 없음'] += 1; rep['대응 없음'].append(key); continue
            jp_layout = f.startswith('LYT/') and f not in EU_LAYOUT
            if tgt not in arcs:
                arcs[tgt] = u8.load(JPR / f if jp_layout else EUR / tgt)
            a = arcs[tgt]
            if inner not in a.files():
                if replace_nested(a, inner, i, img, st):   # 퍼즐 .acrarc 안의 .ARC 등 묶음 안 묶음
                    st['묶음 안 묶음'] += 1; continue
                st['묶음 안 대응 없음'] += 1; rep['묶음 안 대응 없음'].append(key); continue
            a.replace(inner, replace_tex(a.files()[inner], inner, i, img, st, jp_layout))
            st['영어 폴더' if tgt.startswith('LANG/') else '공용'] += 1
    for tgt, a in arcs.items():
        if tgt in EU_LAYOUT_FILES:
            e = u8.load(EUR / tgt).files()
            for inner in EU_LAYOUT_FILES[tgt]:
                a.replace(inner, e[inner]); st['유럽판 레이아웃 파일로 바꿈'] += 1
        data = merge_eu_only(tgt, a, st)
        (OUT / tgt).parent.mkdir(parents=True, exist_ok=True)
        open(OUT / tgt, 'wb').write(data)
    json.dump(rep, open(paths.WORK / 'insert_tex_report.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    st['묶음'] = len(arcs)
    return st




EUO = paths.ASSETS / 'eu_only'


def glow_mask(img):
    """장 제목 빛번짐 마스크(*ap): 배경색(하늘색)과 다른 픽셀 = 글자 → 3px 부풀림 + 흐림 6 + 밝기 1.3배.
    원본 영어 마스크를 이 방식으로 다시 만들면 평균 오차 8/255 정도(1·3·5·9장 확인)."""
    import numpy as np
    from PIL import ImageFilter
    c = np.asarray(img.convert('RGB'), float); bg = np.median(c.reshape(-1, 3), 0)
    m = ((np.sqrt(((c - bg) ** 2).sum(-1)) > 50) * 255).astype('uint8')
    g = Image.fromarray(m).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(6))
    v = np.clip(np.asarray(g, float) * 1.3, 0, 255).astype('uint8')
    return Image.merge('RGBA', [Image.fromarray(v)] * 3 + [Image.new('L', img.size, 255)])


def eu_only():
    """유럽판 전용 영어 이미지(장 제목·엔딩 이름) + 영어판에만 있는 연구소 층 안내판(DC_R130_02)."""
    idx = json.load(open(EUO / '_목록.json', encoding='utf-8'))['items']
    arcs = {}; n = 0
    jobs = []
    for it in idx:
        p = EUO / it['png']
        if not p.exists(): continue  # 번역 안 하기로 한 것(Chapter N 등)
        f, inner, i = split_key(it['eu_path'])
        img = Image.open(p).convert('RGBA')
        jobs.append((f, inner, i, img))
        if re.search(r'chapter\d+_02\.tpl$', inner):
            jobs.append((f, inner.replace('_02.tpl', '_02ap.tpl'), 0, glow_mask(img)))
    # 연구소 층 안내판: 영어판에만 있는 묶음(LYT/000/DC_R130_R100_*)의 DC_R130_02 = 204호 강조, 「어나더」 제어실 칸 없음.
    # GPT DC_R130_03(204 강조+제어실)에서 제어실 칸만 DC_R100_02(제어실 없음)로 덮어 만든 합성본
    dc = Image.open(EUO / '04_연구소안내판/DC_R130_02.png').convert('RGBA')
    for nm in ('IN', 'OUT', 'loop'):
        jobs.append((f'LANG/ENG/LYT/000/DC_R130_R100_{nm}.ARC', f'DC_R130_R100_{nm}/timg/DC_R130_02.tpl', 0, dc))
    for f, inner, i, img in jobs:
        if f not in arcs:
            arcs[f] = u8.load(OUT / f) if (OUT / f).exists() else u8.load(EUR / f)
        a = arcs[f]
        a.replace(inner, replace_tex(a.files()[inner], inner, i, img, Counter(), True)); n += 1
    for f, a in arcs.items():
        (OUT / f).parent.mkdir(parents=True, exist_ok=True)
        open(OUT / f, 'wb').write(a.build())
    return n, len(arcs)


if __name__ == '__main__':
    print(main())
    print('유럽판 전용', eu_only())
