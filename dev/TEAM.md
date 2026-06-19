# TEAM · 团队花名册（developer_id ↔ role）

> 谁在 git 协作开发本项目。**本机身份在 `dev/.identity`(不入库,gitignore)**,其值须是下表某个 `developer_id`。
> **role 语义**：`leader`(**唯一,×1**)· `admin`(×N)· `developer`。
> **权限**：只有 `leader`/`admin` 能 ① **分配**(卡 `tasks/pool/{uuid8}/` → `tasks/{developer_id}/{uuid8}/`)② **land**(合并进 main + 合并 decisions/issues 等全局账)。`developer` 只写自己 `tasks/{自己}/` 名下卡 + self-review。
> **canonical/全局决策**(项目级,人人遵守)归 **leader 的 folder**(`decisions/{leader_id}/`)。

<!-- 格式·防跑偏 | 结构型【项目级别】填：固定表 developer_id | role | 说明。
新成员加一行；leader 唯一(改动慎重)；developer_id 须与各人 dev/.identity 一致。 -->

| developer_id | role | 说明 |
|---|---|---|
| <leader_id> | leader | 唯一 leader；可分配 + 可 land |
| <admin_id> | admin | 可分配 + 可 land |
| <dev_id> | developer | 只写自己名下卡 + self-review |
