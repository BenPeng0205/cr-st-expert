# 定时器组合模式


> 适用场景：TON/TOF/TP 的典型组合用法

---

## 1. 定时器基础速查

| FB | 触发方式 | Q 输出 | 典型用途 |
|---|---|---|---|
| `TON` | IN 上升沿开始计时 | IN=TRUE 且 ET≥PT 时为 TRUE | 延时接通、超时检测 |
| `TOF` | IN 下降沿开始计时 | IN=TRUE 或 ET<PT 时为 TRUE | 延时断开、冷却时间 |
| `TP` | IN 上升沿触发单次 | 脉冲宽度固定为 PT | 固定宽度脉冲 |

**关键规则**：定时器 FB 必须每周期无条件调用，不能放在 IF 分支内。

---

## 2. 模式一：超时检测

```st
// 场景：操作必须在规定时间内完成，否则报错
VAR
    tonTimeout  : TON;
    bOperating  : BOOL;
    bTimeout    : BOOL;
END_VAR

// 无条件调用
tonTimeout(
    IN := bOperating,       // 操作进行中时计时
    PT := T#10S             // 10秒超时
    );

IF tonTimeout.Q THEN
    bTimeout   := TRUE;
    bOperating := FALSE;    // 停止操作
END_IF;
```

---

## 3. 模式二：振荡器（周期脉冲）

```st
// 场景：生成固定频率的脉冲信号，用于心跳、闪烁、轮询
VAR
    tonOnTimer  : TON;
    tonOffTimer : TON;
    bPulse      : BOOL := FALSE;    // 振荡输出
    tOnTime     : TIME := T#500MS;  // 高电平持续时间
    tOffTime    : TIME := T#500MS;  // 低电平持续时间
END_VAR

// 无条件调用两个定时器
tonOnTimer(
    IN := NOT bPulse,
    PT := tOffTime
    );
tonOffTimer(
    IN := bPulse,
    PT := tOnTime
    );

// 振荡逻辑
IF tonOnTimer.Q THEN
    bPulse := TRUE;
END_IF;
IF tonOffTimer.Q THEN
    bPulse := FALSE;
END_IF;
```

---

## 4. 模式三：去抖动（输入滤波）

```st
// 场景：消除传感器抖动，信号稳定保持 tDebounce 后才认为有效
VAR
    tonDebounce : TON;
    bRawInput   : BOOL;     // 原始输入（可能抖动）
    bStableInput: BOOL;     // 去抖后的稳定信号
    tDebounce   : TIME := T#20MS;
END_VAR

tonDebounce(
    IN := bRawInput,
    PT := tDebounce
    );
bStableInput := tonDebounce.Q;

// 说明：bRawInput 必须连续保持 TRUE 达 20ms，bStableInput 才变 TRUE
// bRawInput 一旦变 FALSE，bStableInput 立即变 FALSE（无延迟）
```

---

## 5. 模式四：延时断开（冷却时间）

```st
// 场景：设备停止命令发出后，风扇/冷却水继续运行一段时间
VAR
    tofCooldown : TOF;
    bMotorRun   : BOOL;     // 电机运行命令
    bFanRun     : BOOL;     // 风扇运行（含冷却时间）
    tCooldown   : TIME := T#30S;
END_VAR

tofCooldown(
    IN := bMotorRun,
    PT := tCooldown
    );
bFanRun := tofCooldown.Q;

// 说明：bMotorRun=TRUE 时 bFanRun=TRUE
// bMotorRun 变 FALSE 后，bFanRun 继续保持 TRUE 达 30s
```

---

## 6. 模式五：超时重试

```st
// 场景：操作失败后等待一段时间再重试，最多重试 N 次
VAR
    tonRetryTimer   : TON;
    iRetryCount     : INT := 0;
    iMaxRetry       : INT := 3;
    bOperationFailed: BOOL;
    bRetrying       : BOOL;
    bGiveUp         : BOOL;
    tRetryInterval  : TIME := T#5S;
END_VAR

tonRetryTimer(
    IN := bOperationFailed AND NOT bGiveUp,
    PT := tRetryInterval
    );

IF tonRetryTimer.Q THEN
    IF iRetryCount < iMaxRetry THEN
        iRetryCount      := iRetryCount + 1;
        bRetrying        := TRUE;
        bOperationFailed := FALSE;  // 清除失败标志，触发重试
    ELSE
        bGiveUp := TRUE;            // 超过最大重试次数
    END_IF;
END_IF;
```

---

## 7. 模式六：单次脉冲（TP）

```st
// 场景：触发一个固定宽度的输出脉冲，不受输入持续时间影响
VAR
    tpPulse     : TP;
    rtrigInput  : R_TRIG;
    bTrigInput  : BOOL;
    bPulseOut   : BOOL;
    tPulseWidth : TIME := T#100MS;
END_VAR

rtrigInput(
    CLK := bTrigInput
    );
tpPulse(
    IN := rtrigInput.Q,
    PT := tPulseWidth
    );
bPulseOut := tpPulse.Q;

// 说明：每次 bTrigInput 上升沿，bPulseOut 输出 100ms 脉冲
// 脉冲期间再次触发无效（TP 不可重触发）
```

---

## 8. 常见错误

```st
// ❌ 错误：定时器放在条件分支内，IN=FALSE 时不调用，ET 不会复位
IF bCondition THEN
    tonTimer(
        IN := TRUE,
        PT := T#5S
        );
END_IF;
// 结果：bCondition=FALSE 时 tonTimer 停止调用，ET 冻结在最后值

// ✅ 正确：无条件调用，用 IN 参数控制启停
tonTimer(
    IN := bCondition,
    PT := T#5S
    );
```

```st
// ❌ 错误：用 VAR_TEMP 声明定时器（每周期重置，永远不会超时）
VAR_TEMP
    tonTimer : TON;  // 状态每周期丢失！
END_VAR

// ✅ 正确：定时器必须在 VAR 区声明
VAR
    tonTimer : TON;
END_VAR
```
