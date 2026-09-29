"""Hold Dungeon Stalkers config files open so the game cannot delete them.

The game deletes Game.ini / Engine.ini / Input.ini on startup.
Holding them open with FILE_SHARE_READ|FILE_SHARE_WRITE but *without*
FILE_SHARE_DELETE makes DeleteFile() fail, so our patches survive a restart.

Run this BEFORE starting the game:
    python keeper.py [config_dir]
Default config_dir = %LOCALAPPDATA%\DungeonStalkers\Saved\Config\Windows
"""

import ctypes
import ctypes.wintypes as wt
import os
import sys
import time

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.CreateFileW.argtypes = [
    wt.LPCWSTR, wt.DWORD, wt.DWORD, wt.LPVOID, wt.DWORD, wt.DWORD, wt.HANDLE
]
k32.CreateFileW.restype = wt.HANDLE
k32.CloseHandle.argtypes = [wt.HANDLE]

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_ALWAYS = 4
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

DEFAULT_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", ""),
    "DungeonStalkers", "Saved", "Config", "Windows",
)

NAMES = ["Game.ini", "Engine.ini", "Input.ini"]


def hold(path):
    if not os.path.exists(path):
        # create it so we can lock an empty file too
        open(path, "a").close()
    h = k32.CreateFileW(
        path,
        GENERIC_READ | GENERIC_WRITE,
        FILE_SHARE_READ | FILE_SHARE_WRITE,   # no FILE_SHARE_DELETE
        None,
        OPEN_ALWAYS,
        0,
        None,
    )
    if h == INVALID_HANDLE_VALUE or h is None:
        print("failed to hold %s (err=%d)" % (path, ctypes.get_last_error()))
        return None
    print("holding open: %s" % path)
    return h


def main():
    cfg = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DIR
    handles = [hold(os.path.join(cfg, n)) for n in NAMES]
    handles = [h for h in handles if h]
    print("keeper alive, %d file(s); the game will not be able to delete them" % len(handles))
    sys.stdout.flush()
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
