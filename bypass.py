import ctypes, ctypes.wintypes as wt, time, subprocess, os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
user32 = ctypes.WinDLL('user32', use_last_error=True)
ACCESS = 0x0400 | 0x0010 | 0x0008 | 0x0020
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.OpenProcess.restype = wt.HANDLE
k32.VirtualProtectEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wt.DWORD, ctypes.POINTER(wt.DWORD)]
k32.VirtualProtectEx.restype = wt.BOOL
k32.WriteProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.WriteProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.ReadProcessMemory.restype = wt.BOOL
k32.FlushInstructionCache.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t]
k32.FlushInstructionCache.restype = wt.BOOL
k32.CloseHandle.argtypes = [wt.HANDLE]

_HERE = os.path.dirname(os.path.abspath(__file__))
_REL_EXE = r"DungeonStalkers\Binaries\Win64\DungeonStalkers-Win64-Shipping.exe"
EXE = (
    os.path.join(_HERE, _REL_EXE)
    if os.path.exists(os.path.join(_HERE, _REL_EXE))
    else os.path.join(os.path.dirname(_HERE), _REL_EXE)
)

# nProtect GameGuard bypass (DungeonStalkers 1.8.05 / build 22811395)
# 1) fake the GameGuard result code so the "GameGuard Init failed" branch is never taken
# 2) stop the subsystem marking itself failed
# 3) clear the global "GG failed" flag
# 4) belt-and-braces: neutralise the two MessageBoxW calls that draw the error dialog
PATCHES = [
    (0x14507be39, b'\xe8',              b'\xb8\x55\x07\x00\x00',    "fake clean GG result (1877)"),
    (0x14507bd84, b'\xc6\x41\x38\x01',  b'\xc6\x41\x38\x00',        "subsystem failed-flag = 0"),
    (0x14507bf36, b'\xc6\x05\x73\x7c\xef\x04\x01', b'\xc6\x05\x73\x7c\xef\x04\x00', "global GG-failed flag = 0"),
    (0x14507bf80, b'\xff\x15\xb2\x16\x79\x02', b'\x90' * 6,         "NOP MessageBoxW (error dialog)"),
    (0x1450753a3, b'\xff\x15\x8f\x82\x79\x02', b'\x90' * 6,         "NOP MessageBoxW (alt dialog)"),
]


def readat(h, addr, n):
    buf = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t(0)
    ok = k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, n, ctypes.byref(got))
    return buf.raw[:got.value] if ok and got.value else b''


def writeat(h, addr, data):
    old = wt.DWORD(0)
    if not k32.VirtualProtectEx(h, ctypes.c_void_p(addr), len(data), 0x40, ctypes.byref(old)):
        return False
    n = ctypes.c_size_t(0)
    k32.WriteProcessMemory(h, ctypes.c_void_p(addr), ctypes.create_string_buffer(data), len(data), ctypes.byref(n))
    k32.VirtualProtectEx(h, ctypes.c_void_p(addr), len(data), old.value, ctypes.byref(wt.DWORD(0)))
    k32.FlushInstructionCache(h, ctypes.c_void_p(addr), len(data))
    return True


def windows_of(pid):
    out = []
    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(hwnd, lparam):
        wpid = wt.DWORD(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
        if wpid.value != pid:
            return True
        n = user32.GetWindowTextLengthW(hwnd)
        if n > 0:
            b = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, b, n + 1)
            if b.value.strip():
                out.append(b.value)
        return True
    user32.EnumWindows(cb, 0)
    return out


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD),
        ("cntUsage", wt.DWORD),
        ("th32ProcessID", wt.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wt.DWORD),
        ("cntThreads", wt.DWORD),
        ("th32ParentProcessID", wt.DWORD),
        ("pcPriClassBase", wt.LONG),
        ("dwFlags", wt.DWORD),
        ("szExeFile", ctypes.c_wchar * 260),
    ]


def live_pids():
    """All running DungeonStalkers-Win64-Shipping.exe pids (Toolhelp32 snapshot)."""
    TH32CS_SNAPPROCESS = 0x00000002
    INVALID = ctypes.c_void_p(-1).value
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap in (None, INVALID):
        return []
    out = []
    try:
        pe = PROCESSENTRY32W()
        pe.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        if k32.Process32FirstW(snap, ctypes.byref(pe)):
            while True:
                if pe.szExeFile.lower() == 'dungeonstalkers-win64-shipping.exe':
                    out.append(pe.th32ProcessID)
                if not k32.Process32NextW(snap, ctypes.byref(pe)):
                    break
    finally:
        k32.CloseHandle(snap)
    return out


def patch_process(pid):
    """Apply every GameGuard patch we can. Returns number newly applied."""
    h = k32.OpenProcess(ACCESS, False, pid)
    if not h:
        return -1
    applied = 0
    try:
        for addr, expect, new, name in PATCHES:
            if readat(h, addr, len(new)).startswith(expect) and writeat(h, addr, new):
                applied += 1
    finally:
        k32.CloseHandle(h)
    return applied


import shutil
import keeper


def kill_existing():
    PROCESS_TERMINATE = 0x0001
    k32.TerminateProcess.argtypes = [wt.HANDLE, wt.UINT]
    k32.TerminateProcess.restype = wt.BOOL
    pids = live_pids()
    if pids:
        print("Closing existing Dungeon Stalkers process(es):", pids)
        for pid in pids:
            h = k32.OpenProcess(PROCESS_TERMINATE, False, pid)
            if h:
                k32.TerminateProcess(h, 0)
                k32.CloseHandle(h)
        time.sleep(1.5)


def focus_game_window(pid):
    target = []
    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(hwnd, lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        wpid = wt.DWORD(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
        if wpid.value == pid:
            n = user32.GetWindowTextLengthW(hwnd)
            if n > 0:
                b = ctypes.create_unicode_buffer(n + 1)
                user32.GetWindowTextW(hwnd, b, n + 1)
                if 'Dungeon' in b.value:
                    target.append(hwnd)
        return True
    user32.EnumWindows(cb, 0)
    if target:
        hwnd = target[0]
        user32.keybd_event(0x12, 0, 0, 0)
        user32.keybd_event(0x12, 0, 0x0002, 0)
        user32.ShowWindow(hwnd, 9)
        user32.SetForegroundWindow(hwnd)


def inject_driver(child_pid):
    src_dll = os.path.join(_HERE, "bin", "Dumper-7.dll")
    dst_dll = os.path.join(os.path.dirname(EXE), "Dumper-7.dll")
    dll_path = dst_dll if os.path.exists(dst_dll) else src_dll
    if os.path.exists(src_dll):
        try:
            shutil.copyfile(src_dll, dst_dll)
            dll_path = dst_dll
        except OSError:
            pass
    if not os.path.exists(dll_path):
        print("WARNING: Dumper-7.dll not found at", dll_path)
        return
    inject_py = os.path.join(_HERE, "Tools", "inject.py")
    print("Injecting %s into child pid %d ..." % (os.path.basename(dll_path), child_pid))
    subprocess.run([sys.executable, inject_py, str(child_pid), dll_path])
    time.sleep(1.5)
    focus_game_window(child_pid)
    log_path = os.path.join(_HERE, "Tools", "inj.log")
    for _ in range(10):
        if os.path.exists(log_path) and os.path.getsize(log_path) > 0:
            break
        time.sleep(0.5)
    if os.path.exists(log_path):
        print("--- Tools/inj.log ---")
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f.read().splitlines()[-8:]:
                print(" ", line)


def main():
    if not os.path.exists(EXE):
        print("ERROR: game not found at", EXE)
        return 1

    kill_existing()

    print("Restoring & locking offline config files ...")
    handles = [keeper.hold(os.path.join(keeper.DEFAULT_DIR, n)) for n in keeper.NAMES]
    handles = [h for h in handles if h]

    print("Starting Dungeon Stalkers ...")
    proc = subprocess.Popen([EXE], cwd=os.path.dirname(EXE))
    print("  pid", proc.pid)

    done = set()
    counts = {}
    start = time.time()
    last_report = 0.0
    win_seen_at = None

    # nEOS (Epic emulator) relaunches the game, and GameGuard unpacks ~1.5s in,
    # so keep patching every game process that shows up until both parent & child are clean.
    while time.time() - start < 45:
        for pid in live_pids():
            if pid in done:
                continue
            n = patch_process(pid)
            if n > 0:
                counts[pid] = counts.get(pid, 0) + n
            if counts.get(pid, 0) >= len(PATCHES):
                done.add(pid)
                print("  GameGuard bypass applied to pid %d" % pid)
            elif time.time() - last_report > 2:
                last_report = time.time()
                print("  pid %d: %d/%d patched, retrying ..." % (pid, counts.get(pid, 0), len(PATCHES)))

        win_pids = [pid for pid in done if any('Dungeon' in w for w in windows_of(pid))]
        if win_pids:
            if win_seen_at is None:
                win_seen_at = time.time()
                print("  window detected (child pid: %d), continuing patch watch ..." % win_pids[-1])
            elif time.time() - win_seen_at >= 3.0:
                child_pid = win_pids[-1]
                print("\nGameGuard bypass active! (window child pid: %d)" % child_pid)
                print("IMPORTANT: Wait until the 3D tutorial level finishes loading on screen")
                print("           (past the black startup screen and loading screen).")
                try:
                    input("Press ENTER once you see your character in the level to inject the input driver...")
                except EOFError:
                    pass
                win_pids = [pid for pid in live_pids() if any('Dungeon' in w for w in windows_of(pid))]
                if win_pids:
                    child_pid = win_pids[-1]
                inject_driver(child_pid)
                print("\nOffline driver injected! Keep this window open while playing (holds config lock).")
                print("Hotkeys in-game: WASD=Move | Mouse=Look | Space=Jump | F1=Toggle Driver | F6=Unload")
                try:
                    input("\nPress ENTER here when you are done playing to exit...")
                except EOFError:
                    pass
                return 0
        time.sleep(0.25)

    if done:
        print("GameGuard bypass applied (window not confirmed yet).")
        return 0
    print("ERROR: nothing was patched - game may have been updated.")
    return 1


if __name__ == '__main__':
    rc = main()
    if rc:
        os.system('pause')
    sys.exit(rc)
