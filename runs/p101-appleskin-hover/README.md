# P101: AppleSkin real hover tooltip

Date: 2026-10-20.

## Setup

Dedicated server (Fabric API only, dry spawn) + client with the converted AppleSkin jar. A probe
gives the player a golden apple, opens the inventory and saves a screenshot; an external cursor
injection hovers the hotbar slot.

## Result

The tooltip gains a second line produced by AppleSkin itself. The probe reads the tooltip through
`Screen.getTooltipFromItem` and logs:

```text
APPLE_TOOLTIP_TEXT [
  empty[style={color=aqua}, siblings=[translation{key='item.minecraft.golden_apple'}]],
  squeek.appleskin.client.TooltipOverlayHandler$FoodOverlayTextComponent@55871d2a
]
```

`FoodOverlayTextComponent` is AppleSkin's own food overlay component, so the real hover now runs
AppleSkin's tooltip handler end to end. The screenshot shows the extra tooltip row; its glyphs look
garbled on this machine because the client assets are incomplete (`icons.png` is missing), so the
exact numbers are not claimed from the image.

## API regressions fixed for the tooltip / HUD path

| legacy call | 1.21.1 change | bridge |
|---|---|---|
| `StatusEffectInstance.getEffectType()` returning `StatusEffect` | returns `RegistryEntry<StatusEffect>` | `StatusEffectInstanceBridge.effectType`, unwrap `comp_349()` |
| `StatusEffects.HUNGER` field typed `StatusEffect` | `RegistryEntry` constant | `hunger()` resolves `minecraft:hunger` from `Registries.STATUS_EFFECT` |
| `StatusEffects.POISON` / `WITHER` | same | `poison()` / `wither()` |
| `PlayerEntity.hasStatusEffect(StatusEffect)` | takes `RegistryEntry<StatusEffect>` | `hasStatusEffect` compares unwrapped values |

AppleSkin 2.5.2 added tooltip lines with a mixin on the removed
`ItemStack.getTooltip(PlayerEntity, TooltipType)`, and the conversion dropped that mixin entry.
`appleskin-tooltip.json` replaces `TooltipOverlayHandler.init()` with a bridge that registers the
mod's handler through Fabric's current `ItemTooltipCallback`.

The bridge exposed a bug in `bodyRedirects`: it always emitted `ALOAD 0` for `this`, even for a
static method, which produced `VerifyError: Bad local variable type`. The patcher now emits `ALOAD 0`
only for non-static methods.

## Scope

- Only the golden apple/hotbar slot was hovered.
- The estimated-health overlay with hunger/poison/wither is exercised by the same methods but was
  not separately screenshotted for each effect.
- The tooltip's numeric rendering is unreadable in this environment; the evidence is the component
  in the tooltip list.

## Evidence

`appleskin-hover.png`, `client.log`, `server.log`.
