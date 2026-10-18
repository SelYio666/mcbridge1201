package top.mcbridge1201.bridge;

import net.minecraft.class_14;
import net.minecraft.class_1922;
import net.minecraft.class_2246;
import net.minecraft.class_2338;
import net.minecraft.class_2680;
import net.minecraft.class_3486;
import net.minecraft.class_3610;
import net.minecraft.class_7;

/**
 * Call-site bridge for the 1.20.1 -> 1.21.1 change of
 * {@code WalkNodeEvaluator.checkNeighbourBlocks}.
 *
 * <p>1.20.1: {@code static BlockPathTypes checkNeighbourBlocks(BlockGetter, BlockPos.MutableBlockPos,
 * BlockPathTypes)}. 1.21.1: {@code static PathType checkNeighbourBlocks(PathfindingContext, int, int,
 * int, PathType)}. The callee's arguments were replaced, not renamed, so the old call site cannot
 * be fixed by a descriptor rewrite alone.
 *
 * <p>Why this is a faithful port instead of a call to the new method: the new method needs a
 * {@code PathfindingContext}, whose only constructor is {@code (CollisionGetter, Mob)}. The old
 * call sites (lithium's {@code PathNodeCache} and its {@code AbstractBlockStateMixin}) pass an
 * arbitrary {@code BlockGetter}, including a synthetic single-block view that is not a
 * {@code CollisionGetter} and has no entity. Fabricating a context would change the semantics and
 * add an entity dependency. This bridge therefore keeps the old neighbour scan and expresses it
 * with the 1.21.1 APIs that still exist (BlockGetter/BlockState/FluidState/Blocks).
 *
 * <p>The old method also mutated the caller's {@link class_2338.class_2339}; that side effect is
 * preserved. The scan is the exact 1.20.1 order: cactus/sweet berry -> DANGER_OTHER, burning block
 * -> DANGER_FIRE, water -> WATER_BORDER, wither rose/pointed dripstone -> DAMAGE_CAUTIOUS; the
 * original type is returned when no neighbour matches.
 */
public final class WalkNodeEvaluatorCheckNeighbourBlocks {
    private WalkNodeEvaluatorCheckNeighbourBlocks() {}

    public static class_7 checkNeighbourBlocks(class_1922 view,
                                               class_2338.class_2339 pos,
                                               class_7 type) {
        int x = pos.method_10263();
        int y = pos.method_10264();
        int z = pos.method_10260();
        for (int dx = -1; dx <= 1; dx++) {
            for (int dy = -1; dy <= 1; dy++) {
                for (int dz = -1; dz <= 1; dz++) {
                    if (dx == 0 && dz == 0) {
                        continue;
                    }
                    pos.method_10103(x + dx, y + dy, z + dz);
                    class_2680 state = view.method_8320(pos);
                    if (state.method_27852(class_2246.field_10029)
                            || state.method_27852(class_2246.field_16999)) {
                        return class_7.field_5; // DANGER_OTHER
                    }
                    if (class_14.method_57082(state)) {
                        return class_7.field_9; // DANGER_FIRE
                    }
                    class_3610 fluid = view.method_8316(pos);
                    if (fluid.method_15767(class_3486.field_15517)) {
                        return class_7.field_4; // WATER_BORDER
                    }
                    if (state.method_27852(class_2246.field_10606)
                            || state.method_27852(class_2246.field_28048)) {
                        return class_7.field_43351; // DAMAGE_CAUTIOUS
                    }
                }
            }
        }
        return type;
    }
}
