# cr-st-expert 产品契约

## 基础能力

用户以自然语言提供需求或代码。AI 加载 SKILL.md 及相对路径规范资料后完成命名、注释、格式、POU、接口、类型和扫描周期审查。基础能力不要求执行脚本、结构化 JSON、其他技能或外部服务。

代码生成前建立简短 generation_contract，确认对象、接口、依赖声明和注释要求。已有工程优先尊重用户对象组织；内置 codesys_st_text_v1 仅为独立文本样例格式，不是 IDE 导入协议。

## 可选规划接口

scripts/main.py 接收 assets/schemas/request.schema.json 描述的结构化请求，输出 recommend、clarify 或 block 及文件/段落规划；不生成完整 ST 代码。

delivery_mode 为 codesys_text 或 single_file。对象族为 FUNCTION_BLOCK、FUNCTION、PROGRAM、GVL、ENUM、STRUCT。父 FB 聚合段使用 METHOD、ACTION、PROPERTY，Property 示例包含 GET 和 SET。其他工程布局仍可由 AI 按用户要求进行人工规范审查。

## 可选静态检查

scripts/st_semantic_linter.py 检查目标源码中的通用规范和风险；scripts/protocol_validator.py 检查内置文本格式。库依赖检查只根据文件头和已知符号线索判断声明，不验证外部库接口或库安装状态。

维护者可运行单元测试、回归、示例准入、编码和公开资产检查。用户未执行脚本时，规范审查仍能完成，结论注明脚本未执行。

## 能力边界

不实现运动、通信或其他领域逻辑，不建立工程、编译、仿真、连接设备或下载。库接口由用户资料或独立文档确认；接口未知时不编造调用，但仍可审查已知部分的规范。静态检查不能代替编译、离线功能测试或现场证据。

## 公开与维护

新增规范同步文档及适用的可选检查或测试。修改技能需明确授权，不自动向外部记忆服务写入。公开资产通过白名单与脱敏检查，Git 历史和使用记录不进入公开包。
