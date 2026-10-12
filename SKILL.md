---
name: cr-st-expert
description: "Use when generating, modifying, or reviewing CODESYS IEC 61131-3 Structured Text (ST): naming, comments, formatting, POU organization, interfaces, types, and scan-cycle rules. A standalone programming-standard skill; no CLI, graph, IDE, Python, other skills, or memory service is required. Bundled static-check scripts are optional."
---

# CODESYS ST 编程规范

## 定位与生效方式

本技能规范 CODESYS ST 代码怎么写。用户提供需求或已有代码，AI 加载后直接按规则生成、修改和审查。自然语言输入即可，不要求结构化 JSON。

不需要安装其他技能、CLI、图谱、IDE、Python 或记忆服务。没有工具时也必须完成规范审查，不能因为检查脚本不可用而拒绝基础任务。

本技能不提供运动、通信等领域库接口知识，不执行工程创建、导入、编译、仿真、设备连接或下载。外部库接口由用户资料或独立资料确认；未知接口不能编造，但仍可检查已提供代码的通用规范。

## 读取与工作流程

1. 完整读取当前 SKILL.md，再读取 references/mandatory-read-manifest.json 所列规范资料。资源路径相对本技能目录，不相对用户项目或当前工作目录。
2. 缺少规范文件时说明无法核对的规则，不宣称完整符合本技能；不要要求安装外部工具补齐。
3. 建立 generation_contract：对象类型、公共对象名、接口、库依赖、诊断输出、文件边界和注释要求。简单任务用简短清单即可，不强制运行 planner 或输出 JSON。
4. 生成或修改代码，保留用户已有业务语义；库接口或行为不明确时询问缺少的事实。
5. 按规则逐项审查。完整项目 review 时必须全量扫描已提供的 .st 文件；只有片段时明确范围，不能声称全项目通过。
6. 报告已核对项、问题位置及未确认项。脚本只在用户选择且环境可用时运行，运行结果与人工审查分开说明。

## 文件和对象组织

一个顶层 IEC 对象对应一个 .st 文件；新项目建议使用 DUTs、GVLs、POUs/FBs、POUs/FCs、POUs/PRGs、DOCs。既有 IDE 工程可保留其组织方式。

内置模板和可选协议脚本使用 codesys_st_text_v1 文本组织约定。这只是代码交换格式，不是 IDE 工程或可直接导入的原生文件：Method、Action、Property 聚合在父 FB 文本内，使用 // === METHOD M_Name ===、// === ACTION A_Name ===、// === PROPERTY P_Name === 标记。Action 段保留实现体，Property 使用 GET、SET 标记。原生 IDE 对象或其他布局按用户工程要求交付，不要求特定导入工具。

## 命名与接口

- 顶层对象使用 FB_ / F_ / PRG_ / GVL_ / E_ / ST_ 前缀和 PascalCase，前缀后不加多余下划线。
- 子对象使用 M_ / A_ / P_ 前缀。枚举带 qualified_only 和 strict 属性；GVL 带 qualified_only 属性。
- FB / FUNCTION / METHOD 使用 hide_all_locals 属性；PROGRAM 不使用该属性。
- 自定义变量按 references/naming.md 使用匈牙利前缀；外部库固定引脚保留原名，自定义接口使用 bExecute / bDone / bBusy / bError / diErrorID / bEnable / bValid 等语义明确的名称。
- 库或包已表达领域时，公共对象名不要机械重复领域词；标准术语、类型族和冲突消解可以保留。
- VAR_INPUT 具有安全默认值；接口说明单位、范围、保持和复位行为，错误输出帮助工程师定位问题。
- 指针具备空指针、长度和生命周期约束；优先使用明确类型的 VAR_IN_OUT。

## 注释与格式

- 使用 4 个空格缩进，禁止 Tab；变量声明中的冒号、赋值和尾部注释按块对齐。
- 自定义变量注释使用“概括：说明”，解释用途、状态边界或单位；物理单位使用方括号。
- 文件头说明功能、接口和库依赖。完整功能注释块位于 // === IMPLEMENTATION === 后；使用说明至少包含 1. 调用条件和 2. 关键约束。
- 有可执行代码的实现段必须有工程师级 // 注释，说明算法、扫描周期、状态转换、边界或异常处理，不只复述语句。
- 按数据来源、工况分支、控制动作和输出结果组织注释；关键 IF、ELSE、CASE 分支说明实际工况。
- 数字阈值说明工程用途和边界，不编造设计来源。
- 命名参数调用采用多行并对齐 := / =>，调用块不插无意义空行，禁止空实参映射。
- 本规范使用行注释，禁止 IEC 块注释；不在公开文件中保存明文乱码测试样本。
- 中文文件使用 UTF-8，批量编辑后核对编码、替换字符和关键正文。

## 通用 ST 语义规则

- R_TRIG / F_TRIG / TON / TOF / TP 等状态型 FB 每个扫描周期稳定调用，实例不能放在 VAR_TEMP。
- 内部判断直接读取实例 .Q，不单独创建多余中转变量；公开输出或组合逻辑结果可使用语义明确的变量。
- REAL / LREAL 比较使用容差；除法前检查除数；跨类型赋值显式转换。
- CASE 包含 ELSE；状态机有初始、异常、复位和非法状态处理。
- 数组访问前检查索引；无符号长度大于 0 后才允许减 1；循环有确定边界。
- 多任务共享变量有明确所有权和一致性策略，不依赖未说明的扫描顺序。

## 库依赖与事实边界

文件头库依赖使用 LibraryId 或 LibraryId@Version，多个库用分号分隔；无外部库写“暂无”。未知版本只写库名并注明待确认，不填虚构版本。详见 references/library-dependency-contract.md。

本技能检查依赖声明格式和已知符号线索，不据此确定库已安装、接口正确或工程编译成功。运动、通信、文件等库的参数及行为由用户提供或另行核对，不强制联动任何其他技能。

## 审查结论与验证边界

输出包含范围、规范问题及位置、修改建议、未确认事实。未发现问题时可写“在已提供范围内，按本技能人工审查未发现规范问题”。

- 未运行脚本时写“脚本未执行”，不影响基础规范审查。
- 脚本运行后记录范围、命令和结果；失败不能掩盖，未覆盖的规则仍需人工审查。
- 静态检查不能声明 compile_passed、offline_pou_logic_verified、仿真通过或现场可用，需对应独立证据。
- 编译器诊断可作为修正规范代码的资料，本技能不负责启动编译器或建立测试工程。

## 可选检查脚本

无需脚本即可使用本技能。选择自动检查时，需要 Python 3.10 或更高，使用标准库。以下命令在技能目录执行，或将脚本路径改为完整路径：

```text
python -X utf8 scripts/st_semantic_linter.py --root <ST源码目录> --strict --output <报告.json>
python -X utf8 scripts/protocol_validator.py
python -X utf8 scripts/main.py examples/request.json <规划结果.json>
```

语义脚本检查用户代码，协议脚本检查内置文本样本。evals/run_delivery_gate.py 供维护者检查仓库，不是用户使用技能的前置条件。

## 规则维护

用户纠正先区分一次性需求与通用规则。只有明确授权修改技能时才更新文件，不自动记录外部记忆、上传代码或修改全局配置。维护者新增可执行规则应同步测试和可选检查，保留人工审查边界。

## 内置资源

- references/mandatory-read-manifest.json：规范资料清单。
- references/naming.md、references/style.md、references/rules/：详细规则。
- templates/：对象模板；examples/：静态验证的规范示例。
- docs/product-contract.md：能力与数据接口边界。
- scripts/：可选规划、静态检查和公开包构建。
- deploy/README.md：独立安装与卸载说明。
