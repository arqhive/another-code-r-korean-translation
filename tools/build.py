"""한글 ISO 빌드: 폰트 → 대사(BMG) → 이미지 → 이름표 → 기타 텍스트 → main.dol → 원본 배치 유지 ISO → 검증.
사용: python tools/build.py [출력 ISO] [--quick]   (기본 work/AnotherCodeR_KO.iso, --quick = 시험판: 바뀐 파일만 검증)
유럽판 ISO에 넣지만, 일본판 ISO도 필요하다(일본판 레이아웃 묶음·메시지 구조·main.dol 문자열 위치를 참조)."""
import filecmp
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banner
import font_ko
import homebutton
import inplace
import insert_bmg
import insert_mess
import insert_tex
import nameplate
import patch_dol
import paths

DEFAULT_ISO = paths.WORK / 'AnotherCodeR_KO.iso'


def verify(out_iso, quick=False):
    """결과 ISO 의 DATA 파티션을 풀어 모든 파일을 (빌드 결과가 있으면 그것, 없으면 유럽판 원본)과 비교.
    quick: 시험판용 — 바뀐 파일(work/build)만 꺼내 대조(릴리즈는 전체)"""
    chk = paths.WORK / 'verify'
    if chk.exists():
        shutil.rmtree(chk)
    sel = []
    if quick:
        for dp, _, fs in os.walk(paths.BUILD):
            for f in fs:
                sel += ['--files', '+/' + os.path.relpath(os.path.join(dp, f), paths.BUILD).replace(os.sep, '/')]
    subprocess.run([paths.rel(paths.wit()), 'extract', paths.rel(out_iso), paths.rel(chk), '--psel', 'DATA', '-q', '-o', *sel],
                   check=True, cwd=paths.ROOT)
    n = bad = 0
    for sub in ('files', 'sys'):
        base = chk / sub
        for dp, _, fs in os.walk(base):
            for f in fs:
                rel = os.path.relpath(os.path.join(dp, f), base)
                exp = paths.BUILD / sub / rel
                if not exp.exists():
                    exp = paths.EU / sub / rel
                n += 1
                if not filecmp.cmp(os.path.join(dp, f), exp, shallow=False):
                    bad += 1; print('    다름:', sub, rel)
    shutil.rmtree(chk)
    if bad:
        raise SystemExit(f'검증 실패: {bad}/{n}개 파일이 다릅니다')
    if quick and n != len(sel) // 2:
        raise SystemExit(f'검증 실패: 바뀐 파일 {len(sel) // 2}개 중 {n}개만 ISO 에서 찾음')
    print(f'  검증: {"바뀐 " if quick else ""}파일 {n}개 모두 일치')


def build_files():
    """바뀐 게임 파일을 work/build 에 만든다(ISO 조립 전 단계)."""
    sys.stdout.reconfigure(encoding='utf-8')
    paths.ensure_extracted()
    if paths.BUILD.exists():
        shutil.rmtree(paths.BUILD)
    print('[1] 폰트(한글 2,350자 + 기호)'); font_ko.main()
    print('[2] 대사(BMG)'); print('   ', dict(insert_bmg.main()))
    print('[3] 이미지'); print('   ', dict(insert_tex.main())); print('    유럽판 전용', insert_tex.eu_only())
    print('    일본판 그림 사용(꺼짐: 기계 이름 TAS 통일)', dict(insert_tex.jp_image_use()))
    print('[4] 대화창 이름표'); print('    ', nameplate.main())
    print('    채널 배너', banner.main())
    print('    HOME 메뉴 한국어', homebutton.main())
    print('[5] 기타 텍스트(.MESS 등)'); insert_mess.main()
    print('[6] main.dol'); print('   ', patch_dol.main())


def main(out_iso=DEFAULT_ISO, quick=False):
    build_files()
    print('[7] ISO(원본 배치 유지)'); inplace.main(str(out_iso))
    print('[8] 검증' + (' (시험판: 바뀐 파일만)' if quick else '')); verify(out_iso, quick)
    print('완료:', out_iso)


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if a != '--quick']
    main(args[0] if args else DEFAULT_ISO, '--quick' in sys.argv)
