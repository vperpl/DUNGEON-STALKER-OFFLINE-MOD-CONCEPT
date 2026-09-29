# DUNGEON STALKER OFFLINE MOD CONCEPT

Offline / single-player proof of concept for **Dungeon Stalkers** (build `1.8.05.LIVE`,
appid `2468730`).

> [!CAUTION]
> **Not playable.** This is a **proof of concept** only - a checkpoint snapshot so the
> work does not get lost. Educational / offline research use only. Do **not** take this
> into online play.

## Demo

<video src="https://raw.githubusercontent.com/vperpl/DUNGEON-STALKER-OFFLINE-MOD-CONCEPT/main/media/2026-09-29-16-25-28.mp4" controls width="860"></video>

[Open the video](media/2026-09-29-16-25-28.mp4)

## Status at a glance

| | |
|---|---|
| **Playable?** | **No - not playable.** |
| **What is it?** | Proof of concept / offline checkpoint |
| **Anti-cheat** | GameGuard bypassed ~**90%** (`bypass.py`, 5 byte patches) |
| **Working level** | Tutorial map (`L_Tutorial`) - boots straight into it |
| **Character movement** | WASD walk, mouse look, jump (Space) |
| **Crouch** | works |
| **Interact** | **does not work** (F) |
| **Hotkeys** | F-row, F1-F9 (F1 toggle input driver, F8 map restart, F9 diagnostics) |

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
write-up - is in the release file:

**[DungeonStalkers-offline-checkpoint.zip](DungeonStalkers-offline-checkpoint.zip)**

Unzip it and read `README.md` inside for offsets, quick start, config and gotchas.

## Requirements

- Windows, Python 3.12, Visual Studio 2022 (to rebuild `Dumper-7.dll`)
- The Steam release of Dungeon Stalkers
