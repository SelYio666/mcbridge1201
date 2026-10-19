# P86: empty-trash hover attempt — geometry measured, key still inactive

Date: 2026-10-19 (Asia/Shanghai). Second attempt at the physical empty-trash key.

## What we measured

The probe opened the inventory, seeded 5 diamonds into the trash, and logged the trash geometry:

```text
TRASH_SLOT  f72=165 f73=152 f74=0
TRASH_SCREEN w=342 h=256 left=-1 top=-1
TRASH_RECT  l=227 t=207 r=258 b=231
```

- the trash slot's GUI position is x=152, y=165 (slot fields f73/f72);
- the component's `isInside` rect is `(227,207)-(258,231)` in GUI coords;
- the GUI screen is 342x256, which with a 1024x768 client area gives GUI scale 3;
- client-area origin via `ClientToScreen` = `(448,216)`, so the icon centre maps to physical
  `(1176,873)`.

## Attempts

The OS cursor was placed at `(1176,873)` and four modifier combinations were injected:
`Delete`, `Ctrl+Delete`, `Shift+Delete`, `Alt+Delete`.

## Result

```text
TRASH_STATE tick=520..840 trash=5 minecraft:diamond
```

The trash never emptied. The geometry is now known, so the remaining causes are outside the
coordinates:

- the synthetic key may not reach the Balm `ScreenKeyEvent$Press$Post` path (focus handling);
- the delete binding may be disabled by TrashSlot config in this world;
- the modifier the binding expects may differ from the four tried.

## Scope

The empty-trash action itself passes at provider level (`runs/p65-trash-empty/`). Only the physical
key path is still unverified.

## Evidence

- `latest.log`, `TrashEmptyKeyProbe.java`, `trashemptykey.jar`, `compile.log`
