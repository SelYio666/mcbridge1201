# Compatibility profiles

One JSON profile per exercised sample. `status` is deliberately narrower than "compatible":

| profile | status | evidence |
|---|---|---|
| [ironchests 5.0.2](ironchests-5.0.2-fabric__fabric-1.21.1.json) | `passed_within_scope` | dedicated-server container contract 5/5 |
| [lithium 0.11.4](lithium-0.11.4-fabric__fabric-1.21.1.json) | `booted_within_scope` | boot + 225-chunk stress + combined container; no gameplay/client |
| [trashslot 15.1.5](trashslot-15.1.5-fabric__fabric-1.21.1.json) | `booted_within_scope` | boot with native Balm 21; no client/network round-trip |

All profiles pin the source jar hash, target client/mappings hashes, rule package hash and
the evidence files. Jars themselves are **not** stored in this repository; `work/` is
gitignored.

## Status vocabulary

- `passed_within_scope`: a declared contract passed; the scope is listed in the profile.
- `booted_within_scope`: the dedicated server reached `Done` and exited 0, but no gameplay or
  client contract was executed.
- `pending`: not executed (usually needs a client or player).
