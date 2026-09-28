"""배포용 xdelta 패치 생성: 한글 ISO 빌드 → xdelta3 패치(유럽판 원본 기준) → 원본에 적용해 결과 검증 → 확인값 출력.
사용: python tools/make_patch.py [버전]        (기본 0.1)"""
import hashlib
import os
import subprocess
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build
import paths

VER = sys.argv[1] if len(sys.argv) > 1 else '0.1'
ISO = paths.WORK / 'AnotherCodeR_KO.iso'
PATCH = paths.RELEASE / f'AnotherCodeR_KO_v{VER}.xdelta'


def digest(path):
    md5, sha1, sha256, crc = hashlib.md5(), hashlib.sha1(), hashlib.sha256(), 0
    with open(path, 'rb') as f:
        while True:
            b = f.read(1 << 24)
            if not b:
                break
            md5.update(b); sha1.update(b); sha256.update(b); crc = zlib.crc32(b, crc)
    return dict(size=os.path.getsize(path), crc32='%08X' % (crc & 0xFFFFFFFF), md5=md5.hexdigest(),
                sha1=sha1.hexdigest(), sha256=sha256.hexdigest())


def run(*cmd):
    subprocess.run(cmd, check=True, cwd=paths.ROOT)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    paths.WORK.mkdir(exist_ok=True); paths.RELEASE.mkdir(exist_ok=True)
    build.main(ISO)
    xd, eu, rel = paths.xdelta3(), paths.eu_iso(), paths.rel  # 상대경로: 패치 헤더에 사용자 폴더명이 남지 않게
    print('[9] xdelta 생성')
    run(xd, '-f', '-e', '-9', '-B', '1073741824', '-s', rel(eu), rel(ISO), rel(PATCH))
    print('[10] 적용 결과 검증')
    check = paths.WORK / 'patched_check.iso'
    run(xd, '-f', '-d', '-s', rel(eu), rel(PATCH), rel(check))
    a, b = digest(ISO), digest(check)
    os.remove(check)
    if a != b:
        raise SystemExit('패치 적용 결과가 빌드 결과와 다릅니다')
    print(f'\n패치: {PATCH} ({PATCH.stat().st_size / 1e6:.2f} MB)')
    for name, d in (('원본 유럽판 ISO', digest(eu)), ('적용 결과', a)):
        print(f"{name}  크기 {d['size']:,} / CRC32 {d['crc32']} / MD5 {d['md5']} / SHA1 {d['sha1']} / SHA256 {d['sha256']}")
