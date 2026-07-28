# Problem Factory 开发日志 — Day 1（2026-07-27）

> 记录本次 session 做了什么、为什么这样做、结果意味着什么。
> 位置：`tracks/agent-kb/solutions/problem-factory/`

---

## 一、做了什么（按顺序）

| 步骤 | 产物 | 说明 |
|---|---|---|
| 1 | `pf/ed.py`（~50 行） | 最小 XXZ+J2 精确对角化：Sz=0 对称 sector 内构稀疏矩阵，dense 对角化取最低两个本征值 |
| 2 | **物理验证** | 用 Bethe ansatz 精确解检验 ED 正确性（见第三节） |
| 3 | `pf/cards.py`（~60 行） | 模板生成 5 张 problem cards + 指纹去重（接口 A） |
| 4 | `pf/static_fire.py`（~40 行） | 第一性原理检查：Bethe oracle + Sz 守恒 |
| 5 | `pf/probe.py`（~50 行） | hop test：跑完整 (L, Δ, J2) 网格，计算 decisiveness 指标 |
| 6 | `pf/verdict.py`（~40 行） | 三态判定（survivor/deferred/dead）+ 战报生成 |
| 7 | `run_demo.py`（~60 行） | 唯一入口，串联全管线 |
| 8 | **抓到并修正一个判据 bug** | deferred 判据初版物理上错误（见第五节） |
| 9 | `AGENTS.md` | scoped 工作约定：schema、verdict 规则、代码风格 |
| 10 | `README.md` | 火箭测试叙事文档 |

运行产物：`cards/*.yaml`（5 张卡）、`results/telemetry.jsonl`（每卡一条遥测）、`results/report.md`（战报）。

---

## 二、架构：火箭测试三级裁判

核心主张：**问题的好坏不由 agent 讨论决定，由实验数字决定**（回应指导老师"多 agent 对抗会模棱两可"的批评）。

```
cards.py 生成 5 张卡（YAML，gate 已冻结）
        │
        ▼
  指纹去重 ────────────────→ dead（duplicate_fingerprint）
        │
        ▼
  static fire（第一性原理）
  · Bethe oracle：L=10, Δ=1 的 E/N 对精确解 −0.4431
  · Sz 守恒：[H, Sz_tot] = 0
        │ 失败 → dead（setup_error）
        ▼
  hop test（实验测量）
  · 跑完卡上声明的全部 (L, Δ, J2) 网格，不许跳点
  · decisiveness = 扰动引起的 gap 移动 / baseline 自身的有限尺寸噪声
        │
        ▼
  三态 verdict
  · decisiveness ≥ 2.0        → survivor（信号决定性）
  · 0.5 ≤ decisiveness < 2.0  → deferred（可见但不决定性，建议放大发射）
  · decisiveness < 0.5        → dead（no_signal）
        │
        ▼
  telemetry.jsonl + report.md（每张卡都有机器可读记录，死亡必须带死因）
```

设计原则：

1. **Gate-first**：没有冻结 gate 的卡不允许占"发射窗口"；gate 在求解后绝不修改
2. **失败是资产**：dead 卡和死因是启发式库的种子，不是垃圾
3. **deferred 是一等公民**：smoke 测不准的问题不冤杀也不放行，带着"值得放大"的建议回到人面前
4. **代码极简**：管线内零 try/except，schema 是约定不是运行时校验，格式错了就让它响亮地崩

---

## 三、物理正确性验证

ED 求解器本身先过了自己的 static fire：

```
L=6   E0/L = -0.467129   gap = 0.6847
L=8   E0/L = -0.456387   gap = 0.5227
L=10  E0/L = -0.451545   gap = 0.4232
Bethe ansatz 热力学极限 E/N = -0.443147
```

E/N 从上方随 L 收敛到精确解（有限尺寸修正 ~1/L²），gap 按 1/L 收缩——正是无磁隙 Heisenberg 链的已知行为。求解器可信，后面的判决才有意义。

---

## 四、首飞结果

```
launched 5: survivor 1, deferred 1, dead 3
```

| 卡 | 设计意图 | 判决 | 机制 |
|---|---|---|---|
| xxz-j2-gap-001 | J2=0.3 强扰动 | **survivor** | decisiveness 5.49，信号远压过噪声 |
| xxz-j2-deferred-004 | J2=0.05 弱扰动 | **deferred** | 0.93，看得见但不够决定性 |
| xxz-j2-tiny-002 | J2=0.001 极弱扰动 | dead | no_signal：0.02，不可见 |
| xxz-bad-setup-003 | pauli/spin 约定混淆（能量差 4×） | dead | setup_error：Bethe oracle 在 static fire 阶段拦截，没浪费 hop 机时 |
| xxz-j2-gap-001-dup | 与 001 完全同构 | dead | duplicate_fingerprint：零物理成本拦截 |

关键观察：**三种死法各由不同机制检出**（去重 / 第一性原理 / 实验信号），这正是系统"有牙齿"的证据。交付物不是那个 survivor，而是整个判决过程的可信度。

---

## 五、首飞抓到的判据 bug（重要教训）

初版 deferred 判据要求"effect 随 L 增长"，结果把 J2=0.05 卡冤杀了（gradient = −0.0017）。

分析：**无磁隙相里，gap 本身 ~1/L，扰动引起的 gap 移动也同样 ~1/L 收缩**。所以 raw effect 随 L 下降是物理正确的行为，不代表信号消失。"effect 必须随 L 增长"对 gap 类观测量是错的判据。

修正：deferred 只看 decisiveness 区间（0.5–2.0），gradient 保留在 telemetry 里供人参考，不做硬判据。

元教训：**判据本身也要被实验检验**——这正是"用实验当裁判"相比"用讨论当裁判"的优势：讨论只会互相附和，实验会当场反驳你。

---

## 六、分工接口（明天接头用）

两个 schema 已冻结在 `AGENTS.md`：

- **接口 A（problem card YAML）**：`pf/cards.py` 是手工 fixtures，换队友的生成器或 LLM 生成器只需替换 `generate()`，schema 不变
- **接口 B（telemetry JSONL）**：`problem_id / verdict / reason / metrics`，队友的任何 probe runner 产出同样格式即可汇合

## 七、Day 2 待办

- [ ] **出题人**：从论文挖掘结构性锚点（对称性条件、守恒律、已知极限、参数绑定）生成 idea → 结晶器强制补齐 gate → 补不出来的记死因 uncrystallizable
- [ ] **value 校准**：decisiveness ≠ 价值；用文献中已知好/平庸问题回测管线排序，区分 idea（无 gate）与 question（可判定）
- [ ] deferred 卡上集群放大（L=12–16，`scripts/harness_array_sbatch.sh`）
- [ ] 与队友接头：外部卡片倒入本管线
- [ ] 死因分类 → heuristic library
- [ ] 更新 `docs/design/` 方法论文档（当前还是听证会旧版）
