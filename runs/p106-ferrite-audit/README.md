# P106: FerriteCore mixin audit

Date: 2026-10-20.

## What was compared

Raw `ferritecore-6.0.1-fabric.jar` vs the converted
`ferritecore-6.0.1-fabric+1.21.1.jar`, all nine `*.mixin.json` files.

## Result

The converted jar keeps all nine config files, but two of them were emptied:

| config | raw mixins | converted mixins |
|---|---|---|
| `ferritecore.fastmap.mixin.json` | `FastMapStateHolderMixin` | *(empty)* |
| `ferritecore.mrl.mixin.json` | `ModelResourceLocationMixin`, `ResourceLocationAccess` | `ResourceLocationAccess` only |

The other seven configs are unchanged (`blockstatecache`, `dedupbakedquad`, `dedupmultipart`,
`fabric`, `modelsides`, `predicates`, `threaddetec`). The mixin classes themselves still exist in
the jar; only the config entries are gone, so those two hooks are inert.

## Impact

- Both are **memory/size optimizations**: the multipart state-holder dedup and the model-resource
  location cache. Losing them costs memory, not correctness.
- This matches the documented "dead mixin target" stripping used elsewhere (AppleSkin tooltip,
  Shulker grid preview): the 1.21.1 targets no longer exist, so re-enabling the entries would fail
  mixin application and crash startup.
- Restoring the optimizations needs replacement mixins for the new 1.21.1 model classes, which is a
  performance task, not a compatibility fix.

## Evidence

This note plus the two config dumps in the conversion workspace
(`work/expansion/converted/ferrite-core/`). The converted jar itself is not distributed.
