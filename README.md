# Multi-Dev-Os · 团队并发协作开发范式（可复用框架）

把一个项目变成「**身份 + 五台 + 并发 Goal Loop**」驱动的协作仓库：多 developer 各写各的 folder、**并发零冲突**，全局视图脚本现生成，导航 map 只定位、实时看原文 + 代码。范式细节见 `dev/README.md`。

---

## 结构与逻辑（详解）

![Multi-Dev-Os 结构图](docs/structure.svg)

![Multi-Dev-Os 逻辑图](docs/logic.svg)

> 上为可视版（GitHub 直接渲染）;下方字符画是同内容的细节详解。

### 一、完整目录树

```
<project>/
├── CLAUDE.md                       ← 根路由:agent 开局先读它       [框架·勿改]
├── .gitignore                      ← 含 dev/.identity(本机身份不入库)
└── dev/                            ← 团队并发开发 OS（整套）
    │
    ├─❶ 全局单文件（committed · 全队共享一份）
    │   ├── GOAL.md                 终态契约(北极星→子系统→工程标准)   [项目填·慢变]
    │   ├── RULES.md                OS 通用铁律 §0–§8                  [框架·勿改]
    │   ├── RULES.project.md        本项目红线/致命错误/性能标准        [项目填]
    │   ├── CODEMAP.md              项目代码结构图(给 agent 导航)      [项目填]
    │   ├── TEAM.md                 花名册:developer_id ↔ role        [项目填]
    │   └── README.md               OS 规约总纲(怎么建)              [框架·勿改]
    │
    ├─❷ 本机身份（不入库 · 每人各异）
    │   └── .identity               = 你的 developer_id(须 ∈ TEAM)   [本地·gitignore]
    │
    ├─❸ per-developer 状态（committed · 各写各文件 → 并发零冲突）
    │   ├── state/{dev}/state.md          现状 gap(从本地代码来;🟡≠✅)
    │   ├── board/{dev}/board.md          本人活跃卡(生成视图)
    │   ├── log/{dev}/log.md              滚动日志(每 session 一行)
    │   ├── experience/{dev}/...          技术坑经验库
    │   ├── decisions/{dev}/...           决策(canonical 归 leader)
    │   └── issues/{dev}/...              问题/风险登记
    │        ▲ 读任何一类 = 遍历 {type}/*/ 聚合(靠 ❽ 导航 map 快定位)
    │
    ├─❹ 任务台 tasks/
    │   ├── pool/{uuid8}/TASK.md          待分配(owner: wait)
    │   ├── {dev}/{uuid8}/TASK.md         已分配给 dev(active)
    │   ├── {dev}/done/{uuid8}/TASK.md    落档
    │   └── _templates/TASK.md            卡模板(YAML frontmatter)    [框架·勿改]
    │
    ├─❺ 研究台 research/（也 per-dev）
    │   ├── ideas/{dev}/  active/{dev}/  findings/{dev}/   灵感→深挖→设计
    │   ├── INDEX.md  TRACE.md            全局聚合视图(溯源)          [项目填]
    │   ├── WORKFLOW.md                   研究调查方法                 [框架·勿改]
    │   └── archive/                      重资料(read-on-demand)
    │
    ├─❻ 执行台 exec/
    │   └── HANDOFF.md                    新 session 入口提示词        [框架·勿改]
    │
    ├─❼ 闸 + 脚本 scripts/（全框架·勿改,除 validate_project）
    │   ├── validate_dev.py               结构+团队+DAG 自检(唯一阻断闸)
    │   ├── validate_project.py           项目锚点/旧路径              [项目填]
    │   ├── build_board.py                生成本人 board
    │   ├── build_dev_map.py              生成 DEVMAP + 各 _NAV
    │   ├── build_ledger.py               全含量任务账本
    │   ├── build_card_counters.py        OQ 计数器派生
    │   └── build_log_index.py            全员 LOG 统一索引
    │
    └─❽ 生成的导航（脚本现生成 · 勿手改 · 只定位）
        ├── DEVMAP.md                     全员→卡(按 developer + area)
        └── {type}/_NAV.md                各 folder 的 developer→文件 索引
```

### 二、身份与角色

```
TEAM.md  developer_id ──▶ role
                          ├── leader     ×1(唯一)  ┐ 可【分配】(pool→{dev})
                          ├── admin      ×N         ┘ + 可【land】(合并进 main)
                          └── developer  ×N           ── 只写 tasks/{自己}/ 名下卡 + self-review

.identity(本机·不入库) = 你是谁;     canonical/全局决策 → 归 leader 的 decisions/{leader}/
```

### 三、任务卡生命周期 + id 体系

```
逻辑 id = {owner}-{uuid}      物理:文件夹名 = uuid 前 8 位 hex(纯,不带前缀)
owner = wait(在 pool) | developer_id     依赖锚 全 32 位 uuid(前缀可变 · uuid 永不变)

  三晋升源                       待分配池            分配(仅 leader/admin)         落档
┌──────────────┐               ┌──────────┐      = 改归属文件夹          ┌───────────────────┐
│ 研究台 findings │─┐            │  tasks/  │   pool/{uuid8}/             │ tasks/{dev}/done/  │
│ GOAL.md gap    │─┼─mint uuid─▶│  pool/   │──────────────────────────▶│  {uuid8}/          │
│ dev×claude 交互 │─┘            │ {uuid8}/ │   →  tasks/{dev}/{uuid8}/   └─────────▲─────────┘
└──────────────┘               └──────────┘      (active · owner:dev)            │ 完成
                                 owner:wait        ────────────────────────────────┘

全部卡的 depends_on 组成有向无环图(DAG),validate 守【无环 + 无悬空】:
        A ──▶ B ──▶ D          连通分量 = 可并行的工作簇
             ╱                  (拆分/分配算法 = 后续 skill;DAG 校验已就位)
        C ──╯
        E ──▶ F ──▶ G
```

### 四、并发为什么零冲突 + 全局怎么读

```
单写者 dev-os:单一 STATE / BOARD / DECISIONS 文件
              └─ 多人并发改同一文件 = git 冲突地狱
        │ 升级
        ▼
团队 dev-os:有主的过程内容全 folder 化  {type}/{developer_id}/...
   ├─ 各 developer 只编自己 folder 的文件         → 不同文件,git 几乎不撞
   ├─ 全局视图(board/ledger/dev-map/nav/log-index)全【脚本从源现生成】→ 不落第二份手维护账本
   └─ 读"全局某类" = 遍历 {type}/*/ 聚合;导航 map(DEVMAP/_NAV)快定位
        ⚠ 铁律:map 只定位,实时依据永远是【原文 + 对应代码】
```

### 五、并发 Goal Loop

```
认身份(.identity / TEAM)
   │  git pull main  +  看 DEVMAP/diff(代码动了→先刷理解,无 commit-hash)
   ▼
取卡 ── developer:自己 tasks/{你}/ 名下 todo(进实现须 review_status=1 且 待拍=0)
       leader/admin:从 tasks/pool/ 分配
   │
   ▼
写实现 + 对抗测试(种已知 bug 门必抓) ──▶ 测试跑绿 · 不破基线
   │
   ▼
落档 tasks/{你}/done/ ─▶ 刷 state/ ─▶ build_board + build_dev_map ─▶ validate_dev
   │
   ▼
land(合并进 main · 仅 leader/admin) ──▶ 他人 pull 同步 ──▶ 各自据新代码刷 state
```

### 六、约束 / 自检（validate_dev 守什么 = 唯一阻断闸,退出码 0/1）

```
身份   .identity ∈ TEAM · TEAM leader 唯一 · 本机 state+log 在
卡     owner==所在文件夹 · 文件夹名==uuid8 · uuid 唯一不重复 · 缺 TASK.md→FAIL
       非法卡(无 uuid 非 T-xxx)→FAIL · done 卡须 status=done
依赖   无悬空 · DAG 无环
归属   tasks/ 下文件夹须 ∈ {pool, _元目录, TEAM developer_id}(防孤儿)
诚实   state ✅ 行须挂可指认证据(防假绿灯) · RULES 核心不变量哨兵
OQ     拍板标签只认 [需拍板]/[已决] · 计数器一致 · todo 卡 [必填] 节齐
连带   自动跑 validate_project(项目锚点存在 + 活跃文档无旧路径)
冻结   历史卡保 legacy id(T-xxx)兼容,不重 mint
```

---

## 部署 / 采纳到你的项目（详细步骤）

### 0. 前置
- 你的项目已是一个 git 仓库；装了 Python 3（跑自检脚本）。

### 1. 把框架拷进你的项目
```bash
# 方式 A：clone 本仓库后拷 dev/ + CLAUDE.md 进你的项目根
git clone https://github.com/dreaminate/Multi-Dev-Os.git /tmp/mdos
cp -R /tmp/mdos/dev   <你的项目>/dev
cp    /tmp/mdos/CLAUDE.md  <你的项目>/CLAUDE.md
```
> `dev/` 整套搬进项目根；`CLAUDE.md` 放项目根（根路由,agent 开局先读）。

### 2. 把 .identity 加进**你项目的** .gitignore
```bash
cd <你的项目>
echo "dev/.identity" >> .gitignore
```
> `dev/.identity` = 本机开发者身份,每人各异、**不入库**。本框架仓库里它是个**空占位**,你填上自己的 id 后它在你项目里被忽略、留本地。

### 3. 填 5 个项目级文件（模板已就位,逐个填）
| 文件 | 填什么 |
|---|---|
| `dev/TEAM.md` | 花名册：你 = `leader`(唯一)；加 `admin`(×N) / `developer` 行 |
| `dev/GOAL.md` | 项目终态契约（§0 北极星 + 子系统 + 工程标准） |
| `dev/RULES.project.md` | 本项目红线 / 致命错误即停工 / 性能·数据标准 |
| `dev/CODEMAP.md` | 项目代码结构图（给 agent 导航,不含 dev/） |
| `dev/scripts/validate_project.py` | 填 `PROJECT_ANCHORS`(关键文件) + `STALE_PREFIXES`(旧路径) |

### 4. 建你的本机身份 + 状态
```bash
echo "你的-developer-id" > dev/.identity            # 须 ∈ TEAM.md
mkdir -p "dev/state/你的-developer-id" "dev/log/你的-developer-id"
printf '# STATE · 现状 gap\n\n> 现状 vs GOAL,🟡 未验证 ≠ ✅。\n' > "dev/state/你的-developer-id/state.md"
printf '# LOG · 滚动日志\n\n> 每 session 末落一行(做了啥 + 下一步)。\n' > "dev/log/你的-developer-id/log.md"
```

### 5. 自检（绿即就绪）
```bash
python dev/scripts/validate_dev.py
```
> 没填 `.identity` 时它会 FAIL 提示"`.identity` 为空/缺失"——这就是采纳清单本身。填好 + 建好 state + log 后转 PASS。

### 6. 日常（并发 Goal Loop）
入口提示词 = `dev/exec/HANDOFF.md`（整段复制给新 session）。
- **取卡**：developer 取自己 `tasks/{你}/` 名下 todo；leader/admin 从 `tasks/pool/` 分配。
- **干活**：写实现 + 对抗测试（种已知 bug 门必抓）→ 跑测试绿、不破基线。
- **收尾**：落档 `tasks/{你}/done/` → 刷 `state/{你}/` → 跑 `build_board.py` + `build_dev_map.py` + `validate_dev.py`。
- **分配 / land（合并进 main）= 仅 leader/admin。**

---

## 给 Claude 的初始化提示词（把 dev/ 拷进项目后，整段复制给 Claude）

```
你要把这套「团队并发开发 OS」初始化进本项目。按顺序做，每步缺信息就停下问我、别瞎编：
1. 读框架(不可改)：dev/README.md + dev/RULES.md + dev/exec/HANDOFF.md。
2. 定团队 → dev/TEAM.md：问我成员+角色(我=leader 唯一；admin×N；developer)。
3. 建本机身份 → dev/.identity(单行=我的 developer_id,须∈TEAM),并把 dev/.identity 加进项目根 .gitignore。
4. 填项目契约(逐个问我+扫代码,照模板填)：dev/GOAL.md(终态)· dev/RULES.project.md(红线)· dev/CODEMAP.md(代码结构)· dev/scripts/validate_project.py(锚点/旧路径)。
5. 建我的状态 → dev/state/{我的id}/state.md(现状 gap 骨架) + dev/log/{我的id}/log.md(日志骨架)。
6. 自检 → python dev/scripts/validate_dev.py,绿即就绪。
7. 之后每次开工用 dev/exec/HANDOFF.md 当入口。

开局即守的铁律：① 文件夹/文件名严格照框架、不自创不改名(validate 会抓) ② 每个文件严格照其顶部「格式·防跑偏」骨架+对应模板填、不漂移 ③ state/board/log/experience/decisions/issues/研究台 全 per-developer folder,读要遍历聚合 ④ 导航 map(DEVMAP/_NAV)只定位,实时依据看原文+代码 ⑤ 分配/land 仅 leader/admin ⑥ 🟡未验证≠✅,不假绿灯。
```

## 框架 · 勿改（= 本仓库的核心；改 = 改范式本身,回流本仓库别在项目里分叉）
`dev/RULES.md` · `dev/README.md`(OS 规约) · `dev/exec/HANDOFF.md` · `dev/tasks/_templates/TASK.md` · `dev/research/{WORKFLOW, ideas/README, ideas/_TEMPLATE, active/README, active/_TEMPLATE, findings/_TEMPLATE}.md` · `dev/scripts/{validate_dev, build_board, build_dev_map, build_ledger, build_card_counters, build_log_index}.py` + `scripts/README.md` · 根 `CLAUDE.md`。

## 核心机制
- **身份**：`.identity`(本机) + `TEAM.md`(全员 + role：leader×1 / admin×N / developer)。**分配 / land 仅 leader/admin**；developer 只写自己名下卡 + self-review。
- **任务卡**：`tasks/pool/{uuid8}/`(待分配) → `tasks/{developer_id}/{uuid8}/`(分配 = 改归属文件夹) → `tasks/{developer_id}/done/`。**文件名 = uuid 前 8 位，内容 + 依赖 = 全 32 位，依赖锚 uuid**(前缀可变、uuid 不变)。
- **folder 化**：state / board / log / experience / decisions / issues / 研究台 全 `{type}/{developer_id}/`，**读 = 遍历聚合**；canonical/全局决策归 leader 的 folder。
- **生成视图不手编**：board / ledger / dev-map / log-index / nav 全脚本现生成。
- **自检**：`validate_dev.py`(身份∈TEAM / leader 唯一 / 卡 owner==所在文件夹 / 文件名==uuid8 / 依赖无悬空 + DAG 无环 / state 不假绿灯)。
- **代码新鲜度**：开工前 `git pull` main；新提交触及你卡依赖代码 → 先看 diff + `DEVMAP` 再动手(git pull/diff = 原生信号,不另设 hash)。
