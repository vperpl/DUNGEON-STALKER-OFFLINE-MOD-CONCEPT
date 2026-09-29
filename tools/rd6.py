import ctypes, ctypes.wintypes as wt, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
k32=ctypes.WinDLL('kernel32',use_last_error=True)
k32.OpenProcess.argtypes=[wt.DWORD,wt.BOOL,wt.DWORD]; k32.OpenProcess.restype=wt.HANDLE
k32.ReadProcessMemory.argtypes=[wt.HANDLE,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)]; k32.ReadProcessMemory.restype=wt.BOOL
PID=23728
CTRL=0x6c4a5d40; PAWN=0x15e300040; GI=0x14f3313c0; HUD=0x1552195b0; PIN=0x14e7e1210
H=k32.OpenProcess(0x0010|0x0400,False,PID)
def rd(a,n):
    b=ctypes.create_string_buffer(n); g=ctypes.c_size_t(0)
    if not k32.ReadProcessMemory(H,ctypes.c_void_p(a),b,n,ctypes.byref(g)) or g.value<n: return None
    return b.raw
def u8(a): r=rd(a,1); return None if r is None else r[0]
def u32(a): r=rd(a,4); return None if r is None else struct.unpack('<I',r)[0]
def u64(a): r=rd(a,8); return None if r is None else struct.unpack('<Q',r)[0]
def f32(a): r=rd(a,4); return None if r is None else struct.unpack('<f',r)[0]
def fvec(a): r=rd(a,12); return None if r is None else struct.unpack('<3f',r)
def arr(a): p=u64(a); c=u32(a+8); return (p,c)

print('== controller ==')
ic_c=u64(CTRL+0x180); print(' InputComponent =',hex(ic_c or 0))
print(' PlayerInput    =',hex(u64(CTRL+0x428) or 0))
print(' CheatManager   =',hex(u64(CTRL+0x418) or 0))
print(' InactiveStateIC=',hex(u64(CTRL+0x618) or 0))
print(' CurrentTouchIF =',hex(u64(CTRL+0x638) or 0))
print(' bytes 340=%s 4C0=%s 554=%s 620=%s'%(u8(CTRL+0x340),u8(CTRL+0x4C0),u8(CTRL+0x554),u8(CTRL+0x620)))
print(' MyCharacter(0x908)=',hex(u64(CTRL+0x908) or 0))
print(' GameWidget(0x9F4) =',hex(u64(CTRL+0x9F4) or 0))

print('== pawn ==')
ic_p=u64(PAWN+0x180); print(' InputComponent =',hex(ic_p or 0))
print(' Controller     =',hex(u64(PAWN+0x2E0) or 0))
print(' RootComponent  =',hex(u64(PAWN+0x1C0) or 0))
print(' ControlInputVec=',fvec(PAWN+0x2F8))
cm=u64(PAWN+0x338); print(' CharacterMove  =',hex(cm or 0))
if cm:
    print('  MovementMode  =',u8(cm+0x221),'(1=Walking)')
    print('  velocity      =',fvec(cm+0xB8))
    print('  MaxWalkSpeed  =',f32(cm+0x268))
    print('  GravityScale  =',f32(cm+0x188))
    print('  CharacterOwner=',hex(u64(cm+0x180) or 0))

print('== input component arrays ==')
for name,ic in (('ctrlIC',ic_c),('pawnIC',ic_p)):
    if not ic: continue
    print(' %s @%s'%(name,hex(ic)))
    for off in (0xA0,0xB0,0xC0,0xD0,0xE0,0xF0,0x100,0x110,0x120):
        p,c=arr(ic+off)
        print('    +%s -> ptr=%s count=%s'%(hex(off),hex(p or 0),c))

print('== player input ==')
pi=u64(CTRL+0x428)
if pi:
    print(' class ptr =',hex(u64(pi) or 0))
    for off in (0x30,0x38,0x40,0x48,0x50,0x58,0x60,0x68,0x70,0x78,0x80,0x88,0x90,0x98,0xA0,0xA8,0xB0,0xB8,0xC0,0xC8,0xD0,0xD8,0xE0,0xE8,0xF0,0xF8,0x100,0x108,0x110,0x118,0x120,0x128,0x130,0x138,0x140,0x148,0x150,0x158,0x160,0x168,0x170,0x178,0x180):
        p,c=arr(pi+off)
        if p and 0<p<0x7FFFFFFF and c and c<0x10000:
            print('   +%s array ptr=%s count=%s'%(hex(off),hex(p),c))

print('== hud ==')
print(' Canvas   =',hex(u64(HUD+0x300) or 0))
print(' 2B8 bits =',u8(HUD+0x2B8))
print(' 2BC      =',u32(HUD+0x2BC))

print('== game instance 0x1B0-0x2D0 ==')
row=[]
for off in range(0x1B0,0x2D0,8):
    v=u64(GI+off); row.append('%s=%s'%(hex(off),hex(v) if v is not None else 'ERR'))
print(' '+' '.join(row))
