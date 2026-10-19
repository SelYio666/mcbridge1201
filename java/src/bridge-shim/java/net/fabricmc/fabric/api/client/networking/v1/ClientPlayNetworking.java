package net.fabricmc.fabric.api.client.networking.v1;

import net.fabricmc.fabric.api.networking.v1.PacketSender;
import net.minecraft.class_2540;
import net.minecraft.class_310;
import net.minecraft.class_634;

/**
 * Legacy 1.20.1 handler shape kept only so converted mods' lambdas link on 1.21.1.
 *
 * <p>Only the nested {@code PlayChannelHandler} class is embedded in patched jars; the outer
 * class is intentionally not shipped, so the real Fabric API class is never shadowed.
 */
public final class ClientPlayNetworking {
    private ClientPlayNetworking() {
    }

    public interface PlayChannelHandler {
        void receive(class_310 client, class_634 handler, class_2540 buf, PacketSender sender);
    }
}
