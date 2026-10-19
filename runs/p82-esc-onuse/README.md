# P82: physical ESC retry with the real onUse path — still blocked

Date: 2026-10-19 (Asia/Shanghai). Follow-up to P81.

## What changed

The probe now opens the chest through the real block path — reflective
`GenericChestBlock.method_9534(state, world, pos, player, hand, hitResult)` — the same call used by
the successful P68–P70 GUI tests, instead of the `MenuProvider` route.

## Result

```text
ESC_PLACED=false pos=class_2338{x=80, y=65, z=65}
ESC_OPEN result=CONSUME
ESC_SERVER_MENU tick=160 slots=46
ESC_CLIENT tick=160 screen=null slots=46
```

`onUse` returned `CONSUME` (it accepted the interaction), but within 80 ticks the server handler was
back to the 46-slot player inventory and the client never logged a `ChestScreen`. So again there was
no open screen to press ESC on.

## Interpretation

Both open routes (`openHandledScreen` + provider, and the real `onUse`) accept the interaction, but
the menu does not stay open in this world state. Candidate causes: the menu's `canUse` check failing
(player position/dimension vs the chest at `(80,65,65)`), or the chest block/entity at that position
being stale from earlier runs (`ESC_PLACED=false` means the block was already there). This needs a
world/position reset or a closer inspection of `GenericChestMenu.canUse` before the physical ESC test
can run.

## Scope

Physical ESC remains **unverified**. The programmatic `Screen.close()` path is verified in
`runs/p77-two-client-close/`.

## Evidence

- `latest.log`, `EscProbe.java`, `escprobe.jar`
