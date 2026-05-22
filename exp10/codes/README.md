# exp10 Code Pointers

`exp10` 不复制 solver 源码，避免产生多个分叉版本。

当前 Layer-A 全量公平实验使用已有代码：

| role | solver family | path |
|---|---|---|
| DBS baseline | Deep | `../../exp-4/codes/Dual-Deep/dual-deep` |
| DBS + Ant-Q | Deep | `../../exp-4/codes/Dual-Deep-v6/dual-deep-v6` |
| DBS baseline | Fast | `../../exp-2/codes/Dual-Fast/dual-fast` |
| DBS + Ant-Q | Fast | `../../exp-2/codes/Dual-Fast-v19/dual-fast-v19` |

Guarded Ant-Q 尚未实现。等 guard 规则通过 T1_RISK pilot 后，再新增代码或 wrapper。

