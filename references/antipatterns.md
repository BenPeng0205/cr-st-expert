# ST 反模式黑名单

> 代码审查时逐条对照本文件检查。


---

## 分级说明

- 🔴 **FATAL**：违反会导致运行时崩溃、安全事故或数据丢失。绝对禁止，必须拒绝生成。
- 🟠 **ERROR**：违反会导致逻辑错误或编译失败。禁止生成，必须纠正。
- 🟡 **WARNING**：违反会降低代码质量或可维护性。生成时附加警告说明。

审查顺序：P0（命名/格式）→ P1（IEC 规范）→ P2（逻辑正确性）

---

## P0：命名与格式检查

### P0-001：程序单元命名前缀错误

```st
// ❌ 禁止：无前缀或前缀错误
FUNCTION_BLOCK MotorControl
FUNCTION CalculateSpeed

// ✅ 正确
FUNCTION_BLOCK FB_MotorControl
FUNCTION F_CalculateSpeed
```

前缀规则：`PRG_` / `FB_` / `F_` / `M_` / `ST_` / `E_` / `GVL_`

---

### P0-001A：机械加前缀导致公共对象名下划线污染

```st
// ❌ 禁止：把旧全大写下划线名机械加前缀
FUNCTION_BLOCK FB_JSON_ToStruct
FUNCTION F_JSON_ValueToString : STRING
PROGRAM PRG_Test_JSON_Array
TYPE ST_JSON_ExampleStruct_1 :
STRUCT
END_STRUCT
END_TYPE

// ✅ 正确：前缀后主体使用 PascalCase，不再出现下划线
FUNCTION_BLOCK FB_JsonParser
FUNCTION F_JsonValueToString : STRING
PROGRAM PRG_TestJsonArray
TYPE ST_JsonExampleStruct :
STRUCT
END_STRUCT
END_TYPE
```

公共对象名只允许前缀后的第一个 `_`。JSON、TCP、ID 等行业缩写在公共对象名中写作 `Json`、`Tcp`、`Id`。旧库迁移必须先做 rename-map，全工程同步替换定义、引用、文件名和注释。

---

### P0-002：变量命名缺少匈牙利前缀

```st
// ❌ 禁止
Start : BOOL;
Counter : INT;
Delay : TON;
TrigStart : R_TRIG;

// ✅ 正确
bStart      : BOOL;
iCounter    : INT;
tonDelay    : TON;
rtrigStart  : R_TRIG;
```

R_TRIG / F_TRIG 实例使用 `rtrig` / `ftrig` 前缀，不使用通用 `fb` 前缀。常量使用 `cn` 前缀。

---

### P0-003：I/O 变量使用方向前缀

```st
// ❌ 禁止：不要把 BOOL 输入写成方向前缀形式 i_bStart。

// ✅ 正确：仅使用类型前缀
VAR_INPUT
    bStart : BOOL;
END_VAR
```

---

### P0-004：枚举元素前缀与底层类型不匹配

```st
// ❌ 禁止：INT 枚举用 e 前缀
TYPE E_Mode : (eStop := 0, eRun := 1) INT;

// ✅ 正确：INT 枚举用 i 前缀，WORD 枚举用 w 前缀
TYPE E_Mode : (iStop := 0, iRun := 1) INT;
```

---

### P0-005：使用 `(* *)` 注释

```st
// ❌ 禁止：使用 IEC 块注释语法

// ✅ 正确：使用 // 或 ///
```

---

### P0-006：POU 写了结束标记

```st
// ❌ 禁止：CoDeSys 自动管理 POU 结束标记，手写会导致编译错误
END_FUNCTION_BLOCK
END_FUNCTION
END_METHOD
END_PROGRAM

// ✅ 正确：STRUCT / ENUM / VAR 块必须写结束标记
END_STRUCT
END_TYPE
END_VAR
```

---

### P0-007：变量声明顺序错误

正确顺序：`VAR_INPUT` → `VAR_OUTPUT` → `VAR_IN_OUT` → `VAR` → `VAR CONSTANT`

---

## P1：IEC 规范与 CoDeSys 平台检查

### P1-001：枚举缺少 `qualified_only` 或 `strict`

```st
// ❌ 禁止：枚举值注入全局命名空间，可能与其他枚举冲突
TYPE E_Mode : (iStop := 0, iRun := 1) INT;

// ✅ 正确
{attribute 'qualified_only'}
{attribute 'strict'}
TYPE E_Mode : (iStop := 0, iRun := 1) INT;
```

---

### P1-002：GVL 缺少 `qualified_only`

```st
// ❌ 禁止：全局变量可裸名访问，多 GVL 时存在命名冲突风险
VAR_GLOBAL
    iState : INT;
END_VAR

// ✅ 正确
{attribute 'qualified_only'}
VAR_GLOBAL
    iState : INT;
END_VAR
```

---

### P1-003：FB / FC 缺少 `hide_all_locals`

```st
// ❌ 禁止：内部变量对外暴露
FUNCTION_BLOCK FB_Motor

// ✅ 正确
{attribute 'hide_all_locals'}
FUNCTION_BLOCK FB_Motor
```

---

### P1-004：枚举引用不使用完整命名空间

```st
// ❌ 禁止：裸名访问，来源不明，可能与其他枚举冲突
IF eState = iStop THEN ...

// ✅ 正确
IF eState = E_Mode.iStop THEN ...
```

---

### P1-005：使用 CHAR 类型

```st
// ❌ 禁止：CHAR 与字符串库函数不兼容
cChar : CHAR;

// ✅ 正确
sChar : STRING(1);
```

---

### P1-006：用 `+` 拼接字符串

```st
// ❌ 禁止：IEC 61131-3 未定义 STRING 的 + 运算符
sResult := sA + sB;

// ✅ 正确
sResult := CONCAT(sA, sB);
```

---

### P1-007：使用 VAR_STAT 在 FB 中声明实例状态

```st
// ❌ 禁止：VAR_STAT 在 FB 中是所有实例共享的，不是每实例独立的
FUNCTION_BLOCK FB_Counter
VAR_STAT
    iCount : INT;   // 所有 FB_Counter 实例共享！
END_VAR

// ✅ 正确：FB 内部状态用 VAR
VAR
    iCount : INT;
END_VAR
```

---

### P1-008：隐式窄化类型转换

```st
// ❌ 禁止：DINT → INT 隐式截断，无警告
iResult := diLargeValue;

// ✅ 正确：显式转换
iResult := DINT_TO_INT(diLargeValue);
```

---

### P1-009：全局变量使用 `g_` 前缀

```st
// ❌ 禁止
g_iState : INT;

// ✅ 正确：无方向前缀，直接用类型前缀
iState : INT;
```

---

## 🔴 FATAL 级反模式

### AP-001：条件调用边沿检测 FB

```st
// ❌ 禁止：只在条件满足时调用，FB 内部状态丢失
IF bCondition THEN
    fbTrig(
        CLK := bSignal
        );
END_IF;

// ✅ 必须：每周期无条件调用
rtrigSignal(
    CLK := bSignal
    );
IF bCondition AND rtrigSignal.Q THEN
    // 处理上升沿
END_IF;
```

**原因**：R_TRIG / F_TRIG 是有状态 FB，内部保存上一周期的 CLK 值。条件调用导致状态不连续，边沿检测失效。

---

### AP-002：VAR_TEMP 中实例化 FB

```st
// ❌ 禁止：VAR_TEMP 每次调用都是新实例，状态全部丢失
VAR_TEMP
    tonTimer    : TON;
    rtrigSignal : R_TRIG;
END_VAR

// ✅ 必须：FB 实例在 VAR 区
VAR
    tonTimer    : TON;
    rtrigSignal : R_TRIG;
END_VAR
```

**原因**：VAR_TEMP 在每次 POU 调用时重新分配，FB 的内部状态（计时值、上一周期状态）全部清零。

---

### AP-003：浮点数直接比较

```st
// ❌ 禁止：IEEE 754 浮点精度问题，可能永远不相等
IF rSpeed = 100.0 THEN ...
IF rPosition = 0.0 THEN ...

// ✅ 必须：使用容差比较
IF ABS(rSpeed - 100.0) < 0.001 THEN ...
IF ABS(rPosition) < 1.0E-6 THEN ...
```

---

### AP-004：除法前不检查除数

```st
// ❌ 禁止：除数为零导致运行时异常
rResult := rA / rB;

// ✅ 必须：先检查除数
IF ABS(rB) > 1.0E-10 THEN
    rResult := rA / rB;
    bError := FALSE;
ELSE
    rResult := 0.0;
    bError := TRUE;
END_IF;
```

---

### AP-005：Abort 后直接 Reset（PackML）

```st
// ❌ 禁止：跳过 Clear，故障上下文未清除
// ABORTED → Reset → RESETTING  ← 错误！

// ✅ 必须：完整路径
// ABORTED → Clear → CLEARING → SC → STOPPED → Reset → RESETTING
```

---

### AP-006：SC 信号做成电平而非脉冲

```st
// ❌ 禁止：电平型 SC 导致 Acting state 被反复退出
bStateComplete := TRUE;  // 一直保持 TRUE

// ✅ 必须：SC 是上升沿脉冲，触发后必须清零
bStateComplete := TRUE;   // 置位一个周期
// 下一周期：
bStateComplete := FALSE;  // 清零
```

---

## 🟠 ERROR 级反模式

### AP-007：CASE 语句缺少 ELSE 分支

```st
// ❌ 禁止：非法状态值无处理，行为未定义
CASE eState OF
    E_State.Idle:    ...
    E_State.Running: ...
END_CASE;

// ✅ 必须：始终有 ELSE
CASE eState OF
    E_State.Idle:    ...
    E_State.Running: ...
ELSE
    // 非法状态：记录诊断，进入安全状态
    bError := TRUE;
    eState := E_State.Idle;
END_CASE;
```

---

### AP-008：Hold 与 Suspend 语义混用

```st
// ❌ 禁止：把外部原因（上游缺料）做成 Hold
IF NOT bMaterialReady THEN
    CntrlCmd := E_PackMLCmd.Hold;  // 错误：缺料是外部原因
END_IF;

// ✅ 必须：外部原因用 Suspend，内部原因用 Hold
IF NOT bMaterialReady THEN
    CntrlCmd := E_PackMLCmd.Suspend;    // 外部原因 → Suspend
END_IF;
IF bInternalFault THEN
    CntrlCmd := E_PackMLCmd.Hold;       // 内部原因 → Hold
END_IF;
```

---

### AP-009：不等 StateChangeInProcess 清零就发下一个命令

```st
// ❌ 禁止：命令覆盖，在错误状态触发
Command.CntrlCmd := 2;  // Start
Command.CmdChangeRequest := TRUE;
Command.CntrlCmd := 3;  // 立刻发 Stop，覆盖 Start

// ✅ 必须：等待握手完成
IF NOT Status.StateChangeInProcess THEN
    Command.CntrlCmd := 2;
    Command.CmdChangeRequest := TRUE;
END_IF;
```

---

### AP-010：在 Execute 状态中修改配方参数

```st
// ❌ 禁止：运行中改配方，语义混乱
IF eState = E_PackMLState.Execute THEN
    Command.Recipe[0].ProcessVariables.Parameter_REAL[0].Value := rNewSpeed;
END_IF;

// ✅ 必须：在 STOPPED 或 IDLE 时交换配方
IF eState = E_PackMLState.Idle OR eState = E_PackMLState.Stopped THEN
    Command.Recipe[0].ProcessVariables.Parameter_REAL[0].Value := rNewSpeed;
END_IF;
```

---

### AP-011：WHILE 循环无安全计数器

```st
// ❌ 禁止：条件永远不满足时死循环，看门狗超时
WHILE NOT bDone DO
    // 处理
END_WHILE;

// ✅ 必须：加安全计数器
iSafetyCount := 0;
WHILE NOT bDone AND iSafetyCount < 1000 DO
    // 处理
    iSafetyCount := iSafetyCount + 1;
END_WHILE;
IF iSafetyCount >= 1000 THEN
    bError := TRUE;  // 超限报警
END_IF;
```

---

### AP-012：数组访问不检查边界

```st
// ❌ 禁止：越界访问导致内存覆盖
arData[iIndex] := rValue;

// ✅ 必须：先检查索引范围
IF iIndex >= 0 AND iIndex <= SIZEOF(arData) / SIZEOF(arData[0]) - 1 THEN
    arData[iIndex] := rValue;
ELSE
    bError := TRUE;
END_IF;
```

---

### AP-013：不同类型之间隐式转换

```st
// ❌ 禁止：隐式转换可能截断或溢出
iResult := rFloatValue;      // REAL → INT，截断
rResult := iIntValue * 2.0;  // INT * REAL，隐式提升

// ✅ 必须：显式转换函数
iResult := REAL_TO_INT(rFloatValue);
rResult := INT_TO_REAL(iIntValue) * 2.0;
```

---

### AP-014：定时器触发后不重置

```st
// ❌ 禁止：TON 触发后 Q 一直为 TRUE，逻辑持续触发
fbTimer(
    IN := bStart,
    PT := T#5S
    );
IF fbTimer.Q THEN
    // 执行动作
    // 忘记重置 fbTimer.IN
END_IF;

// ✅ 必须：触发后重置 IN
tonTimer(
    IN := bStart,
    PT := T#5S
    );
IF tonTimer.Q THEN
    bStart := FALSE;  // 重置触发条件
    // 执行动作
END_IF;
```

---

### AP-015：Holding/Suspending 未保存设定值

```st
// ❌ 禁止：进入 Hold/Suspend 前不保存状态，恢复后无法还原
E_PackMLState.Holding:
    // 直接进入 Held，不保存任何东西
    bStateComplete := TRUE;

// ✅ 必须：保存恢复所需的 set-point 和过程状态
E_PackMLState.Holding:
    rSavedSpeed    := rCurrentSpeed;
    rSavedPosition := rCurrentPosition;
    bStateComplete := TRUE;
```

---

## 🟡 WARNING 级反模式

### AP-016：全局变量滥用

```st
// ⚠️ 警告：全局变量增加耦合，难以追踪数据流
// 应优先使用 VAR_IN_OUT 传递大型结构体
// 全局变量仅用于：机器状态、报警、跨任务共享数据
```

---

### AP-017：STRING 操作不检查长度

```st
// ⚠️ 警告：超长字符串被截断，可能丢失数据
// 必须在 CONCAT / MID / INSERT 前检查结果长度
IF LEN(sSource) + LEN(sAppend) <= 80 THEN
    sResult := CONCAT(sSource, sAppend);
END_IF;
```

---

### AP-018：IF 嵌套超过 3 层

```st
// ⚠️ 警告：深层嵌套难以阅读和维护
// 超过 3 层时，考虑提取子 FB 或使用 CASE 语句
```

---

### AP-019：使用 2015 版 PackTags 结构

```st
// ⚠️ 警告：2015 版标签在 2022 版中已删除或重命名
// 禁止使用：Admin.ProdConsumedCount[#]  → 改用 Admin.ProductData[#].ConsumedCount
// 禁止使用：Command/Status.Parameter[#] → 改用 Parameter_REAL/STRING/LREAL/DINT
// 禁止使用：Command/Status.RemoteInterface[#] → 已删除
```

---

### AP-020：运动控制 FB 不检查 Error 输出

```st
// ⚠️ 警告：忽略 Error 输出导致轴故障无法感知
fbMove(
    Execute := bStart,
    ...
    );
// 只检查 Done，不检查 Error
IF fbMove.Done THEN ...

// ✅ 必须：同时处理 Done 和 Error
fbMove(
    Execute := bStart,
    ...
    );
IF fbMove.Done THEN
    // 成功处理
ELSIF fbMove.Error THEN
    diErrorID := fbMove.ErrorID;
    bAxisError := TRUE;
END_IF;
```
