# 标准 FB 模板


> 所有 FB 设计必须以此为基础，不得随意删减接口

---

## 1. 标准 bExecute/bDone/bBusy/bError 接口模板

本技能自定义 FB 接口必须使用匈牙利命名。PLCopen 库 FB 的固定引脚名可以在调用第三方库时保留，但不得作为本项目自定义 POU 的变量声明名。

```st
/// 功能    : 标准执行型功能块模板
/// 库依赖  : Standard

{attribute 'hide_all_locals'}
FUNCTION_BLOCK FB_TemplateAction
VAR_INPUT
    bExecute        : BOOL := FALSE;    // 上升沿触发，保持 TRUE 直到完成
    // 在此添加业务输入参数
    // rTargetValue : REAL := 0.0;      // 目标值 [mm]
END_VAR
VAR_OUTPUT
    bDone           : BOOL;             // 执行成功完成，保持一个周期
    bBusy           : BOOL;             // 正在执行中
    bError          : BOOL;             // 发生错误
    diErrorID       : DINT;             // 错误代码，0=无错误
    // 在此添加业务输出参数
END_VAR
VAR
    rtrigExecute    : R_TRIG;           // 检测 bExecute 上升沿
    iInternalState  : INT := 0;         // 内部状态：0=Idle, 1=Running, 2=Done, 3=Error
END_VAR

// === IMPLEMENTATION ===

/// =======================================================================
/// 名称      : FB_TemplateAction
/// 功能      : 标准 bExecute/bDone/bBusy/bError 执行型功能块模板
/// 库依赖    : Standard
/// =======================================================================

/// 边沿检测（每周期无条件调用）
rtrigExecute(
    CLK := bExecute
    );

/// =======================================================================
/// 主状态机
/// =======================================================================
CASE iInternalState OF

    0: // Idle
        bDone     := FALSE;
        bBusy     := FALSE;
        bError    := FALSE;
        diErrorID := 0;
        IF rtrigExecute.Q THEN
            iInternalState := 1;
        END_IF;

    1: // Running
        bBusy := TRUE;
        bDone := FALSE;

        /// 在此实现业务逻辑
        // IF <完成条件> THEN
        //     iInternalState := 2;
        // ELSIF <错误条件> THEN
        //     diErrorID := 16#0001;
        //     iInternalState := 3;
        // END_IF

        // 如果 bExecute 被撤销，中止执行
        IF NOT bExecute THEN
            iInternalState := 0;
        END_IF;

    2: // Done
        bBusy  := FALSE;
        bDone  := TRUE;
        bError := FALSE;
        IF NOT bExecute THEN            // bExecute 撤销后回到 Idle
            bDone          := FALSE;
            iInternalState := 0;
        END_IF;

    3: // Error
        bBusy  := FALSE;
        bDone  := FALSE;
        bError := TRUE;
        IF NOT bExecute THEN            // bExecute 撤销后清除错误，回到 Idle
            bError         := FALSE;
            diErrorID      := 0;
            iInternalState := 0;
        END_IF;

ELSE
    // 非法状态：安全复位
    iInternalState := 0;
    bError    := TRUE;
    diErrorID := 16#FFFF;

END_CASE;
```

### 调用方式

```st
VAR
    fbAction    : FB_TemplateAction;
    bStart      : BOOL;
    bDone       : BOOL;
    bError      : BOOL;
    diErrorCode : DINT;
END_VAR

fbAction(
    bExecute := bStart
    // , rTargetValue := 100.0
    );

bDone       := fbAction.bDone;
bError      := fbAction.bError;
diErrorCode := fbAction.diErrorID;

IF fbAction.bDone THEN
    bStart := FALSE;                    // 撤销 bExecute，FB 回到 Idle
ELSIF fbAction.bError THEN
    bStart := FALSE;
    // 处理错误
END_IF;
```

---

## 2. bEnable/bValid 接口模板（持续使能型）

适用于需要持续运行的 FB（如通信、监控、PID）。

```st
/// 功能    : 持续使能型功能块模板
/// 库依赖  : Standard

{attribute 'hide_all_locals'}
FUNCTION_BLOCK FB_TemplateContinuous
VAR_INPUT
    bEnable         : BOOL := FALSE;    // 电平使能，TRUE=运行，FALSE=停止
END_VAR
VAR_OUTPUT
    bValid          : BOOL;             // 输出有效（bEnable=TRUE 且无错误）
    bBusy           : BOOL;             // 正在初始化/建立连接
    bError          : BOOL;             // 发生错误
    diErrorID       : DINT;             // 错误代码
END_VAR
VAR
    rtrigEnable     : R_TRIG;           // 检测 bEnable 上升沿（初始化用）
    ftrigEnable     : F_TRIG;           // 检测 bEnable 下降沿（清理用）
END_VAR

// === IMPLEMENTATION ===

/// =======================================================================
/// 名称      : FB_TemplateContinuous
/// 功能      : 标准 bEnable/bValid 持续使能型功能块模板
/// 库依赖    : Standard
/// =======================================================================

rtrigEnable(
    CLK := bEnable
    );
ftrigEnable(
    CLK := bEnable
    );

IF rtrigEnable.Q THEN
    // 初始化动作
    bBusy  := TRUE;
    bValid := FALSE;
    bError := FALSE;
END_IF;

IF ftrigEnable.Q THEN
    // 清理动作
    bValid := FALSE;
    bBusy  := FALSE;
END_IF;

IF bEnable THEN
    // 持续运行逻辑
    // IF <就绪条件> THEN bValid := TRUE; bBusy := FALSE; END_IF
    // IF <错误条件> THEN bError := TRUE; diErrorID := ...; END_IF
ELSE
    bValid := FALSE;
END_IF;
```

---

## 3. FB 设计原则速查

| 原则 | 规则 |
|---|---|
| 单一职责 | 一个 FB 只做一件事，不混合控制/诊断/HMI |
| 接口稳定 | VAR_INPUT/OUTPUT 确定后不随意修改 |
| 防御性编程 | 处理所有边界值和异常输入 |
| 大结构体传递 | 用 VAR_IN_OUT，避免复制开销 |
| 初始值 | 所有 VAR_INPUT 必须有合理默认值 |
| 注释 | 每个参数注明用途和单位 |
| 错误输出 | 所有 FB 必须有 `bError/xError` + `diErrorID/udiErrorID` 输出 |
