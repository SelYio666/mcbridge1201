package top.mcbridge1201;

import org.junit.jupiter.api.Test;
import top.mcbridge1201.rules.RuleSet;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

/** Loads a rule file from disk to prove the JSON shape the CLI sees is the shape tests assume. */
class RuleSetLoadTest {
    @Test
    void parsesInsertBeforeCallRules() throws Exception {
        Path json = Path.of("..", "work", "tmp", "probe-rule", "probe.json");
        assumeTrue(Files.isRegularFile(json), "probe rule not present");
        RuleSet rs = RuleSet.load(json);
        assertEquals(1, rs.insertBeforeCalls.size(), "insertBeforeCalls must be parsed");
        RuleSet.InsertBeforeCall r = rs.insertBeforeCalls.get(0);
        assertEquals("java/util/function/Supplier", r.matchOwner);
        assertEquals("get", r.matchName);
        assertEquals("()Ljava/lang/Object;", r.matchDesc);
        assertEquals(185, r.matchOpcode);
        assertEquals(0, r.loadLocal);
        assertEquals(List.of(1), r.loadLocals);
        assertEquals("getWithKey", r.replaceMethod);
    }
}
