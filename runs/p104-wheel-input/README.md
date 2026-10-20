# P104: real mouse-wheel input attempt

Date: 2026-10-20.

## Goal

Scroll the Mod Menu list with a real OS mouse wheel (the earlier scroll evidence used the list's
`setScrollAmount` directly).

## Method

A probe opens `ModsScreen`, prints the list geometry and scroll amount every 40 ticks, and
screenshots before/after. External injection tried three approaches while the cursor was over the
list centre (`x=67 w=163`, GUI y=128):

1. `SetCursorPos` + `mouse_event(MOUSEEVENTF_WHEEL, -120 x5)`;
2. `mouse_event(MOUSEEVENTF_MOVE | ABSOLUTE)` + five wheel notches;
3. `PostMessage(WM_MOUSEMOVE)` + five `PostMessage(WM_MOUSEWHEEL)`.

## Result

The list scroll amount never changed:

```text
WHEEL_BEFORE  x=67 w=163 h=153 scroll=0.0
WHEEL_SAMPLE160..400 x=67 w=163 h=153 scroll=0.0
WHEEL_AFTER   x=67 w=163 h=153 scroll=0.0
```

So the real-wheel path is **not verified** in this environment. The window is a directly launched
Java process; OS wheel messages appear not to reach GLFW's scroll callback here (and the focus state
cannot be asserted reliably from the harness).

Earlier verified scrolling (programmatic) is unchanged: `runs/p94-modmenu-list/` scrolled the list
with `setScrollAmount` and shows the rows moving.

## Scope

- This is an input-injection limitation, not a conversion regression: the list's own scroll value
  and rendering were already verified.
- Keyboard input into mod screens has the same injection limitation.

## Evidence

`client.log`, `modmenu-wheel-before.png`, `modmenu-wheel-after.png`.
