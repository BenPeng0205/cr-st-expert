# 执行语义规则


> 适用场景：边沿检测、定时器、计数器、SC 机制、状态机执行语义

---

## 1. 边沿检测（R_TRIG / F_TRIG）

### 核心规则

| 规则 | 说明 |
|---|---|
| **每周期无条件调用** | FB 必须在每个扫描周期被调用，不能放在条件分支内 |
| **实例在 VAR 区** | 不能在 VAR_TEMP 中声明，否则状态每次清零 |
| **一个信号一个实例** | 不能复用同一个 R_TRIG 实例检测不同信号 |
| **Q 只在上升沿为 TRUE** | Q 只在检测到上升沿的那一个周期为 TRUE，下一周期自动清零 |

### 正确用法

```st
VAR
    rtrigStart  : R_TRIG;   // 启动按钮上升沿
    ftrigStop   : F_TRIG;   // 停止按钮下降沿
END_VAR

// 每周期无条件调用
rtrigStart(
    CLK := bStartButton
    );
ftrigStop(
    CLK := bStopButton
    );

// 在调用之后使用 Q
IF rtrigStart.Q THEN
    // 启动按钮刚按下
END_IF;
IF ftrigStop.Q THEN
    // 停止按钮刚松开
END_IF;
```

---

## 2. 定时器（TON / TOF / TP）

### TON（接通延时）

```st
VAR
    tonDelay    : TON;
    bStart      : BOOL;
END_VAR

tonDelay(
    IN := bStart,
    PT := T#5S
    );

IF tonDelay.Q THEN
    // 5秒后触发
    bStart := FALSE;  // 必须重置 IN，否则 Q 持续为 TRUE
END_IF;
```

**关键陷阱**：
- `IN` 变为 FALSE 时，`ET` 立即清零，`Q` 立即变 FALSE
- 触发后如果不重置 `IN`，`Q` 会一直保持 TRUE

### TOF（断开延时）

```st
tonDelay(
    IN := bCondition,
    PT := T#3S
    );
// IN 变 FALSE 后，Q 再保持 TRUE 3秒
// IN 变 TRUE 时，Q 立即变 TRUE，ET 清零
```

### TP（脉冲定时器）

```st
tpPulse(
    IN := bTrigger,
    PT := T#100MS
    );
// IN 上升沿触发，Q 保持 TRUE 100ms，期间 IN 变化不影响
// 脉冲期间再次触发 IN 无效，必须等脉冲结束
```

### 定时器组合：自振荡时钟

```st
VAR
    tonClock    : TON;
    bTick       : BOOL;
END_VAR

tonClock(
    IN := NOT tonClock.Q,
    PT := T#500MS
    );
bTick := tonClock.Q;  // 每 500ms 产生一个周期的 TRUE 脉冲
```

---

## 3. 计数器（CTU / CTD / CTUD）

```st
VAR
    ctuCounter  : CTU;
    rtrigEdge   : R_TRIG;
END_VAR

rtrigEdge(
    CLK := bPulseSignal
    );                             // 边沿检测，每周期调用
ctuCounter(
    CU := rtrigEdge.Q,             // 用边沿脉冲驱动计数，不用电平
    R  := bReset,
    PV := 100
    );

IF ctuCounter.Q THEN
    // 计数到 100
END_IF;
```

**关键陷阱**：`CU` 输入应该是脉冲（来自 R_TRIG.Q），不能是电平信号，否则每个周期都计数。

---

## 4. SC（State Complete）机制

SC 是 PackML Acting state 完成后发出的**上升沿脉冲**，不是电平信号。

### 正确实现

```st
VAR
    bStateComplete  : BOOL := FALSE;    // SC 信号
    rtrigSC         : R_TRIG;           // 检测 SC 上升沿
END_VAR

// 在 Acting state 内部，完成条件满足时置位
E_PackMLState.Resetting:
    // 执行复位动作...
    IF bResetDone THEN
        bStateComplete := TRUE;         // 置位 SC
    END_IF;

// 状态机主循环检测 SC
rtrigSC(
    CLK := bStateComplete
    );
IF rtrigSC.Q THEN
    bStateComplete := FALSE;            // 立即清零，保持脉冲特性
    // 转换到下一个 Wait state
    eState := E_PackMLState.Idle;
END_IF;
```

**关键约束**：
- SC 置位后必须在同一周期或下一周期清零
- 不能用电平型 SC（一直保持 TRUE），会导致状态机抖动
- SC 只对 Acting state 有效，Wait state 收到 SC 忽略

---

## 5. 状态机执行语义

### Acting State vs Wait State

| 类型 | 退出方式 | 典型状态 |
|---|---|---|
| Wait State | 收到有效命令 | Stopped, Idle, Held, Suspended, Aborted, Completed |
| Acting State | SC 脉冲 | Starting, Stopping, Aborting, Resetting, Holding... |
| Dual State | Hold/Suspend/Complete/Stop/Abort 命令 | Execute |

### 进入/退出动作模式

```st
// 使用 bFirstScan 标志实现进入动作
VAR
    bFirstScan  : BOOL := TRUE;
END_VAR

E_State.Running:
    IF bFirstScan THEN
        bFirstScan := FALSE;
        // 进入动作：初始化、保存设定值
        rSavedSpeed := rTargetSpeed;
    END_IF;
    // 持续动作
    ...

// 状态转换时重置 bFirstScan
IF eState <> ePrevState THEN
    bFirstScan := TRUE;
    ePrevState := eState;
END_IF;
```

---

## 6. 命令优先级（PackML）

```
Abort > Stop > Complete > Suspend > Hold > UnSuspend > UnHold > Start > Reset
```

实现时，高优先级命令必须能打断低优先级命令的执行：

```st
// Abort 可以打断任何状态，包括 Stopping
IF bAbortCmd THEN
    eState := E_PackMLState.Aborting;   // 无条件跳转
ELSIF bStopCmd AND eState <> E_PackMLState.Aborting THEN
    eState := E_PackMLState.Stopping;
END_IF;
```
