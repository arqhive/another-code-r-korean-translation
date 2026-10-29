"""유럽판 main.dol 에 한국어 문자열을 넣는다 → work/build/sys/main.dol (크기 불변)
1) GPMESS(획득 문구·장 이름·세이브/오류 문구 136개): dol 안에 5개 언어 사본이 이어져 있다(영어 0x2f3f40~).
   코드(0x8008d6fc~)가 언어 번호로 영어 사본 주소 + 0x1500/0x2b38/0x42e0/0x5a04 를 고르므로 그 더하는 값을 모두 0으로 바꾸고,
   한국어 사본을 영어 자리부터 다섯 칸 전체 공간에 쓴다(모든 언어 → 한국어).
2) 장소 이름 136개: 0x331b08 부터 언어별 목록(개수 + 길이·문자열) 5개가 이어져 있다. 직접 가리키는 주소가 코드에 없어
   앞에서부터 차례로 읽는 것으로 보고, 영어 자리에 한국어 목록을 쓰고 나머지 4개 언어는 빈 문자열 목록으로 줄여 뒤에 잇는다.
   (영어 목록 시작 주소는 그대로. 한국어 목록이 영어 칸보다 커서 제자리 교체는 불가)
번역: translation/ko/main.dol.json(일본판 dol 위치 기준). 일본판 GPMESS 사본 0x2cd4c0, 장소 이름 0x300f78~."""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import insert_mess as M
import paths

JP_GP, JP_GP_LEN = 0x2cd4c0, 0x2aeb
EU_GP = [0x2f3f40, 0x2f5440, 0x2f6a78, 0x2f8220, 0x2f9944]  # 영어·독일어·프랑스어·스페인어·이탈리아어
EU_GP_END = 0x2f9944 + 0x16e6
LANG_ADDI = [0x8008d75c, 0x8008d76c, 0x8008d77c, 0x8008d78c]  # addi r0, r30, <언어별 더하는 값>
EU_MAP = 0x331b08
EU_MAP_END = 0x3362c3
JP_MAP_FROM = 0x300000


def a2f(d, a):
    offs = struct.unpack_from('>18I', d, 0); addrs = struct.unpack_from('>18I', d, 0x48); sizes = struct.unpack_from('>18I', d, 0x90)
    return next(o + a - b for o, b, s in zip(offs, addrs, sizes) if s and b <= a < b + s)


def blob_of(d, start):
    """dol 안 GPMESS 사본(개수 + 위치 표 + 레코드, 레코드 = 문자열 하나) → 정확한 길이로 자른 바이트"""
    n = M.u32(d, start); last = M.u32(d, start + 4 * n)
    return bytes(d[start:start + last + 4 + M.u32(d, start + last)])


def main():
    jd = open(paths.JP / 'sys/main.dol', 'rb').read()
    ed = bytearray(open(paths.EU / 'sys/main.dol', 'rb').read())
    j = json.load(open(paths.KO / 'main.dol.json', encoding='utf-8'))
    # 1) GPMESS
    ko = {}
    for s in j['strings']:
        if JP_GP <= s['offset'] < JP_GP + JP_GP_LEN:
            ko[s['block'] + 4 - JP_GP] = s['ko'].encode('utf-8') + b'\0'
    kb, cnt = M.rebuild(jd[JP_GP:JP_GP + JP_GP_LEN], blob_of(ed, EU_GP[0]), ko)
    room = EU_GP_END - EU_GP[0]
    assert len(kb) <= room, ('GPMESS 공간 부족', len(kb), room)
    ed[EU_GP[0]:EU_GP_END] = kb + b'\0' * (room - len(kb))
    for a in LANG_ADDI:
        p = a2f(ed, a); w = struct.unpack('>I', ed[p:p + 4])[0]
        assert w >> 16 == 0x381e, hex(w)
        struct.pack_into('>I', ed, p, 0x381e0000)
    # 2) 장소 이름
    names = [s for s in sorted(j['strings'], key=lambda s: s['offset']) if s['offset'] >= JP_MAP_FROM]
    assert len(names) == 136 and M.u32(ed, EU_MAP) == 136
    lst = struct.pack('>I', 136) + b''.join(struct.pack('>I', len(b)) + b for b in (s['ko'].encode('utf-8') + b'\0' for s in names))
    empty = struct.pack('>I', 136) + (struct.pack('>I', 1) + b'\0') * 136
    blob = lst + empty * 4
    room = EU_MAP_END - EU_MAP
    assert len(blob) <= room, ('장소 이름 공간 부족', len(blob), room)
    ed[EU_MAP:EU_MAP_END] = blob + b'\0' * (room - len(blob))
    # 3) dol 안 그림 묶음 INIT_DAT(저장 확인·오류 창): 「예/아니요」 버튼 그림을 기본·언어별 6벌 모두 한글로
    n_img = init_dat_images(ed)
    out = paths.BUILD / 'sys/main.dol'; out.parent.mkdir(parents=True, exist_ok=True)
    open(out, 'wb').write(bytes(ed))
    return {'GPMESS 한국어': (cnt, len(kb)), '장소 이름': (len(names), len(lst)), '언어 분기 패치': len(LANG_ADDI),
            'INIT_DAT 그림': n_img}


INIT_DAT = 0x2fb0e0   # 유럽판 dol 파일 위치(U8, 이름 INIT_DAT)
INIT_IMG = {'ICON_DASyesTEXT': '05_DAS_메뉴/058_ICON_DASyesTEXT.png',   # 일본판 MENU.ARC 와 같은 그림·크기(68×24)
            'ICON_DASnoTEXT': '05_DAS_메뉴/057_ICON_DASnoTEXT.png'}
INIT_UP = 2


def init_dat_images(ed):
    """INIT_DAT 안 TPL 자료를 같은 크기·형식으로 제자리 덮어쓴다(dol 크기 불변). 「OK」는 일본판도 영어라 그대로."""
    from PIL import Image
    import gxenc
    import gxtex
    import u8
    fs = u8.U8(bytes(ed[INIT_DAT:])).files(); n = 0; cur = INIT_DAT
    for k, v in fs.items():   # 자료는 노드 순서대로 놓여 있으므로 앞에서부터 차례로 찾는다(같은 그림이 두 벌일 수 있음)
        p = ed.find(v, cur)
        if p >= 0: cur = p + len(v)
        stem = k.split('/')[-1][:-4]
        key = next((b for b in INIT_IMG if stem == b or stem.startswith(b + '_')), None)
        if key is None: continue
        pos = p; assert pos > 0, k
        (i, w, h, f, off, nb, pal), = list(gxtex.tpl_images(v))
        src = Image.open(paths.ASSETS / 'jp' / INIT_IMG[key]).convert('RGBA')
        assert src.size == (w, h), (k, src.size, w, h)
        # 한글 그림은 일본판 기준(글자 세로 중심 12)인데 이 창의 영어 그림은 10.5 → 버튼 안에서 처져 보여(10/30 제보) 2px 올린다
        img = Image.new('RGBA', src.size, (0, 0, 0, 0)); img.paste(src, (0, -INIT_UP))
        data = gxenc.encode(img, f); assert len(data) == nb, (k, len(data), nb)
        ed[pos + off:pos + off + nb] = data; n += 1
    return n


if __name__ == '__main__':
    print(main())
