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

import shutil

DEFAULT_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", ""),
    "DungeonStalkers", "Saved", "Config", "Windows",
)
SEED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")

NAMES = ["Game.ini", "Engine.ini", "Input.ini"]


k32.SetFileAttributesW.argtypes = [wt.LPCWSTR, wt.DWORD]
k32.SetFileAttributesW.restype = wt.BOOL

FILE_ATTRIBUTE_READONLY = 0x00000001
FILE_ATTRIBUTE_NORMAL = 0x00000080


def hold(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    seed = os.path.join(SEED_DIR, os.path.basename(path))
    if os.path.exists(seed):
        try:
            if os.path.exists(path):
                k32.SetFileAttributesW(path, FILE_ATTRIBUTE_NORMAL)
            shutil.copyfile(seed, path)
            print("restored from config/: %s" % path)
        except OSError as e:
            print("note: could not overwrite %s (%s)" % (path, e))
    elif not os.path.exists(path):
        # create it so we can lock an empty file too
        open(path, "a").close()
    k32.SetFileAttributesW(path, FILE_ATTRIBUTE_READONLY)
    h = k32.CreateFileW(
        path,
        GENERIC_READ,
        FILE_SHARE_READ | FILE_SHARE_WRITE,   # no FILE_SHARE_DELETE; READONLY attribute blocks writes
        None,
        OPEN_ALWAYS,
        0,
        None,
    )
    if h == INVALID_HANDLE_VALUE or h is None:
        print("failed to hold %s (err=%d)" % (path, ctypes.get_last_error()))
        return None
    print("holding open (read-only lock): %s" % path)
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
