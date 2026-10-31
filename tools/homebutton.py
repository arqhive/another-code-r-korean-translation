"""HOME 메뉴(files/REVOLUTION/HomeButton2)를 한국어로.
유럽판 디스크에도 한국어 묶음(homeBtn_KOR.arc)과 CSV 한국어 열이 들어 있다. 본체 언어에 따라 묶음·열을 고르므로
나머지 언어 묶음에 한국어 묶음의 글꼴(arc/font, 한글 포함)과 글자 그림(tx_*)을 그대로 넣고(배치 파일은 언어별로 같음),
home.csv·home_nosave.csv 는 모든 언어 칸을 한국어 칸(마지막 열)으로 채운다(11/01, 위쪽 메뉴가 영어로 나온다는 지적).
처음엔 메시지 창 「Yes/No」 그림(tx_msgBtn_00·01)만 바꿨다 — 게임의 저장 확인 창도 이 그림을 쓴다."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gxtex
import paths
import u8

HBM = 'files/REVOLUTION/HomeButton2'
CSV = ['home.csv', 'home_nosave.csv']
COLS = 10   # 일본어·영어·독일어·프랑스어·스페인어·이탈리아어·네덜란드어·중국어·영어·한국어


def arcs(kor):
    done = {}
    for fn in sorted(os.listdir(paths.EU / HBM)):
        if not (fn.startswith('homeBtn') and fn.endswith('.arc')) or fn == 'homeBtn_KOR.arc':
            continue
        arc = u8.U8(open(paths.EU / HBM / fn, 'rb').read()); fs = arc.files(); n = 0
        for t, data in kor.items():
            if t not in fs or fs[t] == data:
                continue
            assert t.startswith(('arc/timg/tx_', 'arc/font/')), (fn, t)
            if t.endswith('.tpl'):
                a = [x[:4] for x in gxtex.tpl_images(fs[t])]; b = [x[:4] for x in gxtex.tpl_images(data)]
                assert a == b, (fn, t, a, b)
            arc.replace(t, data); n += 1
        if n:
            out = paths.BUILD / HBM / fn
            out.parent.mkdir(parents=True, exist_ok=True)
            open(out, 'wb').write(arc.build())
            done[fn] = n
    return done


def csvs():
    done = {}
    for fn in CSV:
        raw = open(paths.EU / HBM / fn, 'rb').read()
        assert raw[:2] == b'\xfe\xff'
        text = raw[2:].decode('utf-16-be')
        cells = re.findall(r'"([^"]*)"', text)
        assert len(cells) % COLS == 0, (fn, len(cells))
        ko = [cells[i + COLS - 1] for i in range(0, len(cells), COLS)]
        k = iter(range(len(cells)))
        new = re.sub(r'"([^"]*)"', lambda m: '"' + ko[next(k) // COLS] + '"', text)
        assert re.findall(r'"([^"]*)"', new) == [ko[i // COLS] for i in range(len(cells))]
        out = paths.BUILD / HBM / fn
        out.parent.mkdir(parents=True, exist_ok=True)
        open(out, 'wb').write(b'\xfe\xff' + new.encode('utf-16-be'))
        done[fn] = len(ko)
    return done


def main():
    kor = u8.U8(open(paths.EU / HBM / 'homeBtn_KOR.arc', 'rb').read()).files()
    return {'묶음': arcs(kor), 'CSV 줄': csvs()}


if __name__ == '__main__':
    print(main())
