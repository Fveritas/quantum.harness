# Problem Factory 开发日志 — Day 1–2（2026-07-27/28）

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

---
---

# Day 2（2026-07-28）

## 一、issue #133 全文重读：被低估的 calibration gate

issue 原文有一条 Day 1 日志没抓住的硬要求：

> Before generating new problems, the generator must **re-derive problems of the same quality class as #124–#128** from the open literature, without access to the originals. If the rubric cannot reconstruct the hand-curated set, it is not trusted on new problems.

结论：校准不是"加分项"，是 issue 明文的信任锚。Day 2 主攻方向因此从"出题人优先"改为**校准优先（造尺子），出题人用尺子量产**。

## 二、校准集画像（#124–#128 的共同指纹）

| # | gate 家族 | 单一标量 |
|---|---|---|
| 124 kagome 能量区间 | certificate（SDP 对偶可行性） | bracket 宽度 ↓ |
| 125 J1-J2 打榜 | fresh_sample（变分自认证） | E/N ↓ |
| 126 AKLT 能隙定理 | interval_arithmetic（Knabe 判据） | 阈值余量 ↑ |
| 127 收缩成本 | cost_arithmetic（确定性 FLOPs） | FLOPs ↓ |
| 128 Trotter 界 | certificate（符号对易子范数） | 可证门数 ↓ |

四条可操作特征：**文献锚（钉死的数字+引用）、证书型 gate、单一标量 merit、可发表单元（超越 SOTA 的陈述）**。

**校准发现 #1（在读论文阶段就浮现）**：Day 1 的 decisiveness gate 属于"统计信号检测"家族，不在 issue 点名的四种证书型 gate 里——不先校准，工厂量产的会是同一偏科家族的问题。

## 三、落地：rubric + 回测（`pf/rubric.py` + `run_calibration.py`，~90 行）

- `pf/rubric.py`：四条指纹检查（presence 层）。**分层声明**：rubric 只查结构存在性；"钉死的数字是否真实、checker 是否真能跑"留给下游 static fire / hop 验证——不把深验证伪装成浅检查。
- `calibration/`：5 个正例（#124–128 手工编码为 candidate YAML）+ 3 个负例。
- 负例设计（阴性对照，呼应 Track 1 教学）：
  - `neg-xxz-signal-detection`：我们自己的 Day 1 卡重新编码 → 必须拒
  - `neg-vague-hubbard`：空洞题（"研究 Hubbard 相图"）→ 四项全挂
  - `neg-anchor-no-scalar`：有文献锚但无标量/无证书 → 检验各检查的独立性

## 四、回测结果

```
calibration: 5/5 positives accepted, 3/3 negatives rejected -> CALIBRATED
```

最有信息量的一条：`neg-xxz-signal-detection`（我们自己的卡）在 4 项检查中挂了 3 项（无文献锚、gate 家族不符、无可发表单元）。**校准发现 #1 现在有了可执行证据**，不再是口头判断。

## 五、对 C（出题人）的设计约束（明天用）

结晶器模板必须按四种 gate 家族分别配置；结构锚点清单里新增必备项：**"文献中已钉死的数字"**。缺此锚的 idea 死因记 `no_literature_anchor`。

## 六、其他记录

- 环境：Track 1 训练顺手装好 `.venv`（pymupdf4llm）和 Julia 1.12.6；Ion.lock 已同步 commit
- **harness 改进候选**：根 `.gitignore` 不忽略 `.venv/`（`make install pdf-render` 的产物），每个新用户都会踩 → 可提炼为 PR 三要素之一的"harness 改进"
- 污染风险对策已定：生成协议只喂原始文献、不喂 issue 文本；隔离声明写进 provenance 日志

## 七、Day 2 剩余 / Day 3 待办

- [ ] 出题人（结晶器按新尺子量产）
- [ ] deferred 卡上集群放大
- [ ] 与队友接头
- [ ] 死因分类 → heuristic library（rubric 拒绝日志是第一批素材）
- [ ] 更新 `docs/design/` 方法论文档
- [ ] `.venv` gitignore 改进项提上 PR 清单

---

## 八、Day 2 下午：#112 实测 → 尺子扩成双质量类

### 隔离协议首测

用户拿来公开 issue #112（陈锟老师出的"局域磁振子侵蚀地图"）考尺子。按既定协议执行：

1. **自我申报**：锯齿链局域磁振子物理（2002–2004 经典文献）在 LLM 训练数据内，声明为污染；issue 文本当天首读，无污染
2. **对策**：编码字段全部可回溯 issue 原文，判决交给 `rubric.py` 确定性代码——LLM 只做搬运，不参与打分

### 一判结果与扩类

旧尺子判决：**REJECTED**（3/4 过，`single_scalar` 挂）。分析：#112 交付物是**曲线族/相图**（侵蚀地图），不是被推进的标量——它和 #124–128 是不同物种：

| | record 类（#124–128） | map 类（#112） |
|---|---|---|
| 交付物 | 一个被推进的标量 | 一族曲线 + 相图 |
| 不可作弊靠 | 证书/确定算术 | 精确整数锚 + 解析 PT 交叉验证 |
| 五条指纹 | 文献锚/证书/单标量/可发表 | 文献锚/证书/**留白声明**/曲线+解析校验/可发表 |

赛道专家亲手出的题不在官方校准集的类里——**校准集 #124–128 的策展偏好被尺子量化出来了**（issue 说的 "partial failure is informative" 的实例）。

### 扩类实现（`pf/rubric.py` v2）

- `grade()` 现在同时算 record / map 两类检查，任一类全过即 accept，返回归属类
- map 类新增两字段：`uncharted`（留白声明，含边界文献）、`merit.curve` + `merit.analytic_check`（曲线族必须带解析牙齿——没牙齿的曲线正是老师批评的"模棱两可"）
- 校准集分 dev（#124–128 + 3 负例）/ held-out test（#112 + 2 个 map 类专属负例）

### 复测结果

```
dev:  5/5 positives（全部 record 类）, 3/3 negatives
test: 1/1 positives（#112 → map 类）, 2/2 negatives -> CALIBRATED
```

两个新负例各只挂该挂的一项（`uncharted_region` / `curve_merit`），新检查项独立性得证。

### 沉淀

- 死因分类法对生成侧的启示：`no_uncharted_region`（没声明留白的地图题）、`no_analytic_teeth`（曲线无解析校验）可入 heuristic library
- 给队友（生成侧）的接口更新：结晶模板现在有两套——record 模板补 `merit.scalar`，map 模板补 `uncharted` + `merit.curve/analytic_check`
