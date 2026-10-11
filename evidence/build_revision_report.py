"""Create the implementation validation report from completed execution receipts."""
from pathlib import Path
import json,runpy
A=Path(__file__).resolve().parent.parent;B=A/'evidence';O=A/'outputs';load=lambda n:json.loads((B/n).read_text())
v=load('validation_comparison.json');art=load('artifact_validation.json');dist=load('distribution_integrity.json')
assert v['all_comparisons_passed'] and dist['wheel_bytes_identical']
tests={e:load(f'validation_{e}/test_suite/summary.json') for e in ('source','wheel','core')}
for e,t in tests.items():
 assert t['tests_run']==t['discovered']==493 and t['passed']==493-(e=='core') and t['skipped']==(e=='core') and t['successful'] and not t['failures'] and not t['errors']
 cs=load(f'validation_{e}/execution.json');assert len(cs)==13 and all(x['returncode']==0 and x['package_unchanged'] and x['wheel_unchanged'] for x in cs)
 assert all(x['returncode']==0 for x in load(f'old_probes_{e}/execution.json'))
 assert load(f'old_probes_{e}/round12.json')['all_revision_criteria_passed']
assert load('parent_negative_control_execution.json')['parent_both_defects_reproduced']
assert load('parent_against_new_acceptance_execution.json')['returncode']==1
ns=runpy.run_path(str(B/'report_style.py'));d,p,lead,h,table,small=[ns[k] for k in ('d','p','lead','h','table','small')]
d.core_properties.title='PACEgame v0.2.11 修订与验证报告';d.core_properties.subject='第12轮两项P2问题的实现验收及同步文稿';d.core_properties.author='Codex'
d.add_paragraph('PACEgame v0.2.11\n修订与验证报告',style='Title')
p('日期：2026-10-08　｜　父版本：v0.2.10　｜　依据：第12轮严格审计报告')
lead('本轮结果','R12-01、R12-02均已实现修复，并通过本轮针对性验收。新增43个回归方法；源码与完整wheel各493项通过；离线核心wheel执行493项、492项通过、1项绘图测试跳过，均无失败或错误。')
lead('结论范围','修订可以提交下一轮独立审计。本报告记录实现后的验证，不替代独立核准或刊物决定；v0.2.11独立复审仍待执行，投稿就绪仍为False。')
table([['问题','实现后的行为','验收'],['R12-01 / P2','所有payoff_for决策者收益先准入，再进入固定、跳过或求导分支','20个原反例不再完整通过；合法控制保留'],['R12-02 / P2','各候选绑定参数与决策，保留收益后相减；排名与差分共用路径','排名、支配、交点与敏感性恢复独立真值']], [3.0,8.4,6.0])
h('依据与冻结输入')
p('第12轮审计报告全文已读取。软件、XeLaTeX、原审计报告与证据重新取得并冻结；父版没有被本轮修订覆盖。刊物结构与元数据继续沿用SoftwareX深度分析报告(7)及上轮核对结果。')
rows=[['输入','SHA-256 前16位']]+[[x['name'].replace('PACEgame_',''),x['sha256'][:16]] for x in load('frozen_inputs.json')]
table(rows,[11.8,5.6]);small('完整哈希、输入身份和来源见frozen_inputs.json与INPUT_PROVENANCE.json。原审计报告和证据保留在完整发布包的prior_audit中。')

h('R12 01 决策者收益的必要准入',True)
p('check_point在候选点和参数保留代入后，遍历全部声明的payoff_for收益；这一步发生在任何求导、固定坐标或skip_optimality分支之前。收益能否准入与是否需要KKT或曲率检查分别判断。常数项不再因为求导消失而逃过检查。')
table([['候选点的owner收益','覆盖路径','本版判定'],['1+I×10^-400、1+I/10','固定、内点、下角点、跳过；8例','required violation；ok=False'],['NaN、正无穷','上述四条路径；8例','required violation；ok=False'],['未代入的实数Symbol z','上述四条路径；4例','required warning；complete=False'],['有限值-1或2与主收益不同','上述四条路径；8个控制','ok=True、complete=True']], [6.0,5.7,5.7])
p('每项记录owner变量标识。已知非实或非有限值是明确违反；未知值是不可用的必要检查。有限负净收益和不同决策者拥有不同收益保持合法；没有增加净收益非负条件。原主收益与已提供gross准入守卫仍保留。')
lead('报告语义','complete表示必要检查获得判定，并不等于判定通过。已知无效收益可以是完整的违反；只有未知准入必须complete=False。批准候选仍需同时检查ok与complete。')
lead('实现范围','修复的是公开check_point的payoff_for入口。父版主solve已有玩家净收益和已实现收益守卫，本报告不声称它原先把这些复数收益排进排名。')
small('位置：pacegame/solve/feasible.py。证据：validate_audit_0211、独立round12.json与逐项测试ledger。')

h('R12 02 保留候选收益再计算差额',True)
p('Solution.retained_payoffs保存每个玩家在本解实际参数和候选坐标下的符号数值；payoff_value访问确定有限实数的保留值。Outcome保存对应的focal与rival收益。原payoffs浮点字段继续用于显示和兼容；最终显示值相同不代表真实收益并列。')
table([['公开接口 / 原反例','v0.2.10','v0.2.11'],['A与A+1；A=2^53、2^60、10^20；两种列序','错误弱支配通过，遗漏严格支配','严格RL>RF通过；弱RF>=RL失败；6例一致'],['rank_strategies与ties','best随列序改变，虚假并列','best=RL；ties仅RL；complete=True'],['A+phi-1/2与A；phi在[.25,.75]','threshold=None','交点0.5'],['A+sigma；中央有限差分','slope=0、sign=0','slope=1、sign=+']], [6.0,4.5,6.9])
p('排名、并列、支配、交点与收益差分在相减前保留两个操作数。不同策略各自绑定自己的候选点；有限差分两端分别求解并绑定自己的参数，继续描述受约束候选响应。玩家收益、策略收益差及随参数移动的固定候选均有回归控制。')
lead('不可用传播','未知排名使complete=False并明确抛ValueError；支配没有可用收益时跳过，不能holds。差分结果若溢出或非零下溢，明确范围错误并不给符号判定；不能写成零、并列或平坦响应。')
lead('原阈值与兼容','Dominates绝对阈值1e-12、ties阈值1e-9保持不变。手动构造且未提供保留映射的旧Solution/Outcome使用其实际已给收益，不猜测输入前已丢失的数字。A=0、2^40及大数差额2的控制仍通过。')
small('搜索仍使用binary64启发式评价；本修复保证列明的最终比较路径，不证明所有搜索算术精确、全局最优或完整Nash互动。')

h('全量执行与分发核验',True)
table([['环境','执行 / 通过 / 跳过','失败 / 错误'],['源码，含绘图依赖','493 / 493 / 0','0 / 0'],['完整安装wheel，checkout外导入','493 / 493 / 0','0 / 0'],['离线核心wheel，无绘图库','493 / 492 / 1','0 / 0']], [7.6,6.1,3.7])
p('使用不变的shipped load_suite；每项结果、显式日志、导入路径及包字节核对都有回执。三种验证环境本轮新建；Linux / CPython 3.12.14，SymPy 1.14.0、mpmath 1.3.0离线安装。完整环境另有Matplotlib 3.10.8、NumPy 2.3.5。仅核心环境绘图测试跳过。')
table([['检查','实际结果'],['新增回归','43个方法；保留450个父版方法，共493个'],['导出器','每环境12个；36次导出命令全部成功；41组/环境接受'],['独立公开探针','R7至R12在三环境重跑全部成功'],['父版区分','冻结父版完成探针并确认两缺陷，预期退出1；新版验收在父版同样失败，在新版三环境通过'],['数值基线','案例、独立积分、有限渐近与解析顺序玩具同父版；三环境一致'],['跨环境','验收组一致；仅排除R6-05的两个安装版本环境字段'],['分发','源码、sdist、wheel及两安装目录61个包成员相同；示例镜像相同'],['sdist重建','从本轮新sdist再次构建wheel；整文件和所有成员字节相同']], [4.4,13.0])
p('构建复用已有build环境，工具为build 1.6.1与hatchling 1.32.4；没有把复用写成新建。源码、完整及核心验证环境另行新建。远端CI和其他平台未执行。本轮没有新计时，v0.2.10的8次成功共享主机基准作为历史记录保留。')
small('初次针对性测试将已知违反也要求complete=False，16项断言过严；已按公开complete语义改正。原观察已是违反，修正不涉及生产逻辑。发现总数后将草稿45/495改为实测43/493；最终交付均使用后者。说明见setup_notes.json。')

h('软件与文稿同步及交付',True)
p('版本、安装路径、README、CHANGELOG、当前audit_0211说明、包内示例镜像、元数据与CI导出列表已同步。稿件第2.2节补充全部owner收益准入，第2.3节解释保留差额与不可用传播，第3节更新反例、控制和执行数量，表5增加两行R12验收。')
table([['核对','结果'],['共享正文','33个正文块；Word、TeX与内容JSON一致；全部表格单元格一致'],['篇幅',f"正文{art['body_words']}词；摘要{art['abstract_words']}词；正文统计不含表格、参考文献和元数据"],['结构','五节正文、5表、3幅灰度图、17个元数据字段'],['渲染',f"Word {art['word_pages']}页、TeX {art['tex_pages']}页；逐页核对；无缺字、溢出或截断"],['编译与数据','XeLaTeX两遍；无Overfull或缺字警告；三环境当前数值与图表核对通过']], [4.0,13.4])
p('篇幅满足上传深度报告的历史3000/250词口径；这不是当前官方模板认证。第12轮官方作者指南正文访问403的记录按历史保留，本轮未重新取得当前模板。作者、机构、贡献、资助与利益声明、支持联系方式、公开冻结源码与永久归档标识仍待完成，不能按已投稿就绪批准。')
p('交付：软件ZIP含源码、sdist、wheel、vendor与本轮证据；独立Word稿；XeLaTeX包含共享内容、图、数据与编译证明；本报告；完整发布ZIP另含第12轮原审计与证据。当前执行记录与历史依据分开保存。')
h('重新复核入口')
p('解开软件ZIP；全新venv离线安装：python -m pip install --no-index --find-links vendor dist/pacegame-0.2.11-py3-none-any.whl。在checkout外运行python -m pacegame.tests及python -m pacegame.examples.validate_audit_0211 validation。evidence/README_evidence.txt列出全部导出器、独立探针及SHA核对入口。')
lead('验收状态','R12-01、R12-02本轮实现验收通过；下一轮独立审计待执行；作者及声明、公开归档和当前官方模板核准待完成。')
small('最终ZIP的CRC、全部负载SHA-256清单与嵌套交付一致性由打包程序另行核验；本报告结论限定于上述实测范围。')
path=O/'PACEgame_v0_2_11_Revision_and_Validation.docx';d.save(path)
summary={'version':'0.2.11','parent_version':'0.2.10','date':'2026-10-08','implemented_and_validated':['R12-01','R12-02'],'new_regression_methods':43,'tests':tests,'exporters_per_environment':12,'acceptance_groups_per_environment':41,'independent_reaudit':'pending','submission_ready':False,'official_template_certified':False,'source_wheel_sdist_installed_package_equal':True,'fresh_sdist_rebuild_performed':True,'rebuilt_wheel_bytes_identical':True,'artifact_checks':art}
(B/'revision_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(path)
