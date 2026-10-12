/// 功能    : 伺服电机控制功能块
/// 库依赖  : Standard

{attribute 'hide_all_locals'}
FUNCTION_BLOCK FB_MotorController
VAR_INPUT
    bEnable         : BOOL := FALSE; // 系统允许电机控制逻辑运行
    bRun            : BOOL := FALSE; // 外部启动或保持运行的命令
    bReset          : BOOL := FALSE; // 故障复位命令，高电平时清除故障状态
    iRequestedSpeed : INT  := 0;     // 外部请求的目标速度[rpm]
END_VAR

VAR_OUTPUT
    bRunning     : BOOL; // 电机已进入运行状态
    bFault       : BOOL; // 控制逻辑已进入故障状态
    bError       : BOOL; // 标准错误标志，供上层统一诊断
    diErrorID    : DINT; // 标准错误代码，0 表示无故障
    iActualSpeed : INT;  // 当前模拟反馈速度[rpm]
END_VAR

VAR
    eState          : E_MotorState; // 内部运行状态机
    iTargetSpeed    : INT;          // 限幅后的目标速度[rpm]
    tonStartTimeout : TON;          // 启动过程超时保护定时器
END_VAR

// === IMPLEMENTATION ===

/// =======================================================================
/// 名称      : FB_MotorController
/// 功能      : 示例功能块，展示 CODESYS ST text 聚合格式下的 FB 主体与子对象段落。
/// 库依赖    : Standard
/// 使用说明  : 1. Method、Action、Property 作为父 FB 内部段落交付，由 CODESYS ST text 解析并回写。
///           : 2. 调用方必须先给出使能、运行和复位命令，速度请求由内部限幅函数统一约束。
/// =======================================================================
// 未使能时强制回到空闲态，并稳定调用定时器，避免上次启动过程留下内部状态。
IF NOT bEnable THEN
    eState := E_MotorState.iIdle;
    bRunning     := FALSE;
    bFault       := FALSE;
    bError       := FALSE;
    diErrorID    := 0;
    iActualSpeed := 0;
    tonStartTimeout(
        IN := FALSE,
        PT := T#5s
        );
    RETURN;
END_IF;

// 复位命令优先于状态机运行，确保故障恢复时不会继续沿用旧故障状态。
IF bReset THEN
    A_ResetFault();
END_IF;

// 目标速度先统一限幅，再进入状态机，防止后续分支重复处理速度边界。
iTargetSpeed := F_LimitSpeed(
    iValue := iRequestedSpeed,
    iMin   := 0,
    iMax   := 3000
    );

CASE eState OF
    E_MotorState.iIdle:
        // 空闲态关闭启动超时定时器，只在收到运行命令后切换到启动流程。
        bRunning := FALSE;
        tonStartTimeout(
            IN := FALSE,
            PT := T#5s
            );
        IF bRun THEN
            eState := E_MotorState.iStarting;
        END_IF;

    E_MotorState.iStarting:
        // 启动态持续喂入定时器，用于识别电机迟迟无法达到目标速度的异常。
        tonStartTimeout(
            IN := TRUE,
            PT := T#5s
            );
        iActualSpeed := iActualSpeed + 100;
        IF iActualSpeed >= iTargetSpeed THEN
            iActualSpeed := iTargetSpeed;
            bRunning := TRUE;
            eState := E_MotorState.iRunning;
        ELSIF tonStartTimeout.Q THEN
            bFault    := TRUE;
            bError    := TRUE;
            diErrorID := 16#1001;
            bRunning  := FALSE;
            eState := E_MotorState.iFault;
        END_IF;

    E_MotorState.iRunning:
        // 运行态将模拟反馈同步到目标速度；取消运行命令后进入受控停机。
        bRunning := TRUE;
        tonStartTimeout(
            IN := FALSE,
            PT := T#5s
            );
        iActualSpeed := iTargetSpeed;
        IF NOT bRun THEN
            eState := E_MotorState.iStopping;
        END_IF;

    E_MotorState.iStopping:
        // 停机态按固定斜率降低模拟速度，到 0 后回到空闲态。
        bRunning := FALSE;
        iActualSpeed := iActualSpeed - 200;
        IF iActualSpeed <= 0 THEN
            iActualSpeed := 0;
            eState := E_MotorState.iIdle;
        END_IF;

    E_MotorState.iFault:
        // 故障态保持输出停止，等待上层复位命令显式清除故障。
        bRunning := FALSE;
        iActualSpeed := 0;

    ELSE
        // 未知状态视为状态机损坏，统一进入故障态并关闭运行输出。
        bFault       := TRUE;
        bError       := TRUE;
        diErrorID    := 16#10FF;
        bRunning     := FALSE;
        iActualSpeed := 0;
        eState := E_MotorState.iFault;
END_CASE;

// === METHOD M_Init ===
METHOD PUBLIC M_Init : BOOL
VAR_INPUT
END_VAR
// === IMPLEMENTATION ===
// 初始化复用空闲态默认值，保证上电或手动调用后状态机从确定状态开始。
// 标准诊断输出同步清零，避免外部 HMI 或上层 PRG 读到过期故障上下文。
eState       := E_MotorState.iIdle;
bRunning     := FALSE;
bFault       := FALSE;
bError       := FALSE;
diErrorID    := 0;
iActualSpeed := 0;
iTargetSpeed := 0;
M_Init := TRUE;

// === METHOD M_ValidateSpeed ===
METHOD PUBLIC M_ValidateSpeed : BOOL
VAR_INPUT
    iCandidateSpeed : INT := 0; // 待校验的候选速度[rpm]
END_VAR
// === IMPLEMENTATION ===
// 速度校验只判断工程允许范围，不在方法内部修改任何运行状态。
M_ValidateSpeed := (iCandidateSpeed >= 0) AND (iCandidateSpeed <= 3000);

// === ACTION A_ResetFault ===
// === IMPLEMENTATION ===
// 复位动作只清故障和运行输出，同时关闭启动定时器，避免恢复后立即超时。
// 这里不直接恢复运行命令，防止外部命令仍保持 TRUE 时复位后立即重新启动。
bFault       := FALSE;
bError       := FALSE;
diErrorID    := 0;
bRunning     := FALSE;
eState       := E_MotorState.iIdle;
iActualSpeed := 0;
tonStartTimeout(
    IN := FALSE,
    PT := T#5s
    );

// === PROPERTY P_TargetSpeed ===
PROPERTY PUBLIC P_TargetSpeed : INT
// === GET ===
P_TargetSpeed := iTargetSpeed;
// === SET ===
IF M_ValidateSpeed(
    iCandidateSpeed := P_TargetSpeed
    ) THEN
    iTargetSpeed := P_TargetSpeed;
END_IF;
