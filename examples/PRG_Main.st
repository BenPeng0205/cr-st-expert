/// 功能    : 主程序样本
/// 库依赖  : Standard

PROGRAM PRG_Main
VAR
    fbMotorController   : FB_MotorController; // 电机控制功能块实例
    bStartCommand       : BOOL := TRUE;       // 启动命令
    bResetCommand       : BOOL;               // 复位命令
END_VAR

// === IMPLEMENTATION ===

/// =======================================================================
/// 名称      : PRG_Main
/// 功能      : 演示 PRG 调用 FB 与 GVL 的基础写法
/// 库依赖    : Standard
/// =======================================================================
/// 使用说明  : 1. PRG 仍然是单文件对象
///           : 2. 运行逻辑放在实现区
///           : 3. 全局量通过 GVL_System 命名空间访问
/// =======================================================================
// 主程序先置位系统级运行状态，再调用下层 FB，保证 FB 获取到稳定的系统使能。
GVL_System.bSystemReady := TRUE;
GVL_System.eSystemState := E_SystemState.iRunning;

// FB 调用使用命名引脚多行格式，便于核对接口与人工审查。
fbMotorController(
    bEnable         := GVL_System.bSystemReady,
    bRun            := bStartCommand,
    bReset          := bResetCommand,
    iRequestedSpeed := GVL_System.iLineSpeedSetpoint
    );

// 调用完成后再回写反馈和故障状态，避免上层读取到上周期的中间值。
GVL_System.iLineSpeedFeedback := fbMotorController.iActualSpeed;
GVL_System.bSystemFault := fbMotorController.bFault;
