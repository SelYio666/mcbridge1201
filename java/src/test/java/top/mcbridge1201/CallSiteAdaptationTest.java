package top.mcbridge1201;

import org.junit.jupiter.api.Test;
import top.mcbridge1201.rules.RuleSet;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertSame;

/** Call-site adaptations must only fire on an exact owner/name/descriptor/opcode match. */
class CallSiteAdaptationTest {

    private static RuleSet.CallSiteAdaptation rule() {
        RuleSet.CallSiteAdaptation a = new RuleSet.CallSiteAdaptation();
        a.id = "test";
        a.sourceOwner = "net/minecraft/class_14";
        a.sourceName = "method_59";
        a.sourceDesc = "(Lnet/minecraft/class_1922;Lnet/minecraft/class_2338$class_2339;Lnet/minecraft/class_7;)"
                + "Lnet/minecraft/class_7;";
        a.sourceOpcode = 184;
        a.targetOwner = "net/minecraft/class_14";
        a.targetName = "method_59";
        a.targetDesc = "(Lnet/minecraft/class_9316;IIILnet/minecraft/class_7;)Lnet/minecraft/class_7;";
        a.bridgeClass = "top/mcbridge1201/bridge/WalkNodeEvaluatorCheckNeighbourBlocks";
        a.bridgeMethod = "checkNeighbourBlocks";
        a.bridgeDesc = a.sourceDesc;
        return a;
    }

    @Test
    void matchesOnlyExactOwnerNameDescriptorAndOpcode() {
        RuleSet rs = new RuleSet();
        RuleSet.CallSiteAdaptation a = rule();
        rs.callSiteAdaptations.add(a);

        assertSame(a, rs.matchCallSite(a.sourceOwner, a.sourceName, a.sourceDesc, 184));
        assertNull(rs.matchCallSite("net/minecraft/class_15", a.sourceName, a.sourceDesc, 184));
        assertNull(rs.matchCallSite(a.sourceOwner, "method_60", a.sourceDesc, 184));
        assertNull(rs.matchCallSite(a.sourceOwner, a.sourceName, a.sourceDesc + "V", 184));
        assertNull(rs.matchCallSite(a.sourceOwner, a.sourceName, a.sourceDesc, 182));
    }

    @Test
    void opcodeZeroMeansAnyCallKind() {
        RuleSet rs = new RuleSet();
        RuleSet.CallSiteAdaptation a = rule();
        a.sourceOpcode = 0;
        rs.callSiteAdaptations.add(a);

        assertSame(a, rs.matchCallSite(a.sourceOwner, a.sourceName, a.sourceDesc, 184));
        assertSame(a, rs.matchCallSite(a.sourceOwner, a.sourceName, a.sourceDesc, 182));
    }

    @Test
    void generatedBridgeNamesAreRecognised() {
        assertEquals(true, top.mcbridge1201.rules.BridgeGenerator.isGenerated(
                top.mcbridge1201.rules.BridgeGenerator.ITEM_PREDICATE_ANY));
        assertEquals(false, top.mcbridge1201.rules.BridgeGenerator.isGenerated(
                "top/mcbridge1201/bridge/WalkNodeEvaluatorCheckNeighbourBlocks"));
    }
}
