package net.fabricmc.fabric.api.networking.v1;

import net.minecraft.class_2540;
import net.minecraft.class_3222;
import net.minecraft.class_3244;
import net.minecraft.server.MinecraftServer;

/**
 * Legacy 1.20.1 server handler shape kept only so converted mods' lambdas link on 1.21.1.
 *
 * <p>Only the nested {@code PlayChannelHandler} class is embedded in patched jars; the outer class
 * is never shipped, so the real Fabric API class is not shadowed.
 */
public final class ServerPlayNetworking {
    private ServerPlayNetworking() {
    }

    public interface PlayChannelHandler {
        void receive(MinecraftServer server, class_3222 player, class_3244 handler,
                     class_2540 buf, PacketSender sender);
    }
}
