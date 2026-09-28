"""(개발용) 유럽판 main.dol 역어셈블: python tools/ppcdis.py <시작 주소 16진> <명령 수>. capstone 필요."""
import struct, sys
import capstone
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import paths
d = open(paths.EU / 'sys/main.dol', 'rb').read()
offs = struct.unpack_from('>18I', d, 0); addrs = struct.unpack_from('>18I', d, 0x48); sizes = struct.unpack_from('>18I', d, 0x90)
def a2f(a):
    for o, b, s in zip(offs, addrs, sizes):
        if b <= a < b + s: return o + a - b
md = capstone.Cs(capstone.CS_ARCH_PPC, capstone.CS_MODE_32 | capstone.CS_MODE_BIG_ENDIAN)
s = int(sys.argv[1], 16); n = int(sys.argv[2]); f = a2f(s)
for i in range(n):
    w = d[f + i * 4:f + i * 4 + 4]; ins = list(md.disasm(w, s + i * 4))
    print(hex(s + i * 4), w.hex(), (ins[0].mnemonic + ' ' + ins[0].op_str) if ins else '??')
