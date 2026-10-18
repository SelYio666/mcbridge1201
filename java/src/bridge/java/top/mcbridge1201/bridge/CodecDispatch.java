package top.mcbridge1201.bridge;

import java.util.function.Function;
import java.util.stream.Stream;

import com.mojang.datafixers.util.Pair;
import com.mojang.serialization.Codec;
import com.mojang.serialization.DataResult;
import com.mojang.serialization.DynamicOps;
import com.mojang.serialization.KeyCompressor;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.MapDecoder;
import com.mojang.serialization.MapEncoder;
import com.mojang.serialization.MapLike;
import com.mojang.serialization.RecordBuilder;

/**
 * 1.20.1 {@code Codec.dispatch(Function, Function<Codec>)} vs 1.21.1
 * {@code Codec.dispatch(Function, Function<MapCodec>)}.
 *
 * <p>The old second function returns a Codec. This bridge wraps that Codec as a MapCodec
 * without {@code assumeMapUnsafe}: map input is materialized with
 * {@code DynamicOps.createMap} and decoded by the Codec; encoding delegates to the Codec and
 * copies the resulting map entries into the RecordBuilder. The wrapper has empty keys and an
 * empty key compressor, which is safe for dispatch values (the dispatch key is handled by
 * {@code Codec.dispatch} itself).
 */
public final class CodecDispatch {
    private CodecDispatch() {}

    @SuppressWarnings({"unchecked", "rawtypes"})
    public static Codec<?> dispatch(Codec codec, Function type, Function codecFn) {
        return codec.dispatch(type, value -> wrap((Codec) codecFn.apply(value)));
    }

    @SuppressWarnings("unchecked")
    private static <A> MapCodec<A> wrap(Codec<A> codec) {
        if (codec instanceof MapCodec.MapCodecCodec<?> existing) {
            return (MapCodec<A>) existing.codec();
        }
        MapEncoder<A> encoder = new MapEncoder<A>() {
            @Override
            public <T> RecordBuilder<T> encode(A input, DynamicOps<T> ops, RecordBuilder<T> prefix) {
                DataResult<T> encoded = codec.encodeStart(ops, input);
                if (encoded.result().isEmpty()) return prefix.withErrorsFrom(encoded);
                DataResult<MapLike<T>> map = ops.getMap(encoded.result().get());
                if (map.result().isEmpty()) return prefix.withErrorsFrom(map);
                for (Pair<T, T> entry : map.result().get().entries().toList()) {
                    prefix.add(entry.getFirst(), entry.getSecond());
                }
                return prefix;
            }

            @Override
            public <T> KeyCompressor<T> compressor(DynamicOps<T> ops) {
                return new KeyCompressor<>(ops, Stream.empty());
            }

            @Override
            public <T> Stream<T> keys(DynamicOps<T> ops) {
                return Stream.empty();
            }
        };
        MapDecoder<A> decoder = new MapDecoder<A>() {
            @Override
            public <T> DataResult<A> decode(DynamicOps<T> ops, MapLike<T> input) {
                T value = ops.createMap(input.entries());
                return codec.decode(ops, value).map(Pair::getFirst);
            }

            @Override
            public <T> KeyCompressor<T> compressor(DynamicOps<T> ops) {
                return new KeyCompressor<>(ops, Stream.empty());
            }

            @Override
            public <T> Stream<T> keys(DynamicOps<T> ops) {
                return Stream.empty();
            }
        };
        return MapCodec.of(encoder, decoder);
    }
}
