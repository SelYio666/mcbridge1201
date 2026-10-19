# P81: physical ESC attempt — blocked by the probe's menu closing immediately

Date: 2026-10-19 (Asia/Shanghai). Attempted, not passed.

## Goal

Verify the real keyboard ESC path closes the IronChests chest (the same path `Screen.close()` takes,
already verified programmatically in P77).

## What happened

The probe placed a chest at `(80,65,65)`, opened it through `ServerPlayer.openHandledScreen` with a
`MenuProvider` built on the block entity, then logged the client screen and the server handler size.

```text
ESC_PLACED=true pos=class_2338{x=80, y=65, z=65}
ESC_OPEN opened=OptionalInt[1]
ESC_SERVER_MENU tick=160 slots=46
ESC_CLIENT tick=160 screen=null slots=46
```

The server accepted the open (`OptionalInt[1]`) but by tick 160 the handler was already back to the
46-slot player inventory, and the client never showed a `ChestScreen`. So there was no open screen
to press ESC on, and the OS key injection never had a target.

## Interpretation

- the provider-based open path (`BlockEntity.createMenu` through `openHandledScreen`) does **not**
  keep the menu open on the integrated server in this probe, unlike the real block `onUse` path
  used in P68–P70;
- therefore this probe cannot test the physical ESC key;
- the physical ESC key path remains **unverified**; the programmatic `Screen.close()` path is
  verified in P77.

## Next

Use the real `GenericChestBlock.onUse` path (reflective `method_9534`, as in P68) to open the
screen, then inject ESC and check the server handler size.

## Evidence

- `latest.log`, `EscProbe.java`, `escprobe.jar`
