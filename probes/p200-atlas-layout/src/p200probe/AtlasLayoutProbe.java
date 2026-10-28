package p200probe;

import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.rendering.v1.HudRenderCallback;
import net.minecraft.class_1011;
import net.minecraft.class_22;
import net.minecraft.class_310;
import net.minecraft.class_330;
import net.minecraft.class_332;
import net.minecraft.class_3620;
import net.minecraft.class_4587;
import net.minecraft.class_4597;
import net.minecraft.class_638;
import net.minecraft.class_9209;

import net.raphimc.immediatelyfast.feature.map_atlas_generation.MapAtlasTexture;
import net.raphimc.immediatelyfast.injection.interfaces.IMapRenderer;

import p200probe.mixin.DrawContextConsumersAccessor;

/**
 * Test-only client probe for p200: where a tile actually lands, verified per map id.
 *
 * <p>p194 could only say "the second overflow atlas exists and some of its pixels match the map
 * colours", because every one of the 2050 synthetic maps shared one MapState: identical content
 * cannot tell a correct slot from a wrong one. This probe gives every id its own content and reads
 * it back from the atlas image, so a slot mix-up is a hard failure instead of an invisible one.
 *
 * <p>Phases, one HUD frame each:
 * <ol>
 *   <li>allocate 2050 ids through the public update path (1..1024 -&gt; atlas 0, 1025..2048 -&gt;
 *       atlas 1, 2049/2050 -&gt; atlas 2), so the atlas slots are assigned by the real allocator.
 *       Three of them (the first slot of each atlas) are created with their own solid-coloured
 *       MapState: the atlas upload copies whatever state the instance holds, so a shared state
 *       would repaint all three tiles with the last colour on every frame;</li>
 *   <li>tile sweep: for every id, write a 12-bit code (the map id) into row 0 of the shared
 *       MapState, push it through the public update+draw path, then read the code back at the slot
 *       the allocator reported. The three display ids are verified by their solid colour instead.
 *       Every id is checked individually, not sampled;</li>
 *   <li>layout frame: the three display maps - one per atlas - are drawn side by side at fixed GUI
 *       coordinates, and their tiles are read back. {@code verify_layout.py} checks the screenshot
 *       against those coordinates.</li>
 * </ol>
 *
 * <p>All drawing of the sweep happens off-screen (translate -100000) because only the upload side
 * effect matters there; the layout frame is the only one meant to be visible.
 */
public final class AtlasLayoutProbe implements ClientModInitializer {
    private static final int MAP_COUNT = 2050;
    private static final int MAPS_PER_ATLAS = MapAtlasTexture.MAPS_PER_ATLAS;
    private static final int ATLAS_SIZE = MapAtlasTexture.ATLAS_SIZE;

    /** Display maps: first slot of atlas 0, first slot of atlas 1, first slot of atlas 2. */
    private static final int[] LAYOUT_IDS = {1, 1025, 2049};
    /** GUI coordinates (guiScale 2 in the instance options -&gt; 2 screen px per unit). */
    private static final int LAYOUT_X = 8;
    private static final int LAYOUT_Y = 8;
    private static final int LAYOUT_STEP = 136;
    private static final int CODE_BITS = 12;
    private static final long HOLD_MS = 4_000L;
    private static final long EXIT_DELAY_MS = 25_000L;

    private int phase;
    private boolean assigned;
    private boolean layoutLogged;
    private long readyAt;
    private byte[] colors;
    private byte blackByte;
    private byte whiteByte;
    private final int[] layoutColors = new int[LAYOUT_IDS.length];
    private final class_22[] layoutStates = new class_22[LAYOUT_IDS.length];

    @Override
    public void onInitializeClient() {
        HudRenderCallback.EVENT.register((context, tickCounter) -> step(context));
        ClientTickEvents.END_CLIENT_TICK.register(this::maybeAssign);
        Thread stopper = new Thread(() -> {
            try {
                Thread.sleep(EXIT_DELAY_MS);
            } catch (InterruptedException ignored) {
                return;
            }
            class_310 client = class_310.method_1551();
            System.out.println("[p200-probe] requesting client stop");
            client.method_18859(client::method_1592);
        }, "p200-stop");
        stopper.setDaemon(true);
        stopper.start();
    }

    private void step(class_332 context) {
        class_310 client = class_310.method_1551();
        class_638 world = client.field_1687;
        if (!assigned || world == null || client.field_1724 == null) {
            return;
        }
        switch (this.phase) {
            case 0 -> {
                this.phase = 1;
                logAtlases(client);
            }
            case 1 -> {
                this.phase = 2;
                sweepTiles(client, context, world);
            }
            default -> drawLayout(client, context, world);
        }
    }

    /** Allocate every id once, so the atlas/slot assignment is the allocator's own decision. */
    private void maybeAssign(class_310 client) {
        if (this.assigned) {
            return;
        }
        class_638 world = client.field_1687;
        if (world == null || client.field_1724 == null) {
            return;
        }
        class_22 state = world.method_17891(new class_9209(1));
        if (state == null) {
            return;
        }
        // Hold still for a few seconds before the allocation. The memory cost of three 4096^2
        // images is only separable if the process is sampled before and after; the allocation
        // itself takes ~200 ms, which is shorter than any useful sampling period.
        if (this.readyAt == 0L) {
            this.readyAt = System.currentTimeMillis();
            Runtime rt = Runtime.getRuntime();
            System.out.println("[p200-probe] pre-atlas hold=4s atlases=0"
                    + " heap-used=" + ((rt.totalMemory() - rt.freeMemory()) >> 20) + " MiB");
            return;
        }
        if (System.currentTimeMillis() - this.readyAt < HOLD_MS) {
            return;
        }
        this.assigned = true;
        this.colors = state.field_122;
        for (int i = 0; i < LAYOUT_IDS.length; i++) {
            byte colorByte = layoutByte(i);
            this.layoutColors[i] = class_3620.method_38480(colorByte & 0xFF);
            class_22 own = class_22.method_32362((byte) 0, false, state.field_118);
            // Assign the buffer instead of filling whatever the factory allocated: the 16384-byte
            // array is the only thing the atlas upload reads, so its size must not be assumed.
            own.field_122 = new byte[128 * 128];
            java.util.Arrays.fill(own.field_122, colorByte);
            this.layoutStates[i] = own;
        }
        class_330 renderer = client.field_1773.method_3194();
        long started = System.nanoTime();
        for (int id = 1; id <= MAP_COUNT; id++) {
            int slot = layoutSlot(id);
            renderer.method_1769(new class_9209(id), slot >= 0 ? this.layoutStates[slot] : state);
        }
        IMapRenderer hooks = (IMapRenderer) renderer;
        Runtime rt = Runtime.getRuntime();
        System.out.println("[p200-probe] allocated " + MAP_COUNT + " ids in "
                + (System.nanoTime() - started) / 1_000_000 + " ms"
                + " heap-used=" + ((rt.totalMemory() - rt.freeMemory()) >> 20) + " MiB"
                + " atlases=" + countAtlases(hooks)
                + " atlasOf1=" + atlasOf(hooks, 1)
                + " atlasOf1024=" + atlasOf(hooks, 1024)
                + " atlasOf1025=" + atlasOf(hooks, 1025)
                + " atlasOf2048=" + atlasOf(hooks, 2048)
                + " atlasOf2049=" + atlasOf(hooks, 2049)
                + " atlasOf2050=" + atlasOf(hooks, MAP_COUNT));
    }

    private void logAtlases(class_310 client) {
        IMapRenderer hooks = (IMapRenderer) client.field_1773.method_3194();
        int atlases = countAtlases(hooks);
        long bytes = 0L;
        for (int id = 0; id < atlases; id++) {
            MapAtlasTexture atlas = hooks.immediatelyFast$getMapAtlasTexture(id);
            class_1011 image = atlas == null ? null : atlas.getTexture().method_4525();
            if (image == null) {
                System.out.println("[p200-probe] atlas" + id + " image MISSING");
                continue;
            }
            // The buffer size is measured, not assumed: reading the last valid pixel proves the
            // image is at least ATLAS_SIZE square, and one past it throws.
            image.method_4315(ATLAS_SIZE - 1, ATLAS_SIZE - 1);
            boolean outOfBounds;
            try {
                image.method_4315(ATLAS_SIZE, ATLAS_SIZE);
                outOfBounds = false;
            } catch (RuntimeException expected) {
                outOfBounds = true;
            }
            long size = (long) ATLAS_SIZE * ATLAS_SIZE * 4;
            bytes += size;
            System.out.println("[p200-probe] atlas" + id + " image " + ATLAS_SIZE + "x" + ATLAS_SIZE
                    + " last-pixel-ok=true past-end-throws=" + outOfBounds
                    + " bytes=" + size + " identifier=" + atlas.getIdentifier());
        }
        Runtime rt = Runtime.getRuntime();
        System.out.println("[p200-probe] atlas images=" + atlases + " native-bytes=" + bytes
                + " (" + (bytes >> 20) + " MiB)"
                + " heap-used=" + ((rt.totalMemory() - rt.freeMemory()) >> 20) + " MiB"
                + " heap-max=" + (rt.maxMemory() >> 20) + " MiB");
    }

    /**
     * Write a unique 12-bit code into row 0 of the shared MapState, push it through update+draw,
     * then read it back at the slot the allocator reported for that id.
     */
    private void sweepTiles(class_310 client, class_332 context, class_638 world) {
        class_330 renderer = client.field_1773.method_3194();
        IMapRenderer hooks = (IMapRenderer) renderer;
        this.blackByte = extremeByte(true);
        this.whiteByte = extremeByte(false);
        class_22 state = world.method_17891(new class_9209(1));
        class_4597.class_4598 consumers =
                ((DrawContextConsumersAccessor) (Object) context).mcbridge$field_44658();
        class_4587 pose = context.method_51448();
        byte base = (byte) 0x20;   // a mid palette shade, only so untouched cells are uniform
        long started = System.nanoTime();
        int mappingMismatch = 0;
        StringBuilder mappingDetail = new StringBuilder();
        for (int id = 1; id <= MAP_COUNT; id++) {
            int expected = expectedMapping(id);
            int actual = hooks.immediatelyFast$getAtlasMapping(id);
            if (actual != expected) {
                mappingMismatch++;
                if (mappingMismatch <= 5) {
                    mappingDetail.append(" id=").append(id).append(" exp=").append(expected)
                            .append(" act=").append(actual);
                }
            }
            int slot = layoutSlot(id);
            if (slot < 0) {
                writeCode(id, base);
            }
            renderer.method_1769(new class_9209(id), state);
            pose.method_22903();
            pose.method_22904(-100000.0, -100000.0, 0.0);
            renderer.method_1773(pose, consumers, new class_9209(id),
                    slot >= 0 ? this.layoutStates[slot] : state, false, 15728880);
            pose.method_22909();
        }
        long swept = System.nanoTime();
        int checked = 0;
        int mismatched = 0;
        StringBuilder detail = new StringBuilder();
        for (int id = 1; id <= MAP_COUNT; id++) {
            int mapping = hooks.immediatelyFast$getAtlasMapping(id);
            MapAtlasTexture atlas = mapping < 0 ? null
                    : hooks.immediatelyFast$getMapAtlasTexture(mapping >> 16);
            class_1011 image = atlas == null ? null : atlas.getTexture().method_4525();
            if (image == null) {
                mismatched++;
                if (detail.length() < 300) {
                    detail.append(" id=").append(id).append(" mapping=").append(mapping).append(';');
                }
                continue;
            }
            int tileX = (mapping >> 8 & 0xFF) * MapAtlasTexture.MAP_SIZE;
            int tileY = (mapping & 0xFF) * MapAtlasTexture.MAP_SIZE;
            int slot = layoutSlot(id);
            boolean ok = slot >= 0
                    ? solidTileMatches(image, tileX, tileY, this.layoutColors[slot])
                    : codeMatches(image, tileX, tileY, id);
            if (!ok) {
                mismatched++;
                if (detail.length() < 300) {
                    detail.append(" id=").append(id).append(" at ").append(mapping >> 16)
                            .append(':').append(tileX).append(',').append(tileY).append(';');
                }
                continue;
            }
            checked++;
        }
        System.out.println("[p200-probe] tile-sweep ids=" + MAP_COUNT
                + " mapping-mismatch=" + mappingMismatch + mappingDetail
                + " pixel-verified=" + checked
                + " pixel-mismatch=" + mismatched + detail
                + " layout-ids-solid-verified=" + LAYOUT_IDS.length
                + " write-ms=" + (swept - started) / 1_000_000
                + " verify-ms=" + (System.nanoTime() - swept) / 1_000_000
                + " atlas-size=" + ATLAS_SIZE + " maps-per-atlas=" + MAPS_PER_ATLAS);
    }

    private void writeCode(int id, byte base) {
        java.util.Arrays.fill(this.colors, base);
        for (int bit = 0; bit < CODE_BITS; bit++) {
            boolean one = (id & (1 << bit)) != 0;
            this.colors[bit] = one ? this.whiteByte : this.blackByte;
        }
    }

    private boolean codeMatches(class_1011 image, int tileX, int tileY, int id) {
        int white = class_3620.method_38480(this.whiteByte & 0xFF);
        int black = class_3620.method_38480(this.blackByte & 0xFF);
        for (int bit = 0; bit < CODE_BITS; bit++) {
            boolean one = (id & (1 << bit)) != 0;
            int expected = one ? white : black;
            if (image.method_4315(tileX + bit, tileY) != expected) {
                return false;
            }
        }
        return true;
    }

    /** The display tiles are a single flat colour, so three points are enough. */
    private static boolean solidTileMatches(class_1011 image, int tileX, int tileY, int expected) {
        return image.method_4315(tileX, tileY) == expected
                && image.method_4315(tileX + 127, tileY + 127) == expected
                && image.method_4315(tileX + 64, tileY + 64) == expected;
    }

    /** Strongest dark/light palette entries, so the code cells cannot be confused. */
    private static byte extremeByte(boolean darkest) {
        int best = -1;
        int bestLum = darkest ? Integer.MAX_VALUE : Integer.MIN_VALUE;
        for (int b = 0; b < 256; b++) {
            int c = class_3620.method_38480(b);
            int lum = (int) (0.299 * (c & 0xFF) + 0.587 * ((c >> 8) & 0xFF)
                    + 0.114 * ((c >> 16) & 0xFF));
            if (darkest ? lum < bestLum : lum > bestLum) {
                bestLum = lum;
                best = b;
            }
        }
        return (byte) best;
    }

    /** Solid palette colour per display map: the channel-dominant entry for red/green/blue. */
    private static byte layoutByte(int which) {
        int best = 0;
        int bestScore = Integer.MIN_VALUE;
        for (int b = 0; b < 256; b++) {
            int c = class_3620.method_38480(b);
            // method_38480 packs 0xAABBGGRR on 1.21.1: the red channel is the low byte. Reading it
            // as ARGB is what made the first layout frame look channel-swapped.
            int r = c & 0xFF;
            int g = (c >> 8) & 0xFF;
            int bl = (c >> 16) & 0xFF;
            int score = switch (which) {
                case 0 -> r - Math.max(g, bl);
                case 1 -> g - Math.max(r, bl);
                default -> bl - Math.max(r, g);
            };
            if (score > bestScore) {
                bestScore = score;
                best = b;
            }
        }
        return (byte) best;
    }

    private void drawLayout(class_310 client, class_332 context, class_638 world) {
        class_330 renderer = client.field_1773.method_3194();
        class_4597.class_4598 consumers =
                ((DrawContextConsumersAccessor) (Object) context).mcbridge$field_44658();
        class_4587 pose = context.method_51448();
        for (int i = 0; i < LAYOUT_IDS.length; i++) {
            pose.method_22903();
            pose.method_22904(LAYOUT_X + i * LAYOUT_STEP, LAYOUT_Y, 0.0);
            renderer.method_1773(pose, consumers, new class_9209(LAYOUT_IDS[i]),
                    this.layoutStates[i], false, 15728880);
            pose.method_22909();
        }
        if (!this.layoutLogged) {
            this.layoutLogged = true;
            IMapRenderer hooks = (IMapRenderer) renderer;
            net.minecraft.class_1041 window = client.method_22683();
            int scale = (int) Math.round(window.method_4495());
            System.out.println("[p200-probe] layout-tiles" + tileReport(hooks)
                    + " atlas-count=" + countAtlases(hooks));
            System.out.println("[p200-probe] layout-drawn guiScale=" + window.method_4495()
                    + " scale=" + scale
                    + " framebuffer=" + window.method_4480() + "x" + window.method_4507()
                    + " gui=" + window.method_4486() + "x" + window.method_4502()
                    + " rects=" + describeRects(scale)
                    + " argb=" + java.util.Arrays.toString(this.layoutColors));
        }
    }

    /** Reads the tile corners of each display map straight out of the atlas image. */
    private String tileReport(IMapRenderer hooks) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < LAYOUT_IDS.length; i++) {
            int id = LAYOUT_IDS[i];
            int mapping = hooks.immediatelyFast$getAtlasMapping(id);
            if (mapping < 0) {
                sb.append(" map").append(id).append("=unassigned");
                continue;
            }
            MapAtlasTexture atlas = hooks.immediatelyFast$getMapAtlasTexture(mapping >> 16);
            class_1011 image = atlas == null ? null : atlas.getTexture().method_4525();
            if (image == null) {
                sb.append(" map").append(id).append("=noimage");
                continue;
            }
            int tileX = (mapping >> 8 & 0xFF) * MapAtlasTexture.MAP_SIZE;
            int tileY = (mapping & 0xFF) * MapAtlasTexture.MAP_SIZE;
            sb.append(" map").append(id).append("=atlas").append(mapping >> 16)
                    .append('@').append(tileX).append(',').append(tileY)
                    .append(" 0x").append(String.format("%08X", image.method_4315(tileX, tileY)))
                    .append(" expected 0x").append(String.format("%08X", this.layoutColors[i]));
        }
        return sb.toString();
    }

    private String describeRects(int scale) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < LAYOUT_IDS.length; i++) {
            if (i > 0) {
                sb.append(';');
            }
            int x = LAYOUT_X + i * LAYOUT_STEP;
            sb.append("map").append(LAYOUT_IDS[i]).append('@')
                    .append(x * scale).append(',').append(LAYOUT_Y * scale).append('+')
                    .append(128 * scale);
        }
        return sb.toString();
    }

    /** Index of a display map inside LAYOUT_IDS, or -1. */
    private static int layoutSlot(int id) {
        for (int i = 0; i < LAYOUT_IDS.length; i++) {
            if (LAYOUT_IDS[i] == id) {
                return i;
            }
        }
        return -1;
    }

    private static int expectedMapping(int id) {
        int index = id - 1;
        int atlas = index / MAPS_PER_ATLAS;
        int slot = index % MAPS_PER_ATLAS;
        return atlas << 16 | (slot % 32) << 8 | (slot / 32);
    }

    private static int atlasOf(IMapRenderer hooks, int id) {
        int mapping = hooks.immediatelyFast$getAtlasMapping(id);
        return mapping < 0 ? -1 : mapping >> 16;
    }

    private static int countAtlases(IMapRenderer hooks) {
        int n = 0;
        while (n < 64 && hooks.immediatelyFast$getMapAtlasTexture(n) != null) {
            n++;
        }
        return n;
    }
}
