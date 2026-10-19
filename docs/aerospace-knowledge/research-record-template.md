# 可复用研究卡模板｜Research Record Template

> 复制本文件到 `docs/aerospace-knowledge/records/<ID>-<topic>.md`，不得直接把未复现结论填作通过项。  
> 状态枚举：`DISCOVERED / SOURCE_CHECKED / ANALYZED / REPRODUCED / CROSS_CHECKED / TRANSFER_PROPOSED / ADOPTED_SOFTWARE / DEFERRED / REJECTED`。

## 0. 元数据

| 字段 | 内容 |
|---|---|
| Record ID / 标题 | `KR-YYYY-NNN` / ... |
| 首次记录 / 最后审阅 | YYYY-MM-DD / YYYY-MM-DD |
| 研究人 / 审阅人 | ... / 未安排 |
| 来源类型 | GitHub / 官方标准 / 论文 / 公开工程案例 |
| 来源、仓库或 DOI | 完整 URL |
| 上游版本 | 精确 git commit SHA / 发布 tag / 标准编号与版号 |
| 查阅的路径与章节 | 具体 README、源码路径、行号或章节 |
| 授权/版权备注 | license 原文链接；依赖与第三方资产待查 |
| 研究状态 | SOURCE_CHECKED |
| 对应项目 / 问题 | AI-rocket `R0-xxx` / AeroForge `...` |

## 1. 本次想回答的工程问题

- 问题定义：
- 为什么这个问题**现在**重要：
- 项目当前权威状态及来源：
- 明确不在研究范围的内容：

## 2. 可以直接证明的原始事实

| 断言 | 原始证据（链接+版本+文件） | 证据类型 | 局限性 |
|---|---|---|---|
| ... | ... | 官方声明 / 源码 / 重现实验 / 论文 | ... |

不得把作者口头描述、AI 总结或社区推荐直接写成通过的测试结论。

## 3. 原理与适配分析

- 核心原理（自写解释，不大段复制有版权内容）：
- 输入/输出与数学、时间、单位、坐标定义：
- 必要依赖、计算资源、维护成本：
- 与项目已有实现的差异：
- 正面案例与反面案例：
- 适用边界、可能误用、已知未知项：

## 4. 独立实验 / 复现计划

```yaml
experiment_id: EXP-...
purpose: ""
upstream_commit_or_release: ""
local_code_commit: ""
environment:
  platform: ""
  language_and_tool_versions: []
inputs:
  source: ""
  sha256: ""
  units_and_coordinate_system: ""
  assumptions: []
  random_seed: null
command: ""
expected_observables: []
acceptance_criteria: []
actual_results: null
logs_and_artifact_hashes: []
limitations: []
classification: NOT_RUN
```

- 复现实际运行时间：
- 预期与实际差异、失败诊断：
- 独立校核参考：
- 不允许据此推出的结论：

## 5. 项目迁移提案（不自动生效）

- 目标仓库/文件：
- 具体拟改接口或测试：
- 为什么优于“不做”或“只写文档”：
- 工程收益 / 新增失效模式 / 引入依赖 / 许可证：
- 不需要迁移的功能：
- 回滚方案与隔离分支：
- 明确验收方式：
- 是否涉及实物能量/动力/安全审批：**默认 NO / 未授权**

## 6. 结论与裁决

- 研究事实：
- 仍未解决的问题：
- 裁决：`PROPOSE / DEFER / REJECT`
- 裁决理由：
- 审核责任人：
- 下一次复审触发事件：
- 后续记录/PR/issue 链接：

## 7. 复盘（完成实验或代码变更后填写）

- 哪个假设被证伪？
- 哪项公开经验不能照搬？
- 哪个测试最有信息量？
- 成本、风险、收益与初始估计相比如何？
- 是否需要更正其它知识库文档？

---

**注意**：该模板是研究管理工具；真正的工程参数和实物证据仍必须更新至 `engineering/` 中对应的受控权威文件，且遵守原有评审与放行门禁。
