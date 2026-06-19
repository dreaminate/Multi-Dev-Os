# Multi-Dev-Os · 团队并发协作开发范式（可复用框架）

把一个项目变成「**身份 + 五台 + 并发 Goal Loop**」驱动的协作仓库：多 developer 各写各的 folder、**并发零冲突**，全局视图脚本现生成，导航 map 只定位、实时看原文 + 代码。范式细节见 `dev/README.md`。

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
mkdir -p "dev/state/你的-developer-id"
printf '# STATE · 现状 gap\n\n> 现状 vs GOAL,🟡 未验证 ≠ ✅。\n' > "dev/state/你的-developer-id/state.md"
```

### 5. 自检（绿即就绪）
```bash
python dev/scripts/validate_dev.py
```
> 没填 `.identity` 时它会 FAIL 提示"`.identity` 为空/缺失"——这就是采纳清单本身。填好 + 建好 state 后转 PASS。

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
