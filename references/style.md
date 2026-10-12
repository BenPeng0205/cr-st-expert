# 代码风格规范

> 适用范围：所有 CoDeSys ST 程序单元的注释、缩进、对齐、格式

---

## 注释规范

### 注释符号

| 类型   | 符号    | 位置         | 用途              |
|------|-------|------------|-----------------|
| 段落注释 | `///` | 代码段落上方     | 逻辑分区、多行说明       |
| 行内注释 | `//`  | 代码行右侧      | 说明单行代码          |

禁止使用 `(* *)` 注释方式。

注释必须体现工程判断：重要逻辑、算法、公式、状态转换、边界保护、异常兜底、平台特殊处理要解释原因和风险；简单赋值、直观条件判断、变量名已经足够清晰的代码不要重复解释。注释质量按“工程师能否通过注释看懂本段逻辑”判断，禁止用“复杂段至少几条注释”这类数量指标替代真实可读性。关键块优先使用 1~2 句高密度说明，避免教学式展开。

### 文件头注释

FB / FC / PRG 文件头（放在 `{attribute}` 和 POU 声明之前）：

```st
/// 功能    : 功能描述
/// 库依赖  : 暂无
{attribute 'hide_all_locals'}

FUNCTION_BLOCK FB_Example
```

文件头只保留功能、库依赖等稳定工程信息，禁止出现编程人员、时间、版本。无外部库写 `暂无`；已使用外部库但名称或版本未知时明确标为待确认，不以 `暂无` 掩盖依赖。

STRUCT / ENUM 文件头：

```st
/// 功能    : 功能描述
/// 库依赖  : 暂无
{attribute 'qualified_only'}
{attribute 'strict'}

TYPE E_Mode :
```

### 程序功能注释块

放在 `// === IMPLEMENTATION ===` 之后，作为实现区最上方内容；禁止放在变量声明区：

```st
// === IMPLEMENTATION ===

/// =======================================================================
/// 名称      : FB_Example
/// 功能      : 详细功能描述
/// 库依赖    : Standard
/// =======================================================================
/// 使用说明  : 1. 说明1
///           : 2. 说明2
/// =======================================================================
```

完整功能注释块必须包含 `名称`、`功能`、`库依赖`、`使用说明`。内置聚合文本样例需要说明子对象在父 FB 内的组织方式；用户原生 IDE 工程按实际对象结构说明，不要求回写工具。
`使用说明` 必须至少写两条编号内容：`1.` 说明调用条件或文件拆分边界，`2.` 说明关键使用约束。禁止只写一行概括性描述。

### 注释层级

连续长代码中，使用两级注释区分主要段落和次要段落：

**大段分隔**（主要逻辑区块，如状态机主体、持续运行区、初始化区）：

```st
/// =======================================================================
/// 主序列状态机
/// =======================================================================
CASE eSeqState OF
    ...
END_CASE;
```

**小段注释**（大段内的次要逻辑分组）：

```st
/// 边沿检测（无条件，每周期调用）
rtrigStart(
    CLK := bStartCmd
    );
rtrigStop(
    CLK := bStopCmd
    );

/// 状态变化检测
IF eState <> ePrevState THEN
    bFirstScan := TRUE;
    ePrevState := eState;
END_IF;
```

**完整示例**（大段 + 小段组合）：

```st
/// =======================================================================
/// 持续运行逻辑
/// =======================================================================

/// 边沿检测（无条件，每周期调用）
rtrigStart(
    CLK := bStartCmd
    );
rtrigStop(
    CLK := bStopCmd
    );

/// 状态变化检测
IF eState <> ePrevState THEN
    bFirstScan := TRUE;
    ePrevState := eState;
    tonActingTimeout(
        IN := FALSE
        );
END_IF;

/// 超时定时器（无条件调用）
tonActingTimeout(
    IN := (eState = E_State.iStarting),
    PT := tActingTimeout
    );

/// =======================================================================
/// 主状态机
/// =======================================================================
CASE eState OF

    E_State.iIdle:
        /// 进入动作
        IF bFirstScan THEN
            bFirstScan := FALSE;
            bRunning   := FALSE;
        END_IF;
        IF rtrigStart.Q THEN
            eState := E_State.iRunning;
        END_IF;

ELSE
    bError    := TRUE;
    diErrorID := 16#FFFF;
    eState    := E_State.iError;

END_CASE;
```

---

## 缩进与对齐

### 基本规则

- 缩进宽度：4 个空格
- 缩进方式：仅使用空格，禁止 Tab
- 变量声明：使用空格补齐，让 `:` / `:=` / `//` 三列尽量垂直对齐

### 变量声明对齐

```st
VAR
    bStart          : BOOL;                 // 启动信号
    iCounter        : INT;                  // 计数器
    rSetValue       : REAL  := 100.0;       // 设定值
    sDeviceName     : STRING := 'Motor1';   // 设备名称
    tonDelay        : TON;                  // 延时定时器
    rtrigStart      : R_TRIG;              // 启动上升沿
END_VAR
```

### 控制结构缩进

```st
IF bCondition THEN
    IF bSubCondition THEN
        iValue := iValue + 1;
    END_IF;
END_IF;

CASE iStep OF
    0:  // 初始化
        iCounter := 0;

    10: // 运行
        iCounter := iCounter + 1;

ELSE
    iStep := 0;
END_CASE;
```

### 功能块调用格式

```st
fbMotor(
    bEnable         := bStart,
    iSpeedSet       := iTargetSpeed,
    bRunning        => bMotorRun,
    iActualSpeed    => iFeedback
    );
```

引脚每行一个，使用空格补齐让 `:=` 和 `=>` 对齐，结尾 `);` 缩进对齐。输出引脚只有在存在语义匹配的接收变量时才使用 `=>` 映射，禁止为了格式完整把输出机械接到含义不匹配的变量。

### 复杂条件换行

```st
IF (bStart = TRUE) AND
    (iCounter < cnMaxCount) AND
    (rTemp > 20.0) THEN
    bReady := TRUE;
END_IF;
```

---

## 变量声明顺序

```st
VAR_INPUT       // 1. 输入变量
    ...
END_VAR

VAR_OUTPUT      // 2. 输出变量
    ...
END_VAR

VAR_IN_OUT      // 3. 输入输出变量
    ...
END_VAR

VAR             // 4. 本地变量
    ...
END_VAR

VAR CONSTANT    // 5. 常量
    ...
END_VAR
```

---

## 结束标记规则

| 程序单元              | 结束标记     | 说明                    |
|-------------------|----------|-----------------------|
| PROGRAM           | 不写       | CoDeSys 自动管理          |
| FUNCTION_BLOCK    | 不写       | CoDeSys 自动管理          |
| FUNCTION          | 不写       | CoDeSys 自动管理          |
| METHOD            | 不写       | CoDeSys 自动管理          |
| STRUCT            | 必须写 `END_STRUCT` | 数据类型声明区无自动管理 |
| ENUM              | 必须写 `END_TYPE`   | 数据类型声明区无自动管理 |
| VAR 块            | 必须写 `END_VAR`    | 变量声明区无自动管理     |

---

## 空格规范

- 运算符两侧必须有空格：`iA + iB`，`iResult := iA * iB`
- 逗号后必须有空格：`Func(a, b, c)`
- 变量声明冒号前至少留 1 个空格，可增加空格按声明块对齐；冒号后至少留 1 个空格：`bStart : BOOL`
- 赋值符前后有空格：`iVal := 0`

---

## 嵌套限制

代码嵌套不超过 3 级。超过时考虑提取子 FB 或用逻辑运算符合并条件：

```st
// 避免
IF bStart THEN
    IF iState = 0 THEN
        IF bReady THEN
            ...
        END_IF;
    END_IF;
END_IF;

// 推荐
IF bStart AND (iState = 0) AND bReady THEN
    ...
END_IF;
```

---

## CoDeSys 属性声明

### FB / FC / PRG

```st
{attribute 'hide_all_locals'}
FUNCTION_BLOCK FB_Example
```

`hide_all_locals` 隐藏所有局部变量，防止外部直接访问内部状态，强制通过 VAR_OUTPUT 接口读取数据。

PRG / PROGRAM 禁止使用 `{attribute 'hide_all_locals'}`。

### ENUM

```st
{attribute 'qualified_only'}
{attribute 'strict'}
TYPE E_Mode :
```

- `qualified_only`：强制使用完整命名空间访问（`E_Mode.iRun`），防止裸名冲突
- `strict`：禁止枚举值与整数之间的隐式转换，防止类型混用

### GVL

```st
{attribute 'qualified_only'}
VAR_GLOBAL
    iSystemState : INT;
END_VAR
```

`qualified_only` 强制使用 `GVL_System.iSystemState` 访问，防止多个 GVL 之间的命名冲突。

---

## 格式检查清单

- [ ] 使用 4 个空格缩进，禁止 Tab
- [ ] 变量声明使用空格补齐，让 `:` / `:=` / `//` 三列尽量对齐
- [ ] 运算符和逗号两侧有空格
- [ ] 代码嵌套不超过 3 级
- [ ] POU 不写结束标记，STRUCT / ENUM / VAR 块保留
- [ ] 使用 `//` 或 `///`，禁用 `(* *)`
- [ ] FB / FC 有 `{attribute 'hide_all_locals'}`
- [ ] PRG / PROGRAM 没有 `{attribute 'hide_all_locals'}`
- [ ] ENUM 有 `{attribute 'qualified_only'}` + `{attribute 'strict'}`
- [ ] GVL 有 `{attribute 'qualified_only'}`
- [ ] 文件头没有编程人员、时间、版本
- [ ] 文件头 `库依赖` 明确；无外部库写 `暂无`，未知外部依赖写待确认
- [ ] FB / FC / PRG 的完整功能注释块位于 `// === IMPLEMENTATION ===` 之后
- [ ] 完整功能注释块包含 `名称`、`功能`、`库依赖`、`使用说明`
- [ ] 重要逻辑有清晰注释，简单代码没有过度注释
- [ ] 注释解释了当前对象的实际算法、状态保持、边界分支、单位换算或函数调用语义，没有使用泛化模板话术凑数量
- [ ] 数字公差和经验常量只写用途与工程边界，不展开替代常量比较
- [ ] 有物理单位的变量注释使用 `[unit]` 格式
