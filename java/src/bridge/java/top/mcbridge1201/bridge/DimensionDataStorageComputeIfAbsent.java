package top.mcbridge1201.bridge;

import java.util.function.Function;
import java.util.function.Supplier;

import net.minecraft.class_18;
import net.minecraft.class_18.class_8645;
import net.minecraft.class_2487;
import net.minecraft.class_26;
import net.minecraft.class_4284;
import net.minecraft.class_7225;
import net.minecraft.class_7225.class_7874;

/**
 * 1.20.1 DimensionDataStorage.computeIfAbsent(Function,Supplier,String) became
 * computeIfAbsent(SavedData.Factory,String) in 1.20.5+. The bridge rebuilds the Factory the
 * way vanilla's own call sites do (ServerLevel init) and the way silk's native 1.21 build
 * does for its custom saved data: the 1.20.1 load function becomes the deserializer, with the
 * WrapperLookup parameter ignored (1.20.1 semantics had no registry lookup here), and the
 * DataFixTypes slot takes DataFixTypes.LEVEL (class_4284.field_19212) exactly like silk
 * persistence's CompoundSavedData$Companion.createFactory.
 *
 * Suggested by tools/suggest_rules.py (computeifabsent.callsite, high confidence) from the
 * analyzer descMismatch on net/minecraft/class_26.method_17924 in silk-all 1.10.1; the runtime
 * trigger was NoSuchMethodError in silk-persistence's ServerWorldMixin during ServerLevel
 * world load (VeinMiner 2.0.7 + converted silk on Fabric 1.21.1).
 */
@SuppressWarnings({"unchecked", "rawtypes"})
public final class DimensionDataStorageComputeIfAbsent {
    private DimensionDataStorageComputeIfAbsent() {
    }

    public static class_18 adapt(class_26 storage, Function loadFunction, Supplier defaultSupplier,
                                 String name) {
        class_18.class_8645<class_18> factory = new class_18.class_8645<>(
                (Supplier<class_18>) defaultSupplier,
                (java.util.function.BiFunction<class_2487, class_7225.class_7874, class_18>)
                        (tag, lookup) -> (class_18) loadFunction.apply(tag),
                class_4284.field_19212);
        return (class_18) storage.method_17924(factory, name);
    }
}
