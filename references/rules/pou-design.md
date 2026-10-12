# POU 设计规则


> 适用场景：FB / FC / PRG 的选择与设计

---

## 1. POU 类型选择决策树

```
需要保存跨周期状态？
├── 是 → 使用 FUNCTION_BLOCK (FB)
└── 否 → 需要返回值？
         ├── 是 → 使用 FUNCTION (FC)
         └── 否 → 使用 PROGRAM (PRG)
                  （PRG 只用于顶层任务入口）
```

| POU 类型 | 有状态 | 返回值 | 实例化 | 典型用途 |
|---|---|---|---|---|
| `FUNCTION_BLOCK` | ✅ | 通过 VAR_OUTPUT | 必须实例化 | 电机控制、通信、状态机 |
| `FUNCTION` | ❌ | 直接返回 | 无需实例化 | 数学计算、类型转换、纯函数 |
| `PROGRAM` | ✅ | — | 自动实例化 | 任务入口、顶层协调 |

---

## 2. FUNCTION_BLOCK 设计规范

### 标准接口结构

```st
FUNCTION_BLOCK FB_MotorControl
VAR_INPUT
    bEnable         : BOOL  := FALSE;   // 使能电机
    rSetSpeed       : REAL  := 0.0;     // 目标速度 [rpm]
    tAccelTime      : TIME  := T#2S;    // 加速时间
END_VAR
VAR_OUTPUT
    bRunning        : BOOL;             // 电机运行中
    rActualSpeed    : REAL;             // 实际速度 [rpm]
    bError          : BOOL;             // 故障标志
    diErrorID       : DINT;             // 错误代码，0=无故障
END_VAR
VAR
    rtrigEnable     : R_TRIG;           // bEnable 上升沿检测
    iState          : INT := 0;         // 内部状态机
END_VAR
```

### 接口设计原则

| 原则 | 规则 |
|---|---|
| 标量 VAR_INPUT 必须有默认值 | 防止未连接时行为未定义；结构体、枚举、FB 引用等复合输入按编译器约束处理，不为消除静态门禁而制造 IDE 告警 |
| 自定义 FB 使用 `bError` + `diErrorID` 诊断输出 | 调用方必须能感知故障；外部库固定引脚保留原名 |
| 大型结构体用 VAR_IN_OUT | 避免复制开销 |
| 不在 VAR_INPUT 中传递指针 | 使用 VAR_IN_OUT 替代 |
| 接口确定后不随意修改 | VAR_INPUT/OUTPUT 是公共契约 |

---

## 3. FUNCTION 设计规范

```st
// FC 无状态，每次调用独立
FUNCTION F_SafeDivide : REAL
VAR_INPUT
    rDividend   : REAL := 0.0;
    rDivisor    : REAL := 1.0;
    rDefault    : REAL := 0.0;  // 除数为零时的返回值
END_VAR

IF ABS(rDivisor) > 1.0E-10 THEN
    F_SafeDivide := rDividend / rDivisor;
ELSE
    F_SafeDivide := rDefault;
END_IF;
```

**FC 的限制**：
- 不能包含 FB 实例（FB 有状态，FC 无状态）
- 不能使用 RETAIN 变量
- 不能有副作用（不修改全局变量）——推荐原则，非强制

---

## 4. 变量声明区规范

### 完整声明示例

```st
FUNCTION_BLOCK FB_Example
VAR_INPUT
    bExecute        : BOOL  := FALSE;       // 触发执行
    rTarget         : REAL  := 0.0;         // 目标值 [mm]
    tTimeout        : TIME  := T#10S;       // 超时时间
END_VAR
VAR_OUTPUT
    bDone           : BOOL;                 // 执行完成
    bBusy           : BOOL;                 // 执行中
    bError          : BOOL;                 // 发生错误
    diErrorID       : DINT;                 // 错误代码
END_VAR
VAR_IN_OUT
    stAxisData      : ST_AxisData;          // 轴数据（引用传递）
END_VAR
VAR
    rtrigExec       : R_TRIG;               // bExecute 上升沿
    tonTimeout      : TON;                  // 超时定时器
    iState          : INT := 0;             // 内部状态
    rSavedTarget    : REAL := 0.0;          // 保存的目标值
END_VAR
VAR_TEMP
    rTempCalc       : REAL;                 // 临时计算（不放 FB 实例！）
END_VAR
```

---

## 5. FB 实例化规则

### 正确实例化

```st
// 在调用方的 VAR 区声明实例
VAR
    fbMotor1    : FB_MotorControl;  // 电机1控制
    fbMotor2    : FB_MotorControl;  // 电机2控制
    fbComm      : FB_TcpClient;     // TCP 通信
END_VAR

// 调用时传入参数
fbMotor1(
    bEnable   := bMotor1Enable,
    rSetSpeed := rMotor1Speed
    );
fbMotor2(
    bEnable   := bMotor2Enable,
    rSetSpeed := rMotor2Speed
    );
```

### 数组实例化（多个相同 FB）

```st
VAR
    afbMotors   : ARRAY[0..3] OF FB_MotorControl;
END_VAR

// 循环调用所有实例
FOR iIdx := 0 TO 3 DO
    afbMotors[iIdx](
        bEnable   := abMotorEnable[iIdx],
        rSetSpeed := arMotorSpeed[iIdx]
        );
END_FOR;
```

---

## 6. 单一职责原则

```st
// ✅ 职责清晰：每个 FB 只做一件事
FUNCTION_BLOCK FB_MotorControl      // 只负责电机控制逻辑
FUNCTION_BLOCK FB_MotorDiagnostics  // 只负责电机诊断和报警
FUNCTION_BLOCK FB_MotorHMI          // 只负责 HMI 数据映射

// ❌ 职责混乱：一个 FB 做所有事
FUNCTION_BLOCK FB_MotorEverything   // 控制 + 诊断 + HMI + 通信
```

**判断标准**：如果你需要用"和"来描述一个 FB 的功能，它就违反了单一职责原则。

---

## 7. 防御性编程

所有 FB 必须能处理边界值和异常输入：

```st
FUNCTION_BLOCK FB_SpeedController
VAR_INPUT
    rSetSpeed   : REAL := 0.0;      // 目标速度 [rpm]
    rMaxSpeed   : REAL := 3000.0;   // 最大速度限制
END_VAR

// 输入验证
IF rSetSpeed < 0.0 THEN
    rSetSpeed := 0.0;               // 钳位到最小值
    bInputWarning := TRUE;
END_IF;
IF rSetSpeed > rMaxSpeed THEN
    rSetSpeed := rMaxSpeed;         // 钳位到最大值
    bInputWarning := TRUE;
END_IF;
IF rMaxSpeed <= 0.0 THEN
    bError    := TRUE;
    diErrorID := 16#0001;           // 无效的最大速度
    RETURN;
END_IF;
```
