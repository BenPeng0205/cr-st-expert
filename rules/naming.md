# 命名规范

> 状态：强制执行。

## 1. 顶层对象前缀

| 对象族 | 前缀 | 示例 |
|---|---|---|
| PROGRAM | `PRG_` | `PRG_Main` |
| FUNCTION_BLOCK | `FB_` | `FB_MotorController` |
| FUNCTION | `F_` | `F_LimitSpeed` |
| GVL | `GVL_` | `GVL_System` |
| ENUM | `E_` | `E_MotorState` |
| STRUCT | `ST_` | `ST_MotorData` |

## 2. 聚合段前缀

| 段落 | 前缀 | 示例 |
|---|---|---|
| METHOD | `M_` | `M_Init` |
| ACTION | `A_` | `A_ResetFault` |
| PROPERTY | `P_` | `P_TargetSpeed` |

## 3. 变量前缀

所有自定义变量声明必须严格使用匈牙利前缀；PLCopen、PackML、CODESYS 标准库或厂商库固定引脚名只允许在调用外部库对象或说明外部标准语义时原样出现，不作为本技能 POU 示例变量声明的豁免。自定义执行型/持续型 FB 使用 `bExecute / bDone / bBusy / bError / diErrorID / bEnable / bValid`。

| 数据类型 | 前缀 | 示例 |
|---|---|---|
| BOOL | `b` | `bEnable` |
| INT | `i` | `iTargetSpeed` |
| DINT | `di` | `diStateCode` |
| REAL | `r` | `rRatedTorque` |
| STRING | `s` | `sModel` |
| TIME | `t` | `tStartDelay` |
| ENUM 实例 | `e` | `eState` |
| STRUCT 实例 | `st` | `stMotorData` |
| FUNCTION_BLOCK 实例 | `fb` | `fbMotorController` |
| TON | `ton` | `tonStartTimeout` |
| R_TRIG | `rtrig` | `rtrigStart` |
| F_TRIG | `ftrig` | `ftrigStop` |

## 4. 文件和段落命名

CODESYS ST text 权威文件：

```text
FB_Name.st
```

父文件内部段落：

```iecst
// === METHOD M_Method ===
// === ACTION A_Action ===
// === PROPERTY P_Property ===
```

禁止在 `cr-st-expert` 权威交付中使用：

```text
FB_Name.M_Method.st
FB_Name.A_Action.st
FB_Name.P_Property.st
```

## 5. 约束

- 对象名使用 PascalCase 主体。
- 前缀后只允许一个下划线。
- 库、包或一级目录已经表达的领域词不得机械重复到每个公共对象名中；例如曲线库内禁止批量命名为 `FB_CurveXxx`，应命名为 `FB_Xxx`。
- 域词只有在类型族区分、标准术语、重名消解或外部兼容需要时保留，并必须在重命名策略中说明原因。
- 缩写必须可读，不得随意造词。
- 同一概念的缩写必须全工程一致。
- 同一技能内不得混用 `n / f` 与 `i / r` 前缀体系。
