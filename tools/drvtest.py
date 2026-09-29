import ctypes, ctypes.wintypes as wt, time, subprocess, sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

user32 = ctypes.WinDLL('user32', use_last_error=True)
k32 = ctypes.WinDLL('kernel32', use_last_error=True)

INPUT_MOUSE, INPUT_KEYBOARD = 0, 1
KEYEVENTF_KEYUP = 0x0002
VK_MENU = 0x12

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong),
                ("dwExtraInfo", ctypes.c_size_t)]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long), ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong), ("dwExtraInfo", ctypes.c_size_t)]

class INPUTUNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("union", INPUTUNION)]

def send_key(vk, up=False):
    inp = INPUT(type=INPUT_KEYBOARD)
    inp.union.ki.wVk = vk
    inp.union.ki.dwFlags = KEYEVENTF_KEYUP if up else 0
    return user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

def find_game():
    import ctypes.wintypes as wt2
    procs = []
    for p in (os.popen("tasklist /FI \"IMAGENAME eq DungeonStalkers-Win64-Shipping.exe\" /FO CSV /NH").read().splitlines()):
        parts = [x.strip('"') for x in p.split('","')]
        if len(parts) >= 2 and parts[0].startswith("DungeonStalkers"):
            procs.append(int(parts[1]))
    for pid in procs:
        hwnd = user32.GetTopWindow(None)
        while hwnd:
            q = wt.DWORD(0)
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(q))
            if q.value == pid and user32.IsWindowVisible(hwnd):
                return hwnd, pid
            hwnd = user32.GetWindow(hwnd, 2)  # GW_HWNDNEXT
    return None

def focus(hwnd):
    # ALT-key trick so SetForegroundWindow is allowed
    send_key(VK_MENU); send_key(VK_MENU, True)
    r = user32.SetForegroundWindow(hwnd)
    time.sleep(0.4)
    if user32.GetForegroundWindow() != hwnd:
        user32.ShowWindow(hwnd, 6)  # minimize
        time.sleep(0.3)
        user32.ShowWindow(hwnd, 9)  # restore
        send_key(VK_MENU); send_key(VK_MENU, True)
        r = user32.SetForegroundWindow(hwnd)
        time.sleep(0.4)
    return user32.GetForegroundWindow() == hwnd

def shot(name):
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), name)
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", os.path.join(os.path.dirname(os.path.abspath(__file__)), "shot.ps1"),
                    "-ProcId", str(GPID), "-Out", out],
                   capture_output=True)
    return out

def diff(a, b):
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                        "-File", os.path.join(os.path.dirname(os.path.abspath(__file__)), "diff.ps1"),
                        "-A", a, "-B", b], capture_output=True, text=True)
    return (r.stdout + r.stderr).strip()

G = find_game()
if not G:
    print("NO GAME WINDOW")
    sys.exit(1)
GH, GPID = G
print("game hwnd=%s pid=%s" % (hex(GH), GPID))
print("focused:", focus(GH))

# --- mouse look test ---
shot("d_before.png")
user32.SetCursorPos(0, 0)
time.sleep(0.2)
user32.SetCursorPos(2500, 0)
time.sleep(0.8)
shot("d_mouse.png")
print("mouse diff:", diff(os.path.join(os.path.dirname(os.path.abspath(__file__)), "d_before.png"),
                          os.path.join(os.path.dirname(os.path.abspath(__file__)), "d_mouse.png")))

# --- WASD test ---
print("focused2:", focus(GH))
send_key(ord('W'))
time.sleep(2.0)
send_key(ord('W'), True)
time.sleep(0.5)
shot("d_w.png")
print("W diff:", diff(os.path.join(os.path.dirname(os.path.abspath(__file__)), "d_mouse.png"),
                      os.path.join(os.path.dirname(os.path.abspath(__file__)), "d_w.png")))

send_key(ord('D'))
time.sleep(2.0)
send_key(ord('D'), True)
time.sleep(0.5)
shot("d_d.png")
print("D diff:", diff(os.path.join(os.path.dirname(os.path.abspath(__file__)), "d_w.png"),
                      os.path.join(os.path.dirname(os.path.abspath(__file__)), "d_d.png")))
