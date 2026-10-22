package net.raphimc.immediatelyfast.feature.batching;

import java.util.SequencedMap;
import net.minecraft.class_1921;
import net.minecraft.class_4597;
import net.minecraft.class_9799;

/** Public-constructor Immediate used for the "no batching" entity consumers. */
public class SimpleImmediate extends class_4597.class_4598 {

    public SimpleImmediate(class_9799 allocator, SequencedMap<class_1921, class_9799> layerBuffers) {
        super(allocator, layerBuffers);
    }
}
