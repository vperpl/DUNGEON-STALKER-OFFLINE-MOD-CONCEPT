import ctypes, ctypes.wintypes as wt, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
k32 = ctypes.WinDLL('kernel32', use_last_error=True)
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]; k32.OpenProcess.restype = wt.HANDLE
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]; k32.ReadProcessMemory.restype = wt.BOOL

PID = int(sys.argv[1]); CTRL = int(sys.argv[2], 16)
H = k32.OpenProcess(0x0010 | 0x0400, False, PID)

def rd(a, n):
    b = ctypes.create_string_buffer(n); g = ctypes.c_size_t(0)
    if not k32.ReadProcessMemory(H, ctypes.c_void_p(a), b, n, ctypes.byref(g)) or g.value < n: return None
    return b.raw

def u64(a): r = rd(a, 8); return None if r is None else struct.unpack('<Q', r)[0]
def i32(a): r = rd(a, 4); return None if r is None else struct.unpack('<i', r)[0]
def u32(a): r = rd(a, 4); return None if r is None else struct.unpack('<I', r)[0]

def wide(a, n):
    r = rd(a, n * 2)
    if r is None: return None
    try:
        return r.decode('utf-16-le', errors='strict').split('\x00')[0]
    except Exception:
        return None

ps = u64(CTRL + 0x2B8)
print('PlayerState =', hex(ps or 0))
if not ps: sys.exit(1)

def probe(tag, base):
    raw = rd(base, 16)
    if raw is None:
        print(tag, 'READ FAIL'); return
    a, b, c, d = struct.unpack('<QQ', raw[:8]) if False else (None,)*4
    q0, q1 = struct.unpack('<QQ', raw)
    print('%s raw = %s | %s' % (tag, raw[:8].hex(), raw[8:].hex()))
    # interpretation A: Data ptr @0, Num @8, Max @0xC  (Dumper TArray order)
    pa = q0; na = u32(base + 8); ma = u32(base + 12)
    print('   A ptr=%s num=%s max=%s -> %r' % (hex(pa), na, ma, wide(pa, min(na, 64)) if pa and 0 < na < 4096 else None))
    # interpretation B: Num @0, Max @4, Data ptr @8
    nb = u32(base); mb = u32(base + 4); pb = q1
    print('   B num=%s max=%s ptr=%s -> %r' % (nb, mb, hex(pb), wide(pb, min(nb, 64)) if pb and 0 < nb < 4096 else None))

probe('PlayerNamePrivate', ps + 0x348)
probe('SavedNetworkAddress', ps + 0x300)
