package top.dext.centurybridge.data;

import java.nio.file.Path;

/**
 * LOCAL P0 BUILD PATCH - not upstream code.
 *
 * The pinned CenturyBridge commit (cf4ebeba...) references
 * {@code top.dext.centurybridge.data.MixinCheck} from Main, but no such source file
 * exists in the published tree, so the engine cannot be compiled as-is.
 *
 * This no-op keeps the engine CLI compilable so P0 can test gen-segment/convert.
 * It does NOT implement the mixin-target gate; any result that depends on
 * `mixin-check` (the bridge-jar build gate in build.sh) is therefore unverified.
 */
public final class MixinCheck {
    private MixinCheck() {}

    public static void run(Path compiledShimDir, Path targetJar, Path wiring, Path nameTable) {
        System.out.println("[local stub] mixin-check NOT IMPLEMENTED: " + compiledShimDir
                + " against " + targetJar);
    }
}
