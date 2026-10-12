# 状态机完整模板


> 适用场景：通用状态机、带进入/退出动作、带超时保护

---

## 1. 通用状态机 FB 模板（带进入/退出动作）

```st
/// 功能    : 通用状态机功能块
/// 库依赖  : Standard

{attribute 'hide_all_locals'}
FUNCTION_BLOCK FB_StateMachine
VAR_INPUT
    bEnable         : BOOL := FALSE;    // 使能，FALSE 时复位到初始状态
    bAbortCmd       : BOOL := FALSE;    // 中止命令，最高优先级
    bStartCmd       : BOOL := FALSE;    // 启动命令
    bResetCmd       : BOOL := FALSE;    // 复位命令
    tStepTimeout    : TIME := T#30S;    // 单步超时时间
END_VAR
VAR_OUTPUT
    eCurrentState   : E_SM_State;       // 当前状态（供外部监控）
    bRunning        : BOOL;             // 状态机运行中
    bDone           : BOOL;             // 完成标志
    bError          : BOOL;             // 错误标志
    diErrorID       : DINT;             // 错误代码
END_VAR
VAR
    ePrevState      : E_SM_State := E_SM_State.iIdle;
    bFirstScan      : BOOL := TRUE;     // 进入新状态的第一个周期
    tonStepTimer    : TON;              // 步骤超时定时器
    rtrigAbort      : R_TRIG;           // Abort 上升沿
    rtrigStart      : R_TRIG;           // Start 上升沿
    rtrigReset      : R_TRIG;           // Reset 上升沿
END_VAR

// === IMPLEMENTATION ===

/// =======================================================================
/// 名称      : FB_StateMachine
/// 功能      : 通用状态机模板，展示进入动作、超时保护和命令优先级
/// 库依赖    : Standard
/// =======================================================================

/// 边沿检测（无条件，每周期调用）
rtrigAbort(
    CLK := bAbortCmd
    );
rtrigStart(
    CLK := bStartCmd
    );
rtrigReset(
    CLK := bResetCmd
    );

/// 未使能时复位
IF NOT bEnable THEN
    eCurrentState := E_SM_State.iIdle;
    bRunning      := FALSE;
    bDone         := FALSE;
    bError        := FALSE;
    diErrorID     := 0;
    RETURN;
END_IF;

/// 状态变化检测（进入动作机制）
IF eCurrentState <> ePrevState THEN
    bFirstScan := TRUE;
    ePrevState := eCurrentState;
    tonStepTimer(
        IN := FALSE
        );                              // 重置超时定时器
END_IF;

/// 超时定时器（每周期更新）
tonStepTimer(
    IN := bRunning,
    PT := tStepTimeout
    );

/// 命令优先级检查（在 CASE 之前）
IF rtrigAbort.Q THEN
    eCurrentState := E_SM_State.iError;
    diErrorID     := 16#0001;           // 外部中止
END_IF;

/// =======================================================================
/// 主状态机
/// =======================================================================
CASE eCurrentState OF

    E_SM_State.iIdle:
        IF bFirstScan THEN
            bFirstScan  := FALSE;
            bRunning    := FALSE;
            bDone       := FALSE;
            bError      := FALSE;
        END_IF;
        IF rtrigStart.Q THEN
            eCurrentState := E_SM_State.iStep1;
        END_IF;

    E_SM_State.iStep1:
        IF bFirstScan THEN
            bFirstScan  := FALSE;
            bRunning    := TRUE;
            bDone       := FALSE;
            // 在此执行步骤1的初始化
        END_IF;
        IF tonStepTimer.Q THEN
            diErrorID     := 16#0010;   // Step1 超时
            eCurrentState := E_SM_State.iError;
        END_IF;
        // 持续动作：每周期执行
        // IF <Step1完成条件> THEN
        //     eCurrentState := E_SM_State.iStep2;
        // END_IF

    E_SM_State.iStep2:
        IF bFirstScan THEN
            bFirstScan := FALSE;
            // Step2 初始化
        END_IF;
        IF tonStepTimer.Q THEN
            diErrorID     := 16#0020;
            eCurrentState := E_SM_State.iError;
        END_IF;
        // IF <Step2完成条件> THEN
        //     eCurrentState := E_SM_State.iDone;
        // END_IF

    E_SM_State.iDone:
        IF bFirstScan THEN
            bFirstScan  := FALSE;
            bRunning    := FALSE;
            bDone       := TRUE;
        END_IF;
        IF rtrigReset.Q THEN
            bDone         := FALSE;
            eCurrentState := E_SM_State.iIdle;
        END_IF;

    E_SM_State.iError:
        IF bFirstScan THEN
            bFirstScan  := FALSE;
            bRunning    := FALSE;
            bError      := TRUE;
        END_IF;
        // 等待复位
        IF rtrigReset.Q THEN
            bError        := FALSE;
            diErrorID     := 0;
            eCurrentState := E_SM_State.iIdle;
        END_IF;

ELSE
    // 非法状态：安全处理
    bError        := TRUE;
    diErrorID     := 16#FFFF;
    eCurrentState := E_SM_State.iError;

END_CASE;
```

### 配套枚举类型

```st
/// 功能    : 状态机状态枚举
/// 库依赖  : 暂无

{attribute 'qualified_only'}
{attribute 'strict'}
TYPE E_SM_State :
(
    iInvalid    := 0,   // 非法状态，上电默认值，ELSE 分支捕获
    iIdle       := 1,   // 空闲，等待启动
    iStep1      := 2,   // 步骤1
    iStep2      := 3,   // 步骤2
    iDone       := 10,  // 完成
    iError      := 99   // 错误
) INT;
END_TYPE
```

---

## 2. 进入/退出动作模式详解

```st
// 关键：状态变化检测放在 CASE 之前
IF eCurrentState <> ePrevState THEN
    bFirstScan := TRUE;     // 标记进入新状态
    ePrevState := eCurrentState;
END_IF;

CASE eCurrentState OF
    E_SM_State.iStep1:
        /// 进入动作（只执行一次）
        IF bFirstScan THEN
            bFirstScan := FALSE;
            // 初始化该步骤的资源
            fbMotor(
                bEnable := TRUE
                );
            tonTimer(
                IN := FALSE
                );                      // 重置定时器
        END_IF;

        /// 持续动作（每周期执行）
        tonTimer(
            IN := TRUE,
            PT := T#5S
            );
        IF tonTimer.Q THEN
            // 退出动作（进入下一状态前的清理）
            fbMotor(
                bEnable := FALSE
                );
            eCurrentState := E_SM_State.iStep2;
        END_IF;
END_CASE;
```

---

## 3. 带子状态的嵌套状态机

```st
// 主状态机调用子状态机 FB
VAR
    fbSubSM     : FB_SubStateMachine;
    eMainState  : E_MainState;
END_VAR

CASE eMainState OF
    E_MainState.iProcessing:
        fbSubSM(
            bEnable  := TRUE,
            bStart   := bSubStart
            );
        IF fbSubSM.bDone THEN
            eMainState := E_MainState.iComplete;
        ELSIF fbSubSM.bError THEN
            diErrorID  := fbSubSM.diErrorID;
            eMainState := E_MainState.iError;
        END_IF;

    E_MainState.iComplete:
        fbSubSM(
            bEnable := FALSE
            );                          // 停止子状态机
        // ...
END_CASE;
```

---

## 4. 状态机设计检查清单

| 检查项 | 说明 |
|---|---|
| ✅ 每个状态都有 ELSE 分支 | 防止非法状态无限循环 |
| ✅ 命令优先级在 CASE 之前检查 | Abort 必须最高优先级 |
| ✅ 进入动作用 bFirstScan 保护 | 避免重复初始化 |
| ✅ 每个 Acting 状态有超时保护 | 防止卡死 |
| ✅ 错误状态需要显式复位才能退出 | 不能自动恢复 |
| ✅ 边沿检测 FB 无条件每周期调用 | 不放在 CASE 分支内 |
| ✅ 枚举有 iInvalid := 0 | 上电默认值有意义 |
