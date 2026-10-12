# 命名规范

> 适用范围：所有 CoDeSys ST 程序单元、变量、常量、类型声明

---

## 程序单元命名

格式：`前缀_PascalCase主体`

硬规则：

- 公共对象名只允许一个分隔下划线，也就是前缀后的第一个 `_`。
- 前缀后的主体必须使用 PascalCase，禁止继续使用 `_` 做单词分隔。
- 禁止把旧库的全大写下划线名机械加前缀后直接交付。
- 旧对象重命名前必须先做语义归一，再输出 rename-map，并全工程同步替换定义、引用、文件名和注释。
- 库域上下文词不得机械重复写入公共对象名。库名、包名或一级目录已经表达领域时，主体命名只保留真正区分职责的词。

| 类型             | 前缀    | 示例                    | 实例变量前缀 |
|----------------|-------|----------------------|---------|
| PROGRAM        | `PRG_` | `PRG_MainControl`    | —       |
| FUNCTION_BLOCK | `FB_`  | `FB_MotorController` | `fb`    |
| FUNCTION       | `F_`   | `F_CalculateSpeed`   | —       |
| METHOD         | `M_`   | `M_Initialize`       | —       |
| ACTION         | `A_`   | `A_Start`            | —       |
| STRUCT         | `ST_`  | `ST_AxisRef`         | `st`    |
| ENUM           | `E_`   | `E_MotorMode`        | `e`     |
| UNION          | `U_`   | `U_DataConvert`      | `u`     |
| INTERFACE      | `I_`   | `I_Control`          | `itf`   |
| GVL            | `GVL_` | `GVL_System`         | —       |

### 公共对象名禁止下划线污染

以下命名全部禁止：

| 错误命名 | 问题 | 正确方向 |
|---|---|---|
| `FB_JSON_ToStruct` | 旧全大写缩写 + 主体继续用 `_` | `FB_JsonToStruct`，更推荐按职责命名为 `FB_JsonParser` |
| `F_JSON_ValueToString` | 机械切词，主体不是 PascalCase | `F_JsonValueToString` |
| `ST_JSON_ExampleStruct_1` | 主体含多个 `_`，编号语义弱 | `ST_JsonExampleStruct` 或按业务语义重命名 |
| `PRG_Test_JSON_Array` | 测试对象名被下划线拆碎 | `PRG_TestJsonArray` |

行业缩写在公共对象名中按 PascalCase 处理，不使用全大写堆叠：

| 技术词 | 公共对象名写法 | 示例 |
|---|---|---|
| JSON | `Json` | `FB_JsonParser` |
| XML | `Xml` | `F_XmlEscapeString` |
| TCP | `Tcp` | `FB_TcpClient` |
| UDP | `Udp` | `FB_UdpServer` |
| HTTP | `Http` | `FB_HttpRequest` |
| SQL | `Sql` | `F_SqlBuildWhere` |
| CSV | `Csv` | `F_CsvEncodeLine` |
| IO | `Io` | `ST_IoChannel` |
| ID | `Id` | `ST_DeviceId` |
| URL / URI | `Url` / `Uri` | `F_ParseUrl` |

允许在变量名中沿用项目既有缩写大小写，例如 `sClientId`、`bTcpConnected`；但程序单元、DUT、GVL 等公共对象名必须遵守上表。

---

### 库域上下文词去重

公共对象名的主体必须表达对象职责，而不是重复库的领域标签。若当前交付对象已经位于某个明确领域库中，例如曲线规划库、矩阵库、滤波库、数组操作库、时间库或掉电保持库，库域词已经由工程和库名提供，不应在每个 IEC 单元名称中再次出现。

| 场景 | 错误命名 | 正确方向 |
|---|---|---|
| 曲线规划库 | `FB_CurveArchimedeanSpiral` | `FB_ArchimedeanSpiral` |
| 曲线规划库 | `F_CurveBlendCubic` | `F_BlendCubic` |
| 矩阵库 | `F_MatrixLrealMultiply` | `F_LrealMultiply` |
| 滤波库 | `FB_FilterMovingAverage` | `FB_MovingAverage` |
| 数组操作库 | `F_ArrayDintSortAsc` | `F_DintSortAsc` |
| 时间库 | `FB_TimeDelayOn` | `FB_DelayOn` |
| 掉电保持库 | `FB_RetainStructToM` | `FB_StructToM` |

允许保留的情况：

- 类型族区分必须存在，例如字符串库中 `String / WString` 成对出现时，`FB_StringBuilder` 与 `FB_WStringBuilder` 可以保留类型族词。
- IEC 标准或行业通用术语本身包含该词，例如 `TimeSpan`、`DateTime`、`KalmanFilter` 等确有标准含义时，可以按语义保留或改成更准确名称。
- 去掉域词后会与同库其他公共对象重名，或会破坏已冻结的外部公共 API；此时必须在 rename-map 中说明保留原因。
- 第三方库固定接口、平台库固定对象名或外部协议字段不按本规则强制改名。

重命名流程：

1. 先识别库域词、类型族词和必须保留的标准术语。
2. 再输出 rename-map，覆盖文件名、声明名、引用、注释和测试入口。
3. 最后核对全工程命名引用一致性；按用户选择执行静态检查或由独立工程流程验证编译，本技能不要求执行工具。

---

## 变量命名（匈牙利命名法）

格式：`前缀驼峰命名`（前缀小写，后续单词首字母大写）

本技能自定义的 `VAR_INPUT / VAR_OUTPUT / VAR_IN_OUT / VAR / VAR_GLOBAL / VAR_TEMP` 变量声明必须执行本表前缀规则。PLCopen、PackML、CODESYS 标准库或厂商库已有的固定引脚名、枚举名和属性名，例如库调用参数 `Execute`、`Done`、`Busy`、`Error`、`ErrorID`、`Enable`、`Valid`，只能在调用外部库对象或解释外部标准语义时原样引用；它们不构成本技能自定义 POU 变量声明的豁免。自定义 FB 若需要同类语义，必须写成 `bExecute / bDone / bBusy / bError / diErrorID / bEnable / bValid`。

### 基本类型

| 类型    | 前缀   | 示例              |
|-------|------|-----------------|
| BOOL  | `b`  | `bMotorRunning` |
| BYTE  | `by` | `byStatus`      |
| WORD  | `w`  | `wCommand`      |
| DWORD | `dw` | `dwCount`       |
| LWORD | `lw` | `lwTotal`       |
| INT   | `i`  | `iCounter`      |
| DINT  | `di` | `diPosition`    |
| SINT  | `si` | `siOffset`      |
| USINT | `usi`| `usiIndex`      |
| UINT  | `ui` | `uiIndex`       |
| UDINT | `udi`| `udiCount`      |
| LINT  | `li` | `liTimestamp`   |
| ULINT | `uli`| `uliTotal`      |
| REAL  | `r`  | `rTemperature`  |
| LREAL | `lr` | `lrVelocity`    |
| STRING| `s`  | `sDeviceName`   |
| TIME  | `t`  | `tDelay`        |
| ARRAY | `a`  | `aBufferData`   |
| STRUCT实例 | `st` | `stAxisRef` |
| ENUM实例   | `e`  | `eState`    |
| POINTER    | `p`  | `pData`     |

### 定时器 / 触发器实例

| 类型    | 前缀      | 示例              |
|-------|---------|-----------------|
| TON   | `ton`   | `tonDelay`      |
| TOF   | `tof`   | `tofReset`      |
| TP    | `tp`    | `tpPulse`       |
| R_TRIG| `rtrig` | `rtrigStart`    |
| F_TRIG| `ftrig` | `ftrigStop`     |

> 注意：`rtrig` / `ftrig` 是 R_TRIG / F_TRIG 实例的专用前缀，不使用通用的 `fb` 前缀。
> 其他 FB 实例（如 `FB_MotorControl`）使用 `fb` 前缀：`fbMotor`。

### 常量

| 类型 | 前缀   | 示例                        |
|----|------|-----------------------------|
| 常量 | `cn` | `cnMaxCount`, `cnTimeOut`   |

常量声明在 `VAR CONSTANT` 或 `VAR_GLOBAL CONSTANT` 块中。

---

## 枚举元素命名

枚举元素根据枚举的底层类型使用对应前缀：

```st
// INT 类型枚举 → i 前缀
TYPE E_Mode :
(
    iStop   := 0,
    iRun    := 1,
    iError  := 2
) INT;
END_TYPE

// WORD 类型枚举（位域）→ w 前缀
TYPE E_Status :
(
    wNone   := 16#0000,
    wActive := 16#0001,
    wError  := 16#8000
) WORD;
END_TYPE
```

枚举引用必须使用完整命名空间：`E_Mode.iRun`，不能裸用 `iRun`。

---

## I/O 变量命名

禁止在 VAR_INPUT / VAR_OUTPUT / VAR_IN_OUT 中使用方向前缀（`i_` / `o_` / `io_`）：

```st
// 错误
// 不要把 BOOL 输入写成方向前缀形式 i_bStart。

// 正确
VAR_INPUT
    bStart : BOOL;
END_VAR
```

---

## 全局变量命名

- 禁止使用 `g_` 前缀
- 普通全局变量：与局部变量命名一致
- 全局常量：使用 `cn` 前缀
- 保持性变量：使用 `RETAIN` 关键字，命名不变

```st
VAR_GLOBAL
    iSystemState    : INT;
    aBufferData     : ARRAY[0..99] OF BYTE;
END_VAR

VAR_GLOBAL CONSTANT
    cnMaxRetries    : INT  := 3;
    cnTimeOut       : TIME := T#5S;
END_VAR

VAR_GLOBAL RETAIN
    bSystemError    : BOOL;
    iErrorCode      : INT;
END_VAR
```

---

## 标准缩写

当变量名或程序单元名称太长、影响阅读或对齐时，应主动使用规范缩写。缩写必须可读、稳定、全工程一致，优先使用下表；下表没有覆盖时，优先沿用项目既有缩写，不得随意造词。

| 缩写       | 含义       | 缩写       | 含义       |
|----------|----------|----------|----------|
| Min/Max  | 最小/最大值   | Act      | 实际值      |
| Prev/Next| 前一个/下一个  | Old/New  | 旧值/新值    |
| Fwd/Bwd  | 正向/反向    | CW/CCW   | 顺时针/逆时针  |
| Avg      | 平均值      | Sum      | 总和       |
| Diff     | 差值       | Cnt      | 计数       |
| Len      | 长度       | Pos      | 位置       |
| Velo     | 速度       | Acc/Dec  | 加速度/减速度  |
| Err      | 错误       | Cmd      | 命令       |
| Ref      | 设定值/参考值  | Fbk      | 反馈值      |
| Trig     | 触发       | Ack      | 确认       |

---

## 命名检查清单

- [ ] 程序单元使用正确前缀（`FB_` / `F_` / `PRG_` 等）
- [ ] 公共对象名前缀后主体为 PascalCase，主体没有额外 `_`
- [ ] JSON / TCP / ID 等行业缩写在公共对象名中使用 `Json` / `Tcp` / `Id` 风格
- [ ] 旧对象重命名不是机械加前缀，而是完成语义归一和全工程同步替换
- [ ] 公共对象名没有重复库域上下文词；确需保留时已说明类型族、标准术语、冲突或兼容原因
- [ ] 变量使用匈牙利命名法前缀
- [ ] R_TRIG / F_TRIG 实例使用 `rtrig` / `ftrig` 前缀
- [ ] 常量使用 `cn` 前缀
- [ ] I/O 变量无方向前缀（无 `i_` / `o_` / `io_`）
- [ ] 枚举元素使用类型对应前缀（INT→`i`，WORD→`w`，BYTE→`by`）
- [ ] 枚举引用使用完整命名空间（`E_Mode.iRun`）
- [ ] 全局变量无 `g_` 前缀
- [ ] 命名不超过 32 字符；过长时使用规范缩写
- [ ] 同一概念的缩写全工程一致
