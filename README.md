# DUNGEON STALKER OFFLINE MOD CONCEPT

Offline / single-player proof of concept for **Dungeon Stalkers** (build `1.8.05.LIVE`,
appid `2468730`).

> [!CAUTION]
> **Not playable.** This is a **proof of concept** only - a checkpoint snapshot so the
> work does not get lost. Educational / offline research use only. Do **not** take this
> into online play.

## Demo video

[![Demo video - Dungeon Stalkers offline mod](https://github.com/vperpl/DUNGEON-STALKER-OFFLINE-MOD-CONCEPT/raw/main/media/poster.jpg)](https://github.com/vperpl/DUNGEON-STALKER-OFFLINE-MOD-CONCEPT/blob/main/media/2026-09-29-16-25-28.mp4)

**[Play the demo video](https://github.com/vperpl/DUNGEON-STALKER-OFFLINE-MOD-CONCEPT/blob/main/media/2026-09-29-16-25-28.mp4)**
- `media/2026-09-29-16-25-28.mp4` - 26 s, 1920x1080 (15 MB)
- direct: [download the mp4](https://github.com/vperpl/DUNGEON-STALKER-OFFLINE-MOD-CONCEPT/raw/main/media/2026-09-29-16-25-28.mp4)

## Status at a glance

| | |
|---|---|
| **Playable?** | **No - not playable.** |
| **What is it?** | Proof of concept / offline checkpoint |
| **Anti-cheat** | GameGuard bypassed ~**90%** (`bypass.py`, 5 byte patches) |
| **Working level** | Tutorial map (`L_Tutorial`) - boots straight into it |
| **Character movement** | WASD walk, mouse look, jump (Space) - all working |
| **Crouch** | works |
| **Interact** | **does not work** ([F]) |
| **Hotkeys** | F-row, **F1**-**F9** (F1 toggle input driver, F8 map restart, F9 diagnostics) |

### Works
- GameGuard bypass - `bypass.py`, 5 byte patches
- Boot straight into a playable map via `Engine.ini` `GameDefaultMap`
- **Move** (WASD), **camera look** (mouse), **jump** (Space)
- **Crouch**
- Map switch / restart - **F8**
- Diagnostics - **F9**

### Not working yet
- **Interact [F]** and the rest of the native UE input bindings -
  `AWSCharacterPlayer::InitInputActionBinding()` is never called by our flow, so
  attack / interact / sprint / inventory do nothing
- `L_TrainingGround` crashes; non-tutorial maps load a bare world with no pawn/HUD
- No maingate / login - `[BigAccount] bEnable=False`, the tutorial map bypasses it
- No UE log (`Saved/Logs/` only has `cef3*.log`)

## Hotkeys

| Key | Action |
|---|---|
| **F1** | toggle the input driver on/off |
| **F6** | unload the DLL (frees the console) |
| **F8** | `open <map>` - re-opens the path in `tools/map.txt` (restart) |
| **F9** | run diagnostics, append to `tools/inj.log` |
| **W A S D** | walk |
| **Mouse** | look |
| **Space** | jump |

Planned / not wired: F5 restart, F10 map cycle, F11 mob spawn, F12 character swap,
plus all combat/UI keys.

## Download

The full package - bypass, injector, Dumper-7 SDK dump, config, tools and the complete
write-up - is in the release archive:

**[DungeonStalkers-offline-checkpoint.zip](https://github.com/vperpl/DUNGEON-STALKER-OFFLINE-MOD-CONCEPT/releases/download/0.1/DungeonStalkers-offline-checkpoint.zip)** (4.3 MB)

or browse it directly in this repo (`bypass.py`, `tools/`, `config/`, `bin/`,
`Dumper-7-main/`). The detailed write-up (offsets, quick start, config, gotchas) is in
[`docs/TECHNICAL-NOTES.md`](docs/TECHNICAL-NOTES.md).

## How it works (short version)

1. `bypass.py` launches `DungeonStalkers-Win64-Shipping.exe` and applies 5 byte patches
   to GameGuard (fake clean result, clear failed-flags, NOP the error dialogs).
2. Two processes spawn - an nEOS parent and the child that owns the window.
   `tools/inject.py` injects `Dumper-7.dll` into the **child** with
   `CreateRemoteThread` + `LoadLibraryW`.
3. `Dumper/main.cpp` (the only modified file) dumps the SDK, then drives movement by
   writing `CharacterMovement->Velocity` at `cm+0xB8` and
   `AController::ControlRotation` at `ctrl+0x328`.

## Requirements

- Windows, Python 3.12, Visual Studio 2022 (to rebuild `Dumper-7.dll`)
- The Steam release of Dungeon Stalkers
