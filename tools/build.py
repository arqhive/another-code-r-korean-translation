"""한글 ISO 빌드: 폰트 → 대사(BMG) → 이미지 → 이름표 → 기타 텍스트 → main.dol → 원본 배치 유지 ISO → 검증.
사용: python tools/build.py [출력 ISO]      (기본 work/AnotherCodeR_KO.iso)
유럽판 ISO에 넣지만, 일본판 ISO도 필요하다(일본판 레이아웃 묶음·메시지 구조·main.dol 문자열 위치를 참조)."""
import filecmp
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import font_ko
import inplace
import insert_bmg
import insert_mess
import insert_tex
import nameplate
import patch_dol
import paths

DEFAULT_ISO = paths.WORK / 'AnotherCodeR_KO.iso'


def verify(out_iso):
    """결과 ISO 의 DATA 파티션을 풀어 모든 파일을 (빌드 결과가 있으면 그것, 없으면 유럽판 원본)과 비교"""
    chk = paths.WORK / 'verify'
    if chk.exists():
        shutil.rmtree(chk)
    subprocess.run([paths.rel(paths.wit()), 'extract', paths.rel(out_iso), paths.rel(chk), '--psel', 'DATA', '-q', '-o'],
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
    print(f'  검증: 파일 {n}개 모두 일치')


def main(out_iso=DEFAULT_ISO):
    sys.stdout.reconfigure(encoding='utf-8')
    paths.ensure_extracted()
    if paths.BUILD.exists():
        shutil.rmtree(paths.BUILD)
    print('[1] 폰트(한글 2,350자 + 기호)'); font_ko.main()
    print('[2] 대사(BMG)'); print('   ', dict(insert_bmg.main()))
    print('[3] 이미지'); print('   ', dict(insert_tex.main())); print('    유럽판 전용', insert_tex.eu_only())
    print('[4] 대화창 이름표'); print('    ', nameplate.main())
    print('[5] 기타 텍스트(.MESS 등)'); insert_mess.main()
    print('[6] main.dol'); print('   ', patch_dol.main())
    print('[7] ISO(원본 배치 유지)'); inplace.main(str(out_iso))
    print('[8] 검증'); verify(out_iso)
    print('완료:', out_iso)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ISO)
