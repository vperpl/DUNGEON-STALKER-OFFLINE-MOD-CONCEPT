import ctypes, ctypes.wintypes as wt, os, sys, re, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, r'C:\Users\snipe\Desktop\DungeonStalkers_Bypass')
import bypass as B

k32 = B.k32
PAGE_GUARD, PAGE_NOACCESS = 0x100, 0x01
MEM_COMMIT = 0x1000
READABLE = {0x02, 0x04, 0x08, 0x20, 0x40, 0x80}


class MBI(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_size_t), ("AllocationBase", ctypes.c_size_t),
                ("AllocationProtect", wt.DWORD), ("RegionSize", ctypes.c_size_t),
                ("State", wt.DWORD), ("Protect", wt.DWORD), ("Type", wt.DWORD)]


k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.POINTER(MBI), ctypes.c_size_t]
k32.VirtualQueryEx.restype = ctypes.c_size_t

INTEREST = re.compile(rb'(https?://|Content-Type|application/json|Authorization|Bearer |maingate|warehouse|/v\d+/|\.json\b|/api/)', re.I)
PATHLIKE = re.compile(rb'^/[A-Za-z][A-Za-z0-9_\-/\.]{4,60}$')


def harvest(data, out, wide=False):
    step = 2 if wide else 1
    run = bytearray(); start = 0; i = 0; n = len(data)
    while i < n:
        if wide:
            ok = (data[i + 1] if i + 1 < n else 1) == 0 and 32 <= data[i] < 127
            ch = data[i]
        else:
            ok = 32 <= data[i] < 127
            ch = data[i]
        if ok:
            if not run:
                start = i
            run.append(ch)
            i += step
        else:
            if len(run) >= 5:
                out.append(bytes(run))
            run = bytearray()
            i += step
    if len(run) >= 5:
        out.append(bytes(run))


def main():
    pid = int(sys.argv[1])
    h = k32.OpenProcess(B.ACCESS, False, pid)
    if not h:
        print('open failed'); return
    hits = set()
    addr = 0
    mbi = MBI()
    while addr < 0x7FFFFFFFFFFF:
        if not k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
            break
        base, size = mbi.BaseAddress, mbi.RegionSize
        if mbi.State == MEM_COMMIT and (mbi.Protect & 0xFF) in READABLE and not (mbi.Protect & PAGE_GUARD) \
                and size <= 0x4000000:
            buf = (ctypes.c_ubyte * size)()
            got = ctypes.c_size_t(0)
            if k32.ReadProcessMemory(h, ctypes.c_void_p(base), buf, size, ctypes.byref(got)) and got.value:
                raw = bytes(buf[:got.value])
                found = []
                harvest(raw, found, False)
                harvest(raw, found, True)
                for s in found:
                    if INTEREST.search(s):
                        hits.add(s.decode('ascii', 'replace'))
                    elif PATHLIKE.match(s) and b'.' not in s[:3]:
                        hits.add(s.decode('ascii', 'replace'))
        addr = base + size
    out = sys.argv[2]
    with open(out, 'w', encoding='utf-8', errors='replace') as f:
        for s in sorted(hits):
            f.write(s + '\n')
    print('%d hits -> %s' % (len(hits), out))


main()
