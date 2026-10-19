import zipfile

src = "work/tmp/rl-2.0.6.jar"
dst = "work/tmp/rl-2.0.6-patched.jar"
base = "com/teamresourceful/resourcefullib/common/networking/fabric/"
repl = {
    base + "PacketChannelHelperImpl.class":
        "work/tmp/rl-server/classes/" + base + "PacketChannelHelperImpl.class",
    base + "FabricClientPacketHelper.class":
        "work/tmp/rl-server/classes/" + base + "FabricClientPacketHelper.class",
    base + "FabricClientPacketHelper$RawPayload.class":
        "work/tmp/rl-server/classes/" + base + "FabricClientPacketHelper$RawPayload.class",
}

zin = zipfile.ZipFile(src)
zout = zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED)
for item in zin.infolist():
    if item.filename in repl:
        continue
    zout.writestr(item, zin.read(item.filename))
for name, path in repl.items():
    zout.write(path, name)
zout.close()

outer_src = "work/client/ironchests-nbt2.jar"
outer_dst = "work/client/ironchests-rlfixed.jar"
nested = "META-INF/jars/resourcefullib-fabric-1.20-2.0.6.jar"

zin = zipfile.ZipFile(outer_src)
zout = zipfile.ZipFile(outer_dst, "w", zipfile.ZIP_DEFLATED)
for item in zin.infolist():
    if item.filename == nested:
        continue
    zout.writestr(item, zin.read(item.filename))
zout.write(dst, nested)
zout.close()
print("wrote", dst, "and", outer_dst)
