# P40: extended evidence verifier

Date: 2026-10-18 (Asia/Shanghai). Adds the P35/P36 at-target evidence and the lithium profile
to the one-command verifier.

## Added checks

- `at_targets_converted`: P35 converted lithium counts `(214, 86, 3)`;
- `at_targets_patched`: P36 patched lithium counts `(209, 84, 0)`;
- `profiles_present`: lithium profile status `booted_within_scope`.

## Result

`python tools/verify_evidence.py` exits 0; all checks true, including the previous 18 unit
tests, P14/P24/P26/P27/P33/P37/P38 evidence, and "no tracked jars".

Full JSON: `verify.log`.

This still checks existing evidence only; it does not launch a server/client.
