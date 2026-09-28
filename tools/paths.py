"""저장소 안팎 경로와 외부 도구 위치(어느 폴더에서 실행해도 같게 동작)."""
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / 'tools'
DATA = TOOLS / 'data'                 # 이름표 이름 등 보조 자료
ASSETS = TOOLS / 'assets'             # 한글화 이미지(jp: 일본판 그림 대응, eu_only: 유럽판 전용 그림 대응)
TRANS = ROOT / 'translation'
KO = TRANS / 'ko'                     # 번역 JSON(번역문과 위치 키만)
RELEASE = ROOT / 'release'
DOCS = ROOT / 'docs'
WORK = ROOT / 'work'                  # 추출본·빌드 결과·원문 대조본 등 커밋하지 않는 작업 폴더
EU = WORK / 'eu'                      # 유럽판 DATA 파티션 추출본(wit extract): files/, sys/
JP = WORK / 'jp'                      # 일본판 DATA 파티션 추출본(레이아웃·원문 구조 참조용)
BUILD = WORK / 'build'                # 바뀐 파일만 모아 두는 곳(files/…, sys/main.dol)
EU_ISO_NAME = 'Another Code - R [RNOP01].iso'
JP_ISO_NAME = 'Another Code - R [RNOJ01].iso'


def _find(env, name):
    p = os.environ.get(env)
    if p:
        return Path(p)
    for d in (ROOT, ROOT / 'iso', ROOT.parent):
        if (d / name).exists():
            return d / name
    for d in ROOT.iterdir():  # 저장소 루트 아래 한 단계 폴더(덤프 폴더째 둔 경우)
        if d.is_dir() and (d / name).exists():
            return d / name
    return None


def eu_iso():
    p = _find('ACR_EU_ISO', EU_ISO_NAME)
    if not p:
        raise SystemExit(f'유럽판 ISO를 찾을 수 없습니다. 저장소 루트(또는 바로 아래 폴더)에 "{EU_ISO_NAME}"를 두거나 환경 변수 ACR_EU_ISO로 지정하세요.')
    return p


def jp_iso():
    p = _find('ACR_JP_ISO', JP_ISO_NAME)
    if not p:
        raise SystemExit(f'일본판 ISO를 찾을 수 없습니다. 저장소 루트(또는 바로 아래 폴더)에 "{JP_ISO_NAME}"를 두거나 환경 변수 ACR_JP_ISO로 지정하세요.')
    return p


def tool(env, exe, local):
    """외부 도구: 환경 변수 → tools/bin → PATH."""
    for p in (os.environ.get(env), TOOLS / 'bin' / Path(*local)):
        if p and Path(p).is_file():
            return str(p)
    p = shutil.which(exe)
    if p:
        return p
    raise SystemExit(f'{exe}를 찾을 수 없습니다. tools/bin 이나 PATH에 두거나 환경 변수 {env}로 지정하세요.')


def wit():
    return tool('WIT', 'wit', ('wit-v3.05a-r8638-cygwin64', 'bin', 'wit.exe'))


def xdelta3():
    return tool('XDELTA3', 'xdelta3', ('xdelta3.exe',))


def rel(p):
    """cygwin wit 는 한글이 든 절대경로를 못 읽고, xdelta 헤더에 사용자 폴더명이 남지 않도록 ROOT 기준 상대경로로"""
    return os.path.relpath(str(p), str(ROOT))


def ensure_extracted():
    """work/eu, work/jp 가 없으면 두 ISO 의 DATA 파티션을 푼다(wit extract)."""
    for out, iso in ((EU, eu_iso), (JP, jp_iso)):
        if not (out / 'files/REVOLUTION').exists():
            print(f'{out.name} 추출 중… ({rel(out)})')
            subprocess.run([rel(wit()), 'extract', rel(iso()), rel(out), '--psel', 'DATA', '-q', '-o'], check=True, cwd=ROOT)
