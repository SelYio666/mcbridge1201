# P100: real hover tooltip for ShulkerBoxTooltip

Date: 2026-10-20.

## Setup

Dedicated server (`online-mode=false`, Fabric API only) + client with converted ShulkerBoxTooltip.
A client probe gives the player a shulker box whose CONTAINER component holds five diamonds, opens
the inventory, and saves a screenshot. An external cursor injection (`SetCursorPos` into the
inventory's hotbar slot, window client origin computed from `GetClientRect`/`ClientToScreen`) makes
the game actually hover that slot.

## Result

The screenshot shows the inventory with the shulker box hovered and the mod's own tooltip:

```text
Shulker Box
Diamond x5
```

`Diamond x5` is read from the CONTAINER component through the bridged legacy NBT path, so the real
hover → tooltip → provider chain works, not only the earlier contract probe.

## Blocker found and fixed on the way

`ShulkerBoxTooltipUtil.id` calls `new Identifier(namespace, path)`. 1.21.1 made that constructor
**private** (only `class_2960.method_60655` is public), so the client aborted at startup with
`IllegalAccessError`. `identifier-single-arg.json` now also redirects the two-argument constructor to
`IdentifierBridge.of(namespace, path)`; six call sites in the Shulker jar are rewritten.

A first attempt spawned in a singleplayer world whose spawn point was underwater; the player drowned
before the screenshot. The dedicated server world has a dry spawn, which is why the test now runs
there. Client and server mod sets must also match, or Fabric disconnects on registry sync
(`Received 73 registry entries that are unknown to this client`).

## Scope

- The tooltip shown is the item-summary variant (`Diamond x5`), not the full grid preview; the grid
  may need the server-side mod channel / a different preview mode.
- Hover is verified for one slot with the hotbar selected; other slots and shulker variants are not.

## Evidence

`shulker-hover.png`, `client.log`, `server.log`.
