import ctypes, ctypes.wintypes as wt, sys, struct, time, threading, subprocess
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
k32 = ctypes.WinDLL('kernel32', use_last_error=True)
u32 = ctypes.WinDLL('user32', use_last_error=True)
k32.OpenProcess.argtypes=[wt.DWORD, wt.BOOL, wt.DWORD]; k32.OpenProcess.restype=wt.HANDLE
k32.ReadProcessMemory.argtypes=[wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.ReadProcessMemory.restype=wt.BOOL

PID=int(sys.argv[1]) if len(sys.argv)>1 else 23728
PAWN=int(sys.argv[2],16) if len(sys.argv)>2 else 0x15e300040

class KEYBDINPUT(ctypes.Structure):
    _fields_=[('wVk',wt.WORD),('wScan',wt.WORD),('dwFlags',wt.DWORD),('dwTime',wt.DWORD),('dwExtraInfo',ctypes.c_size_t)]
class MOUSEINPUT(ctypes.Structure):
    _fields_=[('dx',ctypes.c_long),('dy',ctypes.c_long),('mouseData',wt.DWORD),('dwFlags',wt.DWORD),('dwTime',wt.DWORD),('dwExtraInfo',ctypes.c_size_t)]
class _U(ctypes.Union):
    _fields_=[('ki',KEYBDINPUT),('mi',MOUSEINPUT)]
class INPUT(ctypes.Structure):
    _anonymous_=('u',)
    _fields_=[('type',wt.DWORD),('u',_U)]
print('sizeof(INPUT)=%d (expect 40)  KEYBDINPUT=%d  MOUSEINPUT=%d' % (ctypes.sizeof(INPUT), ctypes.sizeof(KEYBDINPUT), ctypes.sizeof(MOUSEINPUT)))
u32.SendInput.argtypes=[wt.UINT, ctypes.POINTER(INPUT), ctypes.c_int]; u32.SendInput.restype=wt.UINT

def key(vk, up=False):
    i=INPUT(); i.type=1; i.ki.wVk=vk; i.ki.dwFlags=0x0002 if up else 0
    return u32.SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))
def move(dx,dy):
    i=INPUT(); i.type=0; i.mi.dx=dx; i.mi.dy=dy; i.mi.dwFlags=0x0001
    return u32.SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))

# focus the game window, hide any other window of this process
ENUMPROC=ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
u32.EnumWindows.argtypes=[ENUMPROC, wt.LPARAM]; u32.EnumWindows.restype=wt.BOOL
u32.IsWindowVisible.argtypes=[wt.HWND]; u32.IsWindowVisible.restype=wt.BOOL
u32.GetWindowTextW.argtypes=[wt.HWND, wt.LPWSTR, ctypes.c_int]
u32.GetWindowRect.argtypes=[wt.HWND, ctypes.POINTER(wt.RECT)]
u32.BringWindowToTop.argtypes=[wt.HWND]
u32.SetForegroundWindow.argtypes=[wt.HWND]; u32.SetForegroundWindow.restype=wt.BOOL
u32.ShowWindow.argtypes=[wt.HWND, ctypes.c_int]
u32.GetForegroundWindow.restype=wt.HWND
u32.SetCursorPos.argtypes=[ctypes.c_int, ctypes.c_int]
wins=[]
def cb(h,l):
    p=wt.DWORD(0); u32.GetWindowThreadProcessId(h, ctypes.byref(p))
    if p.value==PID and u32.IsWindowVisible(h):
        n=ctypes.create_unicode_buffer(512); u32.GetWindowTextW(h,n,512)
        r=wt.RECT(); u32.GetWindowRect(h,ctypes.byref(r)); wins.append((h,n.value,(r.left,r.top,r.right,r.bottom)))
    return True
u32.EnumWindows(ENUMPROC(cb),0)
game=None
for h,t,r in wins:
    print('  hwnd=%d title=%r rect=%s'%(h,t,r))
    if t.startswith('DungeonStalkers'): game=h
    elif t: u32.ShowWindow(h,0); print('     hid (focus thief)')
if not game: print('NO GAME WINDOW'); sys.exit(1)
u32.ShowWindow(game,9); u32.BringWindowToTop(game)
print('foreground ->', bool(u32.SetForegroundWindow(game)))
u32.GetForegroundWindow.restype=wt.HWND
if u32.GetForegroundWindow()!=game:
    # ALT key trick: makes the calling thread's next SetForegroundWindow legal
    u32.keybd_event.argtypes=[wt.BYTE,wt.BYTE,wt.DWORD,ctypes.c_size_t]
    u32.keybd_event(0x12,0,0,0); u32.keybd_event(0x12,0,0x0002,0)
    time.sleep(0.1)
    print('foreground (alt trick) ->', bool(u32.SetForegroundWindow(game)))
if u32.GetForegroundWindow()!=game:
    u32.ShowWindow(game,6); time.sleep(0.2)
    u32.ShowWindow(game,9); u32.BringWindowToTop(game)
    print('foreground (min/restore) ->', bool(u32.SetForegroundWindow(game)))
time.sleep(0.3)
print('foreground hwnd =', u32.GetForegroundWindow(), 'game', game)
u32.SetCursorPos(1280,720)

H=k32.OpenProcess(0x0010|0x0400,False,PID)
def vec(a):
    b=ctypes.create_string_buffer(12); g=ctypes.c_size_t(0)
    if not k32.ReadProcessMemory(H,ctypes.c_void_p(a),b,12,ctypes.byref(g)) or g.value<12: return None
    return struct.unpack('<3f', b.raw[:12])
def shot(name):
    subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',
        r'C:\Users\snipe\Desktop\DungeonStalkers_Bypass\tools\shot.ps1','-ProcId',str(PID),
        '-Out',r'C:\Users\snipe\Desktop\DungeonStalkers_Bypass\tools\%s.png'%name], capture_output=True)

samples=[]; stop=False
def sampler():
    while not stop:
        samples.append((time.time(), vec(PAWN+0x2F8)))
        time.sleep(0.015)
th=threading.Thread(target=sampler,daemon=True); th.start()
time.sleep(0.2)
shot('b_real')

print('SendInput W down =', key(0x57))
time.sleep(2.0)
print('SendInput W up   =', key(0x57, True))
time.sleep(0.3)
print('SendInput mouse  =', sum(1 for _ in range(40) if move(20,0)))
time.sleep(1.0)
stop=True; th.join(timeout=1)

nz=[s for s in samples if s[1] and any(abs(v)>0.001 for v in s[1])]
print('samples=%d nonzero=%d'%(len(samples), len(nz)))
for ts,v in (nz[:10] if nz else samples[::max(1,len(samples)//6)]):
    print('   ', round(ts,3), v)
shot('a_real')
print('done')
