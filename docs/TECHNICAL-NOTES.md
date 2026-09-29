# Dungeon Stalkers — offline / single-player checkpoint

**Checkpoint date:** 2026-09-29 15:40 (game build `1.8.05.LIVE`, appid 2468730)
**Known-good state:** boots straight into `L_Tutorial`, character walks, camera looks,
jump works, HUD + minimap are alive.

This is a snapshot so nothing gets lost if a future change breaks it.

---

## 1. Status

### Works
| Thing | How |
|---|---|
| GameGuard bypass | `bypass.py` — 5 byte patches |
| Boot straight into a playable map | `Engine.ini` `GameDefaultMap=/Game/Maps/Tutorial/L_Tutorial.L_Tutorial` |
| **Move** (WASD) | injected driver writes `CharacterMovement->Velocity` at `cm+0xB8` |
| **Camera look** | injected driver writes `AController::ControlRotation` at `ctrl+0x328` |
| **Jump** (Space) | `ProcessEvent(ACharacter::Jump)` |
| Map switch / restart | **F8** re-opens the map named in `tools/map.txt` |
| Diagnostics | **F9** |

### Not working yet
* Native UE input bindings are **dead** — `AWSCharacterPlayer::InitInputActionBinding()`
  is never called by our flow, so the game's own keys (attack, interact, crouch,
  sprint, inventory) do nothing. The driver only emulates move/look/jump.
* `L_TrainingGround` crashes (AV at `0x100`). Runtime `open` of non-tutorial maps
  (Hideout, Prison) loads a bare world with no pawn/HUD and then the child dies.
* No maingate/login — `[BigAccount] bEnable=False` so the title/login screens appear
  but never get past "Zaloguj się". Tutorial map bypasses this entirely.
* No UE log (`Saved/Logs/` only has `cef3*.log`).

---

## 2. Quick start

```powershell
# 0) once: config keeper must run BEFORE the game (stops the game deleting our .ini)
python keeper.py

# 1) optional: log maingate/HTTP traffic to read the API contract
python stub.py 80 8080

# 2) launch the game with the GameGuard bypass
powershell -NoProfile -ExecutionPolicy Bypass -File ".\Start Dungeon Stalkers.bat"
#    -> prints two pids; the one with MainWindowHandle != 0 is the real game

# 3) build the DLL (only needed after editing main.cpp)
& "C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe" `
   ".\Dumper-7-main\Dumper\Dumper.vcxproj" `
   /p:Configuration=Release /p:Platform=x64 /p:PlatformToolset=v143 /v:m /nologo

# 4) stop the game, copy the DLL, verify, relaunch
Copy-Item ".\Dumper-7-main\Dumper\x64\Release\Dumper-7.dll" `
          "D:\SteamLibrary\steamapps\common\Dungeon Stalkers\DungeonStalkers\Binaries\Win64\Dumper-7.dll" -Force

# 5) inject into the CHILD pid (the one that owns the window)
python .\tools\inject.py <child_pid> "D:\SteamLibrary\steamapps\common\Dungeon Stalkers\DungeonStalkers\Binaries\Win64\Dumper-7.dll"

# 6) wait ~40s, then read the log
Get-Content .\tools\inj.log
```

Kill leftovers before every launch — **only** by exact name:
```powershell
Get-Process DungeonStalkers-Win64-Shipping -ErrorAction SilentlyContinue | Stop-Process -Force
```

---

## 3. Hotkeys (implemented in `Dumper-7-main/Dumper/main.cpp`)

| Key | Action |
|---|---|
| **F1** | toggle the input driver on/off |
| **F6** | unload the DLL (frees the console) |
| **F8** | `open <map>` — re-opens whatever path is in `tools/map.txt` (acts as *restart* when it matches the current map) |
| **F9** | run diagnostics, append to `tools/inj.log` |
| **W A S D** | walk (velocity write, speed = `MaxWalkSpeed` read from `cm+0x268`) |
| **Mouse** | look (cursor is re-centred every tick, 0.06°/px) |
| **Space** | jump |

Planned / not yet wired: F5 restart, F10 map cycle, F11 mob spawn, F12 character swap,
plus **all** combat/UI keys (attack, interact, crouch, sprint, inventory).

---

## 4. How the offline injection works

1. `bypass.py` launches `DungeonStalkers-Win64-Shipping.exe` and patches GameGuard:
   ```
   0x14507be39  e8 -> b8 55 07 00 00   fake clean GG result (1877)
   0x14507bd84  c6 41 38 01 -> 00      subsystem failed-flag = 0
   0x14507bf36  c6 05 .. 01 -> 00      global GG-failed flag = 0
   0x14507bf80  ff 15 ..  -> 90*6      NOP MessageBoxW (error dialog)
   0x1450753a3  ff 15 ..  -> 90*6      NOP MessageBoxW (alt dialog)
   ```
2. **Two** processes spawn: an nEOS **parent** (hwnd `0`) and the **child** which owns
   the window. Always inject into the child.
3. `inject.py` uses `CreateRemoteThread` + `LoadLibraryW` to drop `Dumper-7.dll`.
4. `main.cpp::MainThread` runs Dumper-7's own SDK dump, truncates `tools/inj.log`,
   runs `WSRun()` (diagnostics) once, then loops at 16 ms calling `WSInputTick()`.

### Why input was dead and how we worked around it
`APawn::ControlInputVector` (`pawn+0x2F8`) is **ignored** — writing it does nothing,
which is why the first attempt didn't move. Writing
`UCharacterMovementComponent::Velocity` (`cm+0xB8`, first 16 bytes = X,Y only, so Z
is left alone) moves the character regardless.

Mouse look works because `AController::ControlRotation` (`ctrl+0x328`) is read
directly every tick, and the game's own look input is dead.

---

## 5. Confirmed offsets (game 1.8.05 / UE 5.5.4)

| Thing | Offset | Notes |
|---|---|---|
| `AController::Pawn` | `ctrl+0x2F0` | `TObjectPtr<APawn>` |
| `AController::Character` | `ctrl+0x300` | used by the driver |
| `AController::ControlRotation` | `ctrl+0x328` | `FRotator` = 3 doubles (24 B), degrees |
| `AController::PlayerState` | `ctrl+0x2B8` | |
| `APlayerController::Player` | `ctrl+0x350` | used to pick the local controller |
| `APlayerController::HUD` | `ctrl+0x360` | |
| `APlayerController::MyCameraManager` | `ctrl+0x368` | |
| `APlayerController::PlayerInput` | `ctrl+0x428` | |
| `APlayerController` `bPlayerIsWaiting` | `ctrl+0x4C0` bit4 | observed `0x4C0 = 9` |
| `APlayerController` `bShowMouseCursor` etc. | `ctrl+0x554` | bit0 cursor, bit1 click, bit2 touch, bit3 mouse-over, bit5 forcefeedback; observed `0xE4` |
| `APawn::ControlInputVector` | `pawn+0x2F8` | 3 doubles (24 B) — **ignored, don't bother** |
| `APawn::LastControlInputVector` | `pawn+0x310` | 3 doubles |
| `ACharacter::CharacterMovement` | `pawn+0x338` | |
| `UCharacterMovementComponent::Velocity` | `cm+0xB8` | 3 doubles — **the one that works** |
| `::MovementMode` | `cm+0x221` | `1 = MOVE_Walking` |
| `::MaxWalkSpeed` | `cm+0x268` | tutorial = `228.9` |
| `::MaxAcceleration` | `cm+0x27C` | `2048` |
| `ACharacter::bPressedJump` | `0x450` bit3 | |
| FString layout | `{ void* Data; int32 Num; int32 Max }` | `Num = wcslen+1` (includes NUL) |
| `UKismetSystemLibrary::ExecuteConsoleCommand` | params size `0x20` | `WorldContextObject 0x00`, `FString Command 0x08`, `APlayerController* SpecificPlayer 0x18` |

Finding the local controller: scan `ObjectArray` for non-`Default__` instances of
`PlayerController` whose `ctrl+0x350` (`Player`) is non-null — see `WSFindLocal()`.

---

## 6. Useful UFUNCTIONs (all on `AWSCharacterPlayer`, FName `WSCharacterPlayer`)

Callable through `ProcessEvent` — these are the missing combat/UI keys:

```
AttackPressed/AttackReleased        CrouchPressed/CrouchReleased
SprintPressed/SprintReleased        InteractionPressed/InteractionReleased
JumpPressed/JumpReleased            Skill1/2/3Pressed & Released
SpecialSkillPressed/Released        UltimateSkillPressed/Released
OnToggleLight                       OnToggleInventory
OnToggleMap                         OnToggleSkillGuide
OnToggleChangeCamera                OnToggleControllGuide
OnQuickPing / OnQuickEnemyPing      SelectFirstWeaponReleased / SelectSecondWeaponReleased
InitInputActionBinding()            InputFlush()
```

`InitInputActionBinding()` is the real fix for native input — worth calling once on
the pawn when it is acquired (it is a UFUNCTION, so `ProcessEvent` works).

Other useful ones:
* `AWSSurvivalGameMode::SpawnEnemy()` — mob spawn (`WorldStalker_classes.hpp:6898`)
* `AWSPlayerController::ServerDebugSpawnEnemy(...)`
* `UWSGameInstance::OpenLevelEx(WorldContextObject, LevelName, bAbsolute, Options)` — params struct not located yet
* `UWSTabBar::TravelToNextMap()`, `UWSGameWidget::OnEnterDungeon()`, `UWSBattleFieldGameScore::StartGame()`

---

## 7. Config the game tries to delete

`%LOCALAPPDATA%\DungeonStalkers\Saved\Config\Windows\` — **`keeper.py` must be
running first**, otherwise the game wipes these on startup.

### `Engine.ini`
```ini
[BigAccount]
bEnable=False
Maingate="http://127.0.0.1:8080/maingate"
ServiceCode=000000000000

[BigAccount.Guest]
bEnable=True

[/Script/EngineSettings.GameMapsSettings]
GameDefaultMap=/Game/Maps/Tutorial/L_Tutorial.L_Tutorial
```
`GameDefaultMap` values tried:
* `/Game/Maps/Tutorial/L_Tutorial.L_Tutorial` — **working, use this**
* `/Game/Maps/L_Title.L_Title` — boots to the real title screen; Enter opens the
  Polish login screen "Zaloguj się" but it never proceeds (needs maingate)
* `/Game/Maps/TrainingGround/L_TrainingGround.L_TrainingGround` — **crashes**
* `/Game/Maps/Hideout/L_Hideout_A`, `/Game/Maps/PrisonDungeon/Prison_Dungeon_A` —
  reachable only by runtime `open`, load a bare world with no pawn/HUD, then die

### `Input.ini`
```ini
[/Script/Engine.InputSettings]
ConsoleKeys=Tilde
```

---

## 8. File map

```
docs/TECHNICAL-NOTES.md      this file
bypass.py                     GameGuard patches + launch
Start Dungeon Stalkers.bat     wrapper around bypass.py
keeper.py                     holds the .ini files open (run before the game)
stub.py                       loopback HTTP stub for 127.0.0.1:80 / 8080 (logs API calls)

Dumper-7-main/                stock Dumper-7 (github.com/EncryptedCrawler/Dumper-7 or similar)
  Dumper-7.sln
  Dumper/main.cpp             *** THE ONLY MODIFIED FILE — all our logic lives here ***
  Dumper/Dumper.vcxproj
tools/
  inject.py                   CreateRemoteThread + LoadLibraryW injector (args: <pid> <dll>)
  map.txt                     map path used by the F8 hotkey
  shot.ps1                    screenshot of a process   (-ProcId -Out)
  diff.ps1                    pixel-diff two PNGs       (-A -B)
  drvtest.py                  focus game, move mouse, hold W/D, screenshot + diff
  rd6.py                      read live pawn/ctrl fields (args: <pid> <ctrlHex>)
  fs.py                       confirms the FString layout
  stringscan.py               scan the exe for strings
  marker.cpp                  tiny marker DLL used by older probes
  inj.log.last                last diagnostics output
bin/
  Dumper-7.dll                last-known-good build
  Dumper-7.pdb                matching symbols
config/
  Engine.ini Game.ini Input.ini   current working config
```

Everything upstream of `main.cpp` is stock Dumper-7 — `main.cpp` is the whole diff.

---

## 9. Gotchas

* **Admin = false.** No hosts-file edits. Binding 80/443/8080 to `127.0.0.1` works.
* Python 3.12 at `C:\Users\snipe\AppData\Local\Programs\Python\Python312\python.exe`.
  Console is cp1250 → scripts start with
  `sys.stdout.reconfigure(encoding='utf-8', errors='replace')`.
* PowerShell 5.1: write files with a file-writing tool, not `Set-Content`;
  run `.ps1` via `powershell -NoProfile -ExecutionPolicy Bypass -File`.
* No PIL — pixel diffs go through `tools/diff.ps1` (System.Drawing).
* Dumper-7's `AllocConsole()` steals focus. To focus the game from a script use the
  **ALT trick**: `keybd_event(VK_MENU)` down/up, *then* `SetForegroundWindow` —
  plain `SetForegroundWindow` returns False while another window is foreground.
* A Win32 `INPUT` struct must be exactly **40 bytes** on x64 or `SendInput` returns 0.
* `__try/__except` is illegal in functions with C++ object unwinding (**C2712**) —
  SEH must live in leaf functions with POD locals only (`WSRead`, `WSWrite`, `WSAppendLogC`).
* Never use broad name patterns when killing processes — the launcher and the real
  game share the name `DungeonStalkers-Win64-Shipping`; pick by `MainWindowHandle`.

---

## 10. Next steps

1. Call `AWSCharacterPlayer::InitInputActionBinding()` + `InputFlush()` on the pawn
   when it is acquired — if native input comes alive, delete the emulated keys.
2. Until then, wire the remaining keys by calling the UFUNCTIONs in §6 from
   `WSInputTick` (edge-triggered for press/release pairs).
3. F11 mob spawn → `AWSSurvivalGameMode::SpawnEnemy()` (tutorial uses
   `BP_TutorialGameMode_C`, so first find a spawn function that exists on it).
4. F12 character swap → `AController::Possess`.
5. Get past the login screen using `stub.py`'s logged request paths to reconstruct
   the maingate contract (or skip it entirely and keep driving through `open`).
