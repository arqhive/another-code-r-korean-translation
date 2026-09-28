"""원본 ISO의 배치를 그대로 두고 바뀐 파일만 교체한 ISO를 만든다(배포 xdelta가 작아지도록).
1) wit로 원본을 배치 유지 복호화(work/dec.iso)
2) 바뀐 파일을 원래 자리에 덮어쓴다. 원본보다 커진 파일(문자열 일부, 다시 압축한 .res.gz)은
   파티션 안 빈틈(파일 크기 합 2.4GB, 데이터 공간 4.0GB)으로 옮긴다. FST 의 위치·크기를 고친다.
3) 바뀐 2MB 그룹의 H0/H1/H2 해시를 직접 계산해 기록
4) wit로 암호화(work/R.iso) — 해시는 다시 계산하지 않으므로 3)의 값이 그대로 쓰인다
5) 원본 ISO 복사본에 바뀐 그룹만 R에서 옮기고, H3 표·TMD 해시 갱신 후 가짜 서명
사용: python tools/inplace.py 출력.iso   (work/build 의 파일을 넣는다)
cygwin wit 는 한글이 든 절대경로를 못 읽으므로 ROOT 기준 상대경로로 넘긴다. (돌격 패미컴 워즈 VS 한글 패치의 inplace.py 기반)
어나더 코드 R 주의: 게임이 파일을 32바이트 단위로 읽어 파일 끝 뒤가 0이어야 한다(EU MEMORY.dat 등).
wit copy 로 새로 묶으면 파일이 4바이트 간격으로 붙어 크래시가 나므로 반드시 이 방식으로 빌드한다."""
import hashlib
import os
import shutil
import struct
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths
import wiidisc
from wiidisc import CL, HDR, DATA, GROUP

POFF = 0xF800000
ALIGN = 0x40
sha1 = lambda b: hashlib.sha1(b).digest()


def wit(*args):
    subprocess.run([paths.rel(paths.wit()), *args, '-q'], check=True, cwd=paths.ROOT)


def read_fst(P):
    boot = P.read_data(0, 0x440)
    dol_off, fst_off, fst_size = [v << 2 for v in struct.unpack('>III', boot[0x420:0x42C])]
    fst = bytearray(P.read_data(fst_off, fst_size))
    n = struct.unpack('>I', fst[8:12])[0]; st = n * 12
    ents = {}  # 경로 → FST 항목 번호
    cur = []; ends = []
    for i in range(1, n):
        while ends and i >= ends[-1]:
            ends.pop(); cur.pop()
        e = fst[i * 12:i * 12 + 12]
        no = int.from_bytes(e[1:4], 'big')
        nm = fst[st + no:fst.index(b'\0', st + no)].decode('cp932')  # PUZZLE_MESS１.BMG 등 SJIS 이름
        if e[0]:
            cur.append(nm); ends.append(struct.unpack('>I', e[8:12])[0])
        else:
            ents['/'.join(cur + [nm])] = i
    return dol_off, fst_off, fst, ents


def changed_files():
    out = {}
    root = paths.BUILD / 'files'
    for dp, _, fs in os.walk(root):
        for f in fs:
            p = os.path.join(dp, f)
            out[os.path.relpath(p, root).replace(os.sep, '/')] = p
    return out


def main(out_iso):
    os.chdir(paths.ROOT)
    jp = paths.eu_iso()
    print('  1) 복호화'); wit('copy', paths.rel(jp), 'work/dec.iso', '--psel', 'WHOLE', '--enc', 'DECRYPT', '--overwrite')
    f = open('work/dec.iso', 'r+b'); P = wiidisc.Part(f, POFF)
    dol_off, fst_off, fst, ents = read_fst(P)
    space = (P.data_size // CL) * DATA
    ent = lambda i: struct.unpack('>II', fst[i * 12 + 4:i * 12 + 12])
    # 쓰이는 구간: 시스템 영역(0 ~ FST 끝) + 모든 파일
    used = [(0, fst_off + len(fst))]
    for i in ents.values():
        a, b = ent(i); used.append((a << 2, (a << 2) + b))
    used.sort()
    gaps = []; pos = 0
    for a, b in used:
        if a > pos: gaps.append([pos, a])
        pos = max(pos, b)
    if pos < space: gaps.append([pos, space])
    new = changed_files()
    touched = []  # (데이터 오프셋, 길이)
    moved = 0
    print('  2) 파일 교체:', len(new), '개')
    for rel, src in sorted(new.items()):
        if rel not in ents:  # wit 이 SJIS 이름(PUZZLE_MESS１.BMG 등)을 latin-1 로 풀어 쓴 경우 되돌림
            rel = rel.encode('latin-1', 'ignore').decode('cp932')
        i = ents[rel]; a, b = ent(i); off = a << 2
        d = open(src, 'rb').read()
        if len(d) > b:  # 빈틈으로 옮김(맨 뒤 빈틈부터 — 원본 파일 사이 짧은 틈은 건드리지 않음)
            for g in sorted(gaps, key=lambda g: -g[0]):
                s = (g[0] + ALIGN - 1) // ALIGN * ALIGN
                if g[1] - s >= len(d):
                    off = s; g[0] = s + len(d); break
            else:
                raise SystemExit(f'{rel}: 옮길 빈 공간이 없습니다')
            moved += 1
            P.write_data(off, d); touched.append((off, len(d)))
        else:
            P.write_data(off, d + b'\0' * (b - len(d))); touched.append((off, b))
        struct.pack_into('>II', fst, i * 12 + 4, off >> 2, len(d))
    dolp = paths.BUILD / 'sys' / 'main.dol'
    if dolp.exists():
        dol = open(dolp, 'rb').read()
        assert len(dol) == len(P.read_data(dol_off, len(dol)))
        P.write_data(dol_off, dol); touched.append((dol_off, len(dol)))
    P.write_data(fst_off, bytes(fst)); touched.append((fst_off, len(fst)))
    (paths.BUILD / 'sys').mkdir(parents=True, exist_ok=True)
    open(paths.BUILD / 'sys' / 'fst.bin', 'wb').write(bytes(fst))  # 검증 기준(build.py verify)
    print(f'     제자리 {len(new) - moved}개, 빈틈으로 옮김 {moved}개, FST 갱신')
    groups = set()
    for off, sz in touched:
        for c in range(off // DATA, (off + sz - 1) // DATA + 1):
            groups.add(c // GROUP)
    ncl = P.data_size // CL
    print('  3) 해시 재계산:', len(groups), '그룹')
    h3 = {}
    for g in sorted(groups):
        cls = range(g * GROUP, min((g + 1) * GROUP, ncl))
        h0 = {}
        for c in cls:
            f.seek(P.cluster_pos(c) + HDR); d = f.read(DATA)
            h0[c] = b''.join(sha1(d[i * 0x400:(i + 1) * 0x400]) for i in range(31))
        h1 = {}
        for sg in range(8):
            sub = [c for c in cls if (c - g * GROUP) // 8 == sg]
            h1[sg] = b''.join(sha1(h0[c]) for c in sub).ljust(0xA0, b'\0')
        h2 = b''.join(sha1(h1[sg]) for sg in range(8))
        for c in cls:
            sg = (c - g * GROUP) // 8
            hdr = h0[c] + b'\0' * 0x14 + h1[sg] + b'\0' * 0x20 + h2 + b'\0' * 0x20
            assert len(hdr) == HDR
            f.seek(P.cluster_pos(c)); f.write(hdr)
        h3[g] = sha1(h2)
    f.close()
    print('  4) 암호화'); wit('copy', 'work/dec.iso', 'work/R.iso', '--psel', 'WHOLE', '--enc', 'ENCRYPT', '--overwrite')
    print('  5) 합치기'); shutil.copyfile(jp, out_iso)
    F = open(out_iso, 'r+b'); R = open('work/R.iso', 'rb')
    for g in sorted(groups):
        a = P.cluster_pos(g * GROUP); n = min(GROUP, ncl - g * GROUP) * CL
        R.seek(a); F.seek(a); F.write(R.read(n))
    F.seek(POFF + P.h3_off); H3 = bytearray(F.read(0x18000))
    for g, v in h3.items():
        H3[g * 20:g * 20 + 20] = v
    F.seek(POFF + P.h3_off); F.write(H3)
    # TMD: 콘텐츠 해시 갱신 + 가짜 서명(서명 0, 0x1C8~ 값을 바꿔 SHA1 첫 바이트 00)
    F.seek(POFF + P.tmd_off); tmd = bytearray(F.read(P.tmd_size))
    tmd[0x4:0x104] = b'\0' * 0x100
    tmd[0x1F4:0x208] = sha1(bytes(H3))
    for i in range(1 << 32):
        struct.pack_into('>I', tmd, 0x1C8, i)
        if sha1(bytes(tmd[0x140:]))[0] == 0:
            break
    F.seek(POFF + P.tmd_off); F.write(tmd)
    F.close(); R.close()
    os.remove('work/R.iso'); os.remove('work/dec.iso')


if __name__ == '__main__':
    main(sys.argv[1])
