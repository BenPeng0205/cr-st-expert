# cr-st-expert 部署与分享

## 技能安装

获取完整的 cr-st-expert 目录，使 SKILL.md 直接位于该目录内。安装到技能宿主的用户技能目录或项目技能目录，具体位置以宿主当前配置为准。

当前 Codex 官方文档列出的用户技能目录为当前用户主目录下的 .agents/skills，项目技能目录为项目中的 .agents/skills。安装前确认宿主实际识别的位置，不要同时在多个目录安装同名技能。见 [官方技能文档](https://learn.chatgpt.com/docs/build-skills)。

某些已有安装器或桌面环境仍使用 CODEX_HOME/skills；这类环境沿用其已经识别的技能目录，不擅自搬迁全局配置。

Windows PowerShell 示例，从公开包解压目录执行：

```powershell
$skillHome = Join-Path $HOME '.agents'
$skillTarget = Join-Path $skillHome 'skills/cr-st-expert'
if (Test-Path -LiteralPath $skillTarget) { throw 'Target exists; review or back up before replacing.' }
Copy-Item -LiteralPath './cr-st-expert' -Destination $skillTarget -Recurse
```

Linux/macOS 示例，未自定义技能主目录时：

```sh
skill_home="$HOME/.agents"
mkdir -p "$skill_home/skills"
test ! -e "$skill_home/skills/cr-st-expert" || exit 1
cp -R ./cr-st-expert "$skill_home/skills/"
```

宿主刷新技能列表或重新开启会话后，确认 cr-st-expert 已识别。主动调用技能审查一段代码；检查输出是否指出命名、注释、接口和扫描周期问题。

其他支持 SKILL.md 的宿主可安装到各自支持的目录，不要求使用某一特定宿主。现有目录禁止盲目覆盖；升级前保留已知文件备份，并先读包内说明。

## 零工具基础使用

安装技能不需要 Python、其他技能、CLI、图谱、IDE 或记忆服务。基础验收是宿主加载 SKILL.md 和相对路径规范资料后，AI 能按规则进行规范审查。使用自然语言，不要求 JSON 请求。

技能不自动编译、不连接设备、不下载程序、不上传代码、不记录外部记忆。检查结果只描述规范问题，不保证领域逻辑或设备行为正确。

## 可选脚本

Python 3.10 或更高，标准库即可。从技能目录执行 README 中的命令。源码路径和结果路径由调用者提供，脚本以自身位置定位技能资产。没有 Python 时仍可使用全部人工规范能力。

scripts/main.py 是规划辅助，不生成完整 ST 程序。协议脚本只验证内置文本约定；该约定不是原生 IDE 导入接口。所有脚本检查结果与人工审查、编译及功能验证分开记录。

## 公开包

使用 scripts/build_public_package.py 构建 ZIP 和文件哈希清单。只包含：
SKILL.md、README.md、README.zh-CN.md、LICENSE、requirements.txt、config.yaml、command.yaml、test-prompts.json，以及 assets、rules、references、templates、examples、scripts、test、evals、deploy 和公开产品契约。

不包含 .git、output、缓存、内部规划、历史用户提示、执行日志或外部记忆配置。分享包之前执行 public_asset_guard.py，禁止将当前整个研发目录直接压缩公开。

原仓库历史可能保留旧路径和内部信息。新公开仓库从经过检查的包初始化，不能仅清理当前文件后推送旧历史。

## 卸载与恢复

仅删除本次安装的 cr-st-expert 目录；不要删除整个技能主目录或其他技能。检查脚本仅在用户指定位置写结果，无服务、后台任务和全局配置写入。升级失败时恢复已备份的原技能目录，再刷新宿主。

跨电脑验证至少包含：不同用户名和安装路径、无其他技能和工具、只加载文档的基础审查，以及选择运行脚本时的首次执行与错误响应。未经验证的平台不宣称已通过。
