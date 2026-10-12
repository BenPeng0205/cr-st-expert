# 通用状态机参考实现

> 适用场景：任何需要状态机的 FB 或 PRG，包含完整的进入动作、超时保护、命令优先级机制。
> 这是一个可直接作为起点的标准实现骨架。

---

## 1. 枚举定义

```st
/// 功能    : 机器状态枚举
/// 库依赖  : 暂无

{attribute 'qualified_only'}
{attribute 'strict'}
TYPE E_MachineState :
(
    iInvalid    := 0,   // 非法状态，上电默认值，用于 ELSE 检测
    iIdle       := 1,   // 空闲，等待启动
    iStarting   := 2,   // 启动中（Acting）
    iRunning    := 3,   // 运行中
    iStopping   := 4,   // 停止中（Acting）
    iStopped    := 5,   // 已停止
    iError      := 99   // 错误
) INT;
END_TYPE
```

> 根据实际需求增减状态。`iInvalid := 0` 是关键——上电后变量默认为 0，CASE 的 ELSE 分支可以捕获这个值并安全处理。

---

## 2. 变量声明

```st
/// 功能    : 机器主状态机程序
/// 库依赖  : Standard

PROGRAM PRG_Machine
VAR
    // ── 状态机核心 ──
    eState          : E_MachineState := E_MachineState.iIdle;
    ePrevState      : E_MachineState := E_MachineState.iIdle;
    bFirstScan      : BOOL := TRUE;     // 进入新状态后第一个扫描周期标志

    // ── 命令接口 ──
    bStartCmd       : BOOL := FALSE;    // 启动命令
    bStopCmd        : BOOL := FALSE;    // 停止命令
    bAbortCmd       : BOOL := FALSE;    // 中止命令（最高优先级）
    bResetCmd       : BOOL := FALSE;    // 复位命令

    // ── 边沿检测（必须无条件调用）──
    rtrigStart      : R_TRIG;
    rtrigStop       : R_TRIG;
    rtrigAbort      : R_TRIG;
    rtrigReset      : R_TRIG;

    // ── 超时保护 ──
    tonActingTimeout : TON;
    tActingTimeout   : TIME := T#30S;   // Acting 状态最大允许时间

    // ── 状态输出 ──
    bRunning        : BOOL := FALSE;
    bError          : BOOL := FALSE;
    diErrorID       : DINT := 0;
END_VAR

// === IMPLEMENTATION ===

/// =======================================================================
/// 名称      : PRG_Machine
/// 功能      : 通用 PRG 状态机骨架，包含进入动作、超时保护和命令优先级
/// 库依赖    : Standard
/// =======================================================================
```

---

## 3. 主逻辑

```st
// ── Step 1：边沿检测（无条件，不能放在 IF/CASE 内）──
rtrigStart(
    CLK := bStartCmd
    );
rtrigStop(
    CLK := bStopCmd
    );
rtrigAbort(
    CLK := bAbortCmd
    );
rtrigReset(
    CLK := bResetCmd
    );

// ── Step 2：状态变化检测（重置 FirstScan 标志）──
IF eState <> ePrevState THEN
    bFirstScan := TRUE;
    ePrevState := eState;
    tonActingTimeout(
        IN := FALSE
        );                          // 重置超时计时器
END_IF;

// ── Step 3：Acting 状态超时保护 ──
tonActingTimeout(
    IN := (eState = E_MachineState.iStarting OR
           eState = E_MachineState.iStopping),
    PT := tActingTimeout
    );

// ── Step 4：命令优先级检查（在 CASE 之前）──
// 优先级：Abort > Stop > Start > Reset
IF rtrigAbort.Q THEN
    eState    := E_MachineState.iError;
    diErrorID := 16#0001;           // 外部中止
ELSIF rtrigStop.Q AND (eState <> E_MachineState.iError) THEN
    eState := E_MachineState.iStopping;
END_IF;

/// =======================================================================
/// 主状态机
/// =======================================================================
CASE eState OF

    E_MachineState.iIdle:
        IF bFirstScan THEN
            bFirstScan  := FALSE;
            bRunning    := FALSE;
        END_IF;
        IF rtrigStart.Q THEN
            eState := E_MachineState.iStarting;
        END_IF;

    E_MachineState.iStarting:
        IF bFirstScan THEN
            bFirstScan := FALSE;
            // TODO: 启动初始化逻辑
        END_IF;
        IF tonActingTimeout.Q THEN
            eState    := E_MachineState.iError;
            diErrorID := 16#0010;   // 启动超时
        END_IF;
        // TODO: 启动完成条件
        // IF <启动完成> THEN
        //     eState := E_MachineState.iRunning;
        // END_IF

    E_MachineState.iRunning:
        IF bFirstScan THEN
            bFirstScan := FALSE;
            bRunning   := TRUE;
        END_IF;
        // TODO: 持续运行逻辑

    E_MachineState.iStopping:
        IF bFirstScan THEN
            bFirstScan := FALSE;
            bRunning   := FALSE;
            // TODO: 停止初始化逻辑
        END_IF;
        IF tonActingTimeout.Q THEN
            eState    := E_MachineState.iError;
            diErrorID := 16#0020;   // 停止超时
        END_IF;
        // TODO: 停止完成条件
        // IF <停止完成> THEN
        //     eState := E_MachineState.iStopped;
        // END_IF

    E_MachineState.iStopped:
        IF bFirstScan THEN
            bFirstScan := FALSE;
        END_IF;
        IF rtrigReset.Q THEN
            bError    := FALSE;
            diErrorID := 0;
            eState    := E_MachineState.iIdle;
        END_IF;

    E_MachineState.iError:
        IF bFirstScan THEN
            bFirstScan := FALSE;
            bRunning   := FALSE;
            bError     := TRUE;
        END_IF;
        // 错误状态需要显式复位才能退出，不能自动恢复
        IF rtrigReset.Q THEN
            bError    := FALSE;
            diErrorID := 0;
            eState    := E_MachineState.iIdle;
        END_IF;

ELSE
    // 非法状态（iInvalid 或内存异常）：安全处理
    bError    := TRUE;
    diErrorID := 16#FFFF;
    eState    := E_MachineState.iError;

END_CASE;
```

---

## 4. 设计要点

**边沿检测位置**：所有 `R_TRIG` / `F_TRIG` 实例在程序顶部无条件调用，不放在任何 IF / CASE 分支内。

**命令优先级**：优先级检查块在 CASE 之前执行。Abort 最高优先级，可以从任意状态触发。

**bFirstScan 机制**：状态变化时置位，在新状态的第一个周期执行进入动作（初始化），之后清零。避免重复初始化。

**超时保护**：所有 Acting 状态（有持续动作、等待完成的状态）都应有超时保护，防止机器卡死在中间状态。

**ELSE 分支**：CASE 必须有 ELSE，捕获非法状态值并强制进入安全状态，防止静默失效。

**错误状态需显式复位**：错误状态不能自动恢复，必须等待操作员确认并发送复位命令。

---

## 5. 状态机设计检查清单

- [ ] 每个状态都有 `bFirstScan` 进入动作保护
- [ ] 命令优先级在 CASE 之前检查，Abort 最高优先级
- [ ] 每个 Acting 状态有超时保护
- [ ] CASE 有 ELSE 分支处理非法状态
- [ ] 错误状态需要显式复位才能退出
- [ ] 边沿检测 FB 无条件每周期调用，不放在 CASE 分支内
- [ ] 枚举有 `iInvalid := 0`，上电默认值有意义
- [ ] 枚举有 `{attribute 'qualified_only'}` + `{attribute 'strict'}`
