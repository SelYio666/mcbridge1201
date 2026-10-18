"""Print tiny v2 mapping entries for one or more intermediary class names (debug helper)."""
import sys

path = sys.argv[1]
targets = set(sys.argv[2:])
hit = False
for line in open(path, encoding="utf-8"):
    if line.startswith("c\t"):
        parts = line.rstrip("\n").split("\t")
        hit = len(parts) > 2 and parts[2] in targets
        if hit:
            print("CLASS", parts[2], "obf", parts[1])
    elif hit and line.startswith("\t"):
        print("  ", line.rstrip("\n"))
