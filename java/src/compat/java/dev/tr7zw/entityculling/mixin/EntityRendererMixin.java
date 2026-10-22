/*
 * mcbridge1201 compatibility port for EntityCulling's EntityRendererMixin (target 1.21.1).
 *
 * This is OUR code, not the upstream mod: the package/class name deliberately matches the
 * original mixin so the patched jar entry keeps the class name the mixin config expects.
 *
 * Why a port is needed: the original (built for 1.20.1/1.20.4) declares a five-parameter
 * @Shadow method_3926; since 1.20.5 the target method gained a trailing `float delta`, so
 * the mixin was stripped as load-bearing. This port declares the 1.21.1 shadow and
 * forwards the extra argument. The rule also re-adds the class to entityculling.mixins.json.
 */
package dev.tr7zw.entityculling.mixin;

import dev.tr7zw.entityculling.access.EntityRendererInter;
import net.minecraft.class_1297;
import net.minecraft.class_238;
import net.minecraft.class_2561;
import net.minecraft.class_4587;
import net.minecraft.class_4597;
import net.minecraft.class_897;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;

@Mixin(class_897.class)
public abstract class EntityRendererMixin<T extends class_1297> implements EntityRendererInter<T> {

    @Shadow
    protected abstract boolean method_3921(T entity);

    @Shadow
    protected abstract void method_3926(T entity, class_2561 component, class_4587 poseStack,
                                         class_4597 buffers, int light, float delta);

    @Override
    public boolean shadowShouldShowName(T entity) {
        return method_3921(entity);
    }

    @Override
    public void shadowRenderNameTag(T entity, class_2561 component, class_4587 poseStack,
                                    class_4597 buffers, int light, float delta) {
        method_3926(entity, component, poseStack, buffers, light, delta);
    }

    @Override
    public boolean entityCullingIgnoresCulling(T entity) {
        return entity.field_5985;
    }

    @Override
    public class_238 entityCullingGetCullingBox(T entity) {
        return entity.method_5830();
    }
}
