# P44: all-three bundle profile

Date: 2026-10-18 (Asia/Shanghai). Packages the P41-P43 coexistence evidence into one profile.

## Profile

`profiles/bundle-all-three__fabric-1.21.1.json`:

- `status: passed_within_scope`;
- mods: lithium P13, ironchests P26, trashslot P29, Balm 21.0.66;
- contracts: boot `Done (4.632s)`, container 5/5, 225-chunk stress, CodecDispatch probe;
- pending: client GUI and multiplayer.

The profile pins the four evidence hashes and references the per-mod profiles. The profile
index in `profiles/README.md` now lists it.

## Verifier

`tools/verify_evidence.py` gained a `bundle_profile` check. The run covers the 18 tests, all
prior contracts/probes and the three profiles; exit 0.

Full output: `verify.log`.
