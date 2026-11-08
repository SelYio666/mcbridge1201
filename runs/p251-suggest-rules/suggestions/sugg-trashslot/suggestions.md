# Rule suggestions

plan: work\plan-corpus.json (sha256 946b9827fc11)

| id | kind | confidence | target | note |
|---|---|---|---|---|
| save.retarget | methodRedirect | medium | net/minecraft/class_1799.method_7953 | net.minecraft.world.item.ItemStack.save is method_57379 (Lkp;Ljava/lang/Object;)Ljava/lang/Object; in 1.21.1; descriptor differs, bridge must convert. instance call: bridge receives the receiver as first argument |

## No mechanical draft (needs human decision)

-  net/minecraft/class_1799.method_7915: no of continuation in 1.21.1 net.minecraft.world.item.ItemStack; needs a semantic port, not a mechanical rule
