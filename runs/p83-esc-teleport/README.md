# P83: physical ESC key closes the chest

Date: 2026-10-19 (Asia/Shanghai). Supersedes the blocked P81/P82 attempts.

## Why the earlier attempts failed

The earlier probes placed the chest next to wherever the player happened to be and opened it without
repositioning. The menu's validity check closed it within ~80 ticks, so the client never kept a
screen to press ESC on. This run:

- clears the target block to air first, then places a fresh iron chest, so no stale block entity;
- teleports the player to `(chest.x + 0.5, chest.y, chest.z + 1.5)` before opening, well inside the
  8-block menu range.

## Result

```text
ESC_PLACED=true pos=class_2338{x=80, y=65, z=65} player=80.5,65.0,66.44
ESC_OPEN result=CONSUME

ESC_CLIENT tick=160 screen=ChestScreen slots=90
ESC_CLIENT tick=200 screen=ChestScreen slots=90
      (OS key injection: ESC)
ESC_CLIENT tick=240 screen=net.minecraft.class_433 slots=46
ESC_SERVER_MENU tick=240 slots=46
```

- the chest screen was open at ticks 160 and 200 (`slots=90`);
- after the physical ESC key press it is gone by tick 240 (`class_433` is the pause/game menu) and the
  client handler is back to the 46-slot inventory;
- the server handler also fell back to 46 slots.

**The physical ESC path closes the IronChests chest on both sides.**

## Evidence

- `latest.log`, `EscProbe.java`, `escprobe.jar`, `compile.log`
