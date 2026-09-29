import ctypes, ctypes.wintypes as wt, sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.OpenProcess.restype = wt.HANDLE
k32.VirtualAllocEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wt.DWORD, wt.DWORD]
k32.VirtualAllocEx.restype = ctypes.c_void_p
k32.WriteProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.WriteProcessMemory.restype = wt.BOOL
k32.CreateRemoteThread.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p, wt.DWORD, wt.LPDWORD]
k32.CreateRemoteThread.restype = wt.HANDLE
k32.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
k32.WaitForSingleObject.restype = wt.DWORD
k32.GetExitCodeThread.argtypes = [wt.HANDLE, wt.LPDWORD]
k32.GetExitCodeThread.restype = wt.BOOL
k32.GetModuleHandleW.argtypes = [wt.LPCWSTR]
k32.GetModuleHandleW.restype = ctypes.c_void_p
k32.GetProcAddress.argtypes = [ctypes.c_void_p, wt.LPCSTR]
k32.GetProcAddress.restype = ctypes.c_void_p
k32.CloseHandle.argtypes = [wt.HANDLE]

ACCESS = 0x0002 | 0x0008 | 0x0010 | 0x0020 | 0x0040 | 0x0400


def inject(pid, dll):
    h = k32.OpenProcess(ACCESS, False, pid)
    if not h:
        return 'OpenProcess failed err=%d' % ctypes.get_last_error()
    buf = ctypes.create_unicode_buffer(dll)
    size = ctypes.sizeof(buf)
    p = k32.VirtualAllocEx(h, None, size, 0x3000, 0x04)
    if not p:
        return 'VirtualAllocEx failed err=%d' % ctypes.get_last_error()
    written = ctypes.c_size_t(0)
    if not k32.WriteProcessMemory(h, p, buf, size, ctypes.byref(written)):
        return 'WriteProcessMemory failed err=%d' % ctypes.get_last_error()
    kh = k32.GetModuleHandleW('kernel32.dll')
    loadlib = k32.GetProcAddress(kh, b'LoadLibraryW')
    if not loadlib:
        return 'GetProcAddress(LoadLibraryW) failed'
    th = k32.CreateRemoteThread(h, None, 0, loadlib, p, 0, None)
    if not th:
        return 'CreateRemoteThread failed err=%d' % ctypes.get_last_error()
    wr = k32.WaitForSingleObject(th, int(sys.argv[3]) if len(sys.argv) > 3 else 15000)
    code = wt.DWORD(0)
    k32.GetExitCodeThread(th, ctypes.byref(code))
    k32.CloseHandle(th)
    k32.CloseHandle(h)
    out = 'wait=0x%x exit=0x%x' % (wr, code.value)
    if wr == 0x102:
        return out + ' -> TIMEOUT (thread still running)'
    if code.value == 0:
        return out + ' -> LoadLibraryW returned NULL'
    return out + ' -> OK'


if __name__ == '__main__':
    pid = int(sys.argv[1])
    dll = sys.argv[2]
    print(inject(pid, dll))
