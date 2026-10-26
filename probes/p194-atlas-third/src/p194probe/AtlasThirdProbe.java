package p194probe;

import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.class_1011;
import net.minecraft.class_22;
import net.minecraft.class_310;
import net.minecraft.class_330;
import net.minecraft.class_638;
import net.minecraft.class_3620;
import net.minecraft.class_9209;

import p194probe.mixin.DrawContextConsumersAccessor;

/**
 * Test-only client probe for p194: the THIRD atlas (2048+ maps) and cross-atlas same-frame draw.
 *
 * <p>Once the server has sent the real MapState of map 1, the probe drives the public update path
 * for ids 1..2050 while reusing that one MapState: 1..1024 fill atlas 0, 1025..2048 fill atlas 1,
 * 2049/2050 must create and fill atlas 2. The HUD then calls the public MapRenderer.draw for map 1
 * (atlas 0), map 1025 (atlas 1) and map 2049 (atlas 2) inside ONE frame, so the bind + upload for
 * both overflow atlases happens in the same screenshot. The second HUD frame reads back the
 * NativeImages of atlas 1 and atlas 2 and compares sampled pixels with the MapState colours. After
 * 60 s the probe requests a normal client stop, letting the runner verify
 * {@code map-atlas clear atlases=3} on a real exit.
 */
public final class AtlasThirdProbe implements ClientModInitializer {
    private static final int FIRST_OVERFLOW_ID = 1025;
    private static final int SECOND_OVERFLOW_ID = 2049;
    private static final int LAST_ID = 2050;
    private static final long EXIT_DELAY_MS = 60_000L;

    private boolean assigned;
    private boolean drawn;
    private boolean pixelChecked;

    @Override
    public void onInitializeClient() {
        net.fabricmc.fabric.api.client.rendering.v1.HudRenderCallback.EVENT.register(
                (context, tickCounter) -> drawThreeMaps(context));
        ClientTickEvents.END_CLIENT_TICK.register(this::tick);
        Thread stopper = new Thread(() -> {
            try {
                Thread.sleep(EXIT_DELAY_MS);
            } catch (InterruptedException ignored) {
                return;
            }
            class_310 client = class_310.method_1551();
            System.out.println("[p194-probe] requesting client stop");
            client.method_18859(client::method_1592);
        }, "p194-stop");
        stopper.setDaemon(true);
        stopper.start();
    }

    /**
     * Cross-atlas frame: draw map 1 (atlas 0), map 1025 (atlas 1) and map 2049 (atlas 2) through
     * the public MapRenderer.draw in the same HUD frame. The quads land near the HUD origin, which
     * does not matter: the bind markers, the screenshot and the pixel checks are the evidence.
     */
    private void drawThreeMaps(net.minecraft.class_332 context) {
        class_310 client = class_310.method_1551();
        class_638 world = client.field_1687;
        if (!assigned || pixelChecked || world == null || client.field_1724 == null) {
            return;
        }
        class_22 state1 = world.method_17891(new class_9209(1));
        if (state1 == null) {
            return;
        }
        if (!drawn) {
            drawn = true;
            class_330 mapRenderer = client.field_1773.method_3194();
            net.minecraft.class_4597.class_4598 consumers =
                    ((DrawContextConsumersAccessor) (Object) context).mcbridge$field_44658();
            for (int id : new int[]{1, FIRST_OVERFLOW_ID, SECOND_OVERFLOW_ID}) {
                mapRenderer.method_1773(context.method_51448(), consumers,
                        new class_9209(id), state1, true, 15728880);
            }
            System.out.println("[p194-probe] drew maps 1/1025/2049 through MapRenderer.draw"
                    + " (atlas 0/1/2, one HUD frame)");
            return;
        }
        pixelChecked = true;
        net.raphimc.immediatelyfast.injection.interfaces.IMapRenderer hooks =
                (net.raphimc.immediatelyfast.injection.interfaces.IMapRenderer) client.field_1773.method_3194();
        checkAtlas(hooks, state1, 1);
        checkAtlas(hooks, state1, 2);
    }

    private static void checkAtlas(net.raphimc.immediatelyfast.injection.interfaces.IMapRenderer hooks,
                                   class_22 state, int atlasId) {
        net.raphimc.immediatelyfast.feature.map_atlas_generation.MapAtlasTexture atlas =
                hooks.immediatelyFast$getMapAtlasTexture(atlasId);
        if (atlas == null) {
            System.out.println("[p194-probe] atlas" + atlasId + "-pixel-check FAILED: atlas missing");
            return;
        }
        class_1011 image = atlas.getTexture().method_4525();
        if (image == null) {
            System.out.println("[p194-probe] atlas" + atlasId
                    + "-pixel-check FAILED: image not allocated");
            return;
        }
        byte[] colors = state.field_122;
        int mismatches = 0;
        int[] probes = {0 + 0 * 128, 64 + 64 * 128, 127 + 127 * 128, 32 + 96 * 128};
        StringBuilder report = new StringBuilder();
        for (int i : probes) {
            int x = i % 128;
            int y = i / 128;
            int expected = class_3620.method_38480(colors[i] & 0xFF);
            int actual = image.method_4315(x, y);
            boolean ok = actual == expected;
            if (!ok) {
                mismatches++;
            }
            report.append(" (").append(x).append(',').append(y)
                    .append(')').append(ok ? "ok" : "exp=" + expected + " act=" + actual);
        }
        System.out.println("[p194-probe] atlas" + atlasId + "-pixel-check mismatches="
                + mismatches + report);
    }

    private void tick(class_310 client) {
        class_638 world = client.field_1687;
        if (world == null || client.field_1724 == null || assigned) {
            return;
        }
        class_22 state1 = world.method_17891(new class_9209(1));
        if (state1 == null) {
            return;
        }
        assigned = true;
        class_330 mapRenderer = client.field_1773.method_3194();
        for (int id = 1; id <= LAST_ID; id++) {
            mapRenderer.method_1769(new class_9209(id), state1);
        }
        net.raphimc.immediatelyfast.injection.interfaces.IMapRenderer hooks =
                (net.raphimc.immediatelyfast.injection.interfaces.IMapRenderer) mapRenderer;
        System.out.println("[p194-probe] assigned 2050 map ids (reusing map 1's MapState)"
                + " mapping1024=" + hooks.immediatelyFast$getAtlasMapping(1024)
                + " mapping2048=" + hooks.immediatelyFast$getAtlasMapping(2048)
                + " mapping2049=" + hooks.immediatelyFast$getAtlasMapping(SECOND_OVERFLOW_ID)
                + " mapping2050=" + hooks.immediatelyFast$getAtlasMapping(LAST_ID)
                + " atlasOf2049=" + (hooks.immediatelyFast$getAtlasMapping(SECOND_OVERFLOW_ID) >> 16)
                + " atlasOf2050=" + (hooks.immediatelyFast$getAtlasMapping(LAST_ID) >> 16));
    }
}
