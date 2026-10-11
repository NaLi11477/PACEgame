> Historical v0.2.0 first-audit record. Its broad technical approval was superseded by the second independent audit. Current v0.2.1 closure and scope are in audit_021.md and release_scope.txt. Test counts below describe v0.2.0 only.

# PACEgame 0.2.0 audit record

Technical review passed within the recorded synthetic-model and Linux/CPython scope. Public submission metadata and official-template verification remain pending.

Source and installed-wheel suites: 135 tests each, passing. Independent quadrature: 18 strategy/model combinations, both players. Global optimization and Nash certification are not provided.



## A01 P0: 把有限搜索上限认定为收益无界

baseline RL 在进入时间为0时的收益极限为51/8000=0.006375；原版仍返回 unbounded。有限预算无法证明无限收益。

引入 search limit 未解决状态；不再由有限探测生成无界结论，并从排名、收益静态分析中排除该候选。

solve/engine.py；test_finite_asymptote_is_not_infinite_payoff；release_validation.json

已修复；不宣称开域全局证明。



## A02 P0: 求解失败仍通过可行性命题

故意使 payoffs 抛出 RuntimeError，原版 Feasible 在2个网格点均通过，Report.ok=True。异常被缓存吞掉，缺失解被跳过。

缓存不再吞异常；报告区分错误与不适用；Feasible 没有计算结果不能通过。

analyze/verify.py；test_broken_feasibility_cannot_pass

已修复；错误保留类型、原因和参数。



## A03 P1: NaN、Inf及非法参数域进入计算

原版 numeric 接受 sigma=NaN；growth_end>horizon 或 readiness lag>growth_end 可生成反向积分或无效搜索盒。

新增 Game.validate，并在 numeric 与 solve 两处检查有限值、正性、时间顺序、成本、质量和上界。

core/game.py；非有限值、负成本、非法生命周期与进入下界测试

已修复；自定义模型须补充领域限制。



## A04 P1: 未知参数生成看似有效的相同结果

原版公开 sweep 接受 TYPO，两行收益完全一致。CLI --set 与网格参数也存在不一致的校验口径。

公开 sweep、验证轴、CLI override 采用模型参数表验证；输入错误明确拒绝。

analyze/equilibrium.py；analyze/verify.py；cli.py

已修复；numeric 保留忽略未启用参数的兼容行为并写明。



## A05 P1: 无有效网格仍可形成成功状态

零或非整数采样数、空轴、非有限轴、空命题列表欠缺有效覆盖定义。

拒绝空覆盖和非法采样；新增 Report.complete 与严格 Result.holds。

analyze/verify.py；test_grid_must_have_coverage；test_skips_do_not_establish_a_whole_grid_claim

已修复；有限网格仍只是样本证据。



## A06 P1: 未解决、无效或全部发散候选被排名

原版全部无界时 best 仍从截断收益中取值；非有限收益、诊断违规也没有统一排除接口。

Solution.rankable 统一检查；Outcome.excluded/complete 披露覆盖；无可排名对象时 best=None。

solve/engine.py；analyze/equilibrium.py；全未解决与排除测试

已修复；部分排名不等于完整策略集合的最优。



## A07 P1: equilibrium/best response术语超过实现能力

代码只根据焦点标签机械赋予另一方角色，没有完整双边策略偏离检验。收入差也不是 Nash 条件。

增加 rank_strategies；equilibrium 仅兼容别名；统一写成条件候选排名，并明确未获 Nash 认证。

analyze/equilibrium.py；README.md；文稿1、2、4、5节

已修正；完整 Nash/子博弈精炼求解未实现。



## A08 P1: 领导者原始偏导被当作带反应的最优性检查

带后续反应时，应检查约化目标；固定另一决策的偏导不是领导者目标导数。

对需要下层反应的阶段，原始偏导诊断不作认证；增加解析顺序博弈例子。

solve/feasible.py；analytic_sequential_toy

已修复报告逻辑；未给出完整约化目标全局证书。



## A09 P1: 内点缺一阶条件及联合曲率检查

原版内点只检查单变量二阶导；负对角线不能排除联合鞍点，也不能证明驻点。

增加终末阶段一阶驻点检查和联合内点 Hessian 检查；强制鞍点反例通过实际诊断路径。

solve/feasible.py；solve/engine.py；stationarity 与 joint saddle 测试

已修复必要检查；不把必要条件当充分条件。



## A10 P1: 决策值数值漂移被有限差分误判

旧示例 RL 最优信号对 sigma 理论上不响应，却因约1e-8的优化误差得到负斜率。

对选定分支的终末内点作高精度一阶条件局部校准，仅接受临近且目标不下降的改进。

solve/engine.py；test_flat_optimal_signal_does_not_become_a_noise_slope

已修复该反例；不连续反应和一般差分稳定性仍需个案检查。



## A11 P1: 不适用/计算错误/完整通过混为一谈

原版异常转为 skipped，部分通过仍可 holds；错误理由未显示。

独立记录 errors、skipped、reasons；完整覆盖才能 holds；Markdown输出也显示覆盖和错误数。

analyze/verify.py；验证错误与partial覆盖测试

已修复；ok与complete含义明确区分。



## A12 P1: 阈值未检出被写成阈值不存在

有限扫描可能遗漏两个网格点之间的交叉，或在边界拐点处不稳定。

文档与示例改为该扫描分辨率下未检出严格交叉；阈值计算拒绝未解决候选。

analyze/equilibrium.py；analyze/statics.py；replicate_study.py

已修正文稿和输出范围；不存在性证明未提供。



## A13 P1: 机械匹配信号被当作玩家完全可互换

rival_signals 仅复用焦点信号，且信号成本只记入焦点；单项质量字典还可能遗漏默认质量1。

信号标签不再被标作玩家可互换；单个显式质量与隐式基准1比较；删除收入差的 Nash 解释。

core/game.py；core/share.py；symmetry测试

已修复对称性报告；模型成本语义保留并明示。



## A14 P2: 缓存指纹遗漏时间符号及策略完整标志

Game 可变；相同名称的标签或时间符号变更可能复用错误的符号积分。

缓存键包含完整 Strategy 和 time；明确私有扩展状态变化需 invalidate。

core/game.py；test_time_symbol_invalidates_cached_payoffs

已修复已识别指纹问题；自定义隐藏状态仍遵循契约。



## A15 P1: 评估路线失败后可能遮蔽后续可评估点

所有路线进入冷却时，合法点也会被当作不可评估；最后数值替代路线不应整体停用。

廉价路线保留冷却，最终精确替代路线始终尝试；保留失败/救回次数。

solve/engine.py；test_evaluator_retries_exact_after_local_failure

已修复；覆盖率是调用次数口径，非连续区域覆盖率。



## A16 P1: 失败命令仍进入基准统计

退出码7的测试程序在原版仍得到n=1的计时结果；新的measure抛出RuntimeError。

每条子进程成功后才入样本；输出原始重复、轮次、环境、命令和负载。

examples/benchmark.py；benchmark_failure_probe.json

已修复；不再推断隔离硬件或普遍性能。



## A17 P1: 旧示例越过进入下界

replicate_study 的growth sweep包含0.05，但lambda=0.1；启用合法域检查后该段不能运行。

增长区间改从0.1开始；位于边界的差分使用可行单边模板；完整重跑图表。

examples/replicate_study.py；analyze/statics.py

已修复；不能为了复现旧图保留非法点。



## A18 P1: 宣称ready lag恢复全部竞争机制

下界lag不迫使RL离开growth_end上界；该角点仍可能没有局部份额参数响应。

删除全部恢复的说法；逐标签输出诊断，并在模型文档和文稿说明局部含义。

docs/model.md；audit_preannouncement.py；文稿3节

已修正；不把局部偏导零当作经济竞争消失的证明。



## A19 P1: 软件公开身份及作者元数据为占位链接

原版CITATION.cff包含伪DOI、假日期、占位ORCID；pyproject链接指向PLACEHOLDER-ORG。

删除无效发布元数据；正文两张表明确永久公开链接和作者联系方式待完成。

pyproject.toml；docs/CITATION_PENDING.txt；元数据表

未提供真实信息，故公开发布/投稿条件仍待完成。



## A20 P1: 稿件大幅超长且Impact充斥历史审计叙事

原文全文8415空白分词，正文按统一词边界约7208词；大量段落讲历轮错误，偏离OSP用户说明。

正文改写为五节，约2552词，摘要197词；历史问题迁至本报告和软件文档。

新版Word、统一内容JSON、LaTeX证明稿

已修正文体与篇幅；词数以随包脚本口径为准。



## A21 P1: 应用证据和伴随研究缺乏可核验来源

上传材料未包含被称为已改变结论的外部文章，也未提供用户、引用、工业应用证据。

撤回独立发表研究复现和实际采纳的口吻；旧命题清单只作为随包遗留库存，潜在影响单独表述。

文稿Motivation、Impact；legacy JSON provenance

证据范围已修正；不补造应用数据。



## A22 P1: 官方模板核验无法由结构相似代替

Elsevier官方页面可访问并提供模板入口，但作者指南返回403；官方docx下载返回Site Unavailable HTML。

采用报告要求的五节、两张元数据表和完整声明，并交付可编辑Word与可编译证明源；明确尚未完成当前官方模板原文件核验。

官方链接见报告第6节；文稿包README

仍需最终模板核验，不能声称已通过官方模板认证。