# P43: CodecDispatch probe with all three samples loaded

Date: 2026-10-18 (Asia/Shanghai). Puts the P37 semantic probe into the P41 coexistence instance.

## Setup

`fabric-1.21.1-server-all-three` plus `codecdispatchprobe.jar`:

- lithium P13 chunk-port
- P26 safe-Codec ironchests
- P29 trashslot + native Balm 21
- Fabric API

## Result

```text
Done (5.425s)! For help, type "help"
[STDOUT]: CODEC_DISPATCH_PROBE_OK
```

The probe encodes `Box(1)` to `{"a":1,"type":"k"}` and decodes it back with the P26
`CodecDispatch`, while lithium/trashslot/Balm are loaded. Runner/JVM exit 0.

## Scope

Dedicated server + command API; the probe is synthetic, not a client and not ironchests GUI.

## Evidence

- `server.log` / `server.result.json`
