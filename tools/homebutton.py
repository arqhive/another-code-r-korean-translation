"""HOME 메뉴 묶음(files/REVOLUTION/HomeButton2/homeBtn_*.arc)의 메시지 창 버튼 「Yes/No」를 「예/아니요」로.
게임의 저장 확인 창도 이 버튼 그림(tx_msgBtn_00·01, 200×32 I4)을 쓴다. 본체 언어에 따라 묶음을 고르므로
같은 디스크의 한국어 묶음(homeBtn_KOR.arc)에 있는 그림을 나머지 언어 묶음에 그대로 넣는다(크기·형식 같음).
메뉴 글(home.csv)은 본체 글꼴로 그려지고 유럽판 본체 글꼴에는 한글이 없어 건드리지 않는다."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gxtex
import paths
import u8

HBM = 'files/REVOLUTION/HomeButton2'
TEX = ['arc/timg/tx_msgBtn_00.tpl', 'arc/timg/tx_msgBtn_01.tpl']


def main():
    kor = u8.U8(open(paths.EU / HBM / 'homeBtn_KOR.arc', 'rb').read()).files()
    done = {}
    for fn in sorted(os.listdir(paths.EU / HBM)):
        if not (fn.startswith('homeBtn') and fn.endswith('.arc')) or fn == 'homeBtn_KOR.arc':
            continue
        arc = u8.U8(open(paths.EU / HBM / fn, 'rb').read()); fs = arc.files(); n = 0
        for t in TEX:
            if t not in fs or t not in kor:
                continue
            a = [x[:4] for x in gxtex.tpl_images(fs[t])]; b = [x[:4] for x in gxtex.tpl_images(kor[t])]
            assert a == b, (fn, t, a, b)
            if fs[t] != kor[t]:
                arc.replace(t, kor[t]); n += 1
        if n:
            out = paths.BUILD / HBM / fn
            out.parent.mkdir(parents=True, exist_ok=True)
            open(out, 'wb').write(arc.build())
            done[fn] = n
    return done


if __name__ == '__main__':
    print(main())
