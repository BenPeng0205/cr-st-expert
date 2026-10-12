/// 功能    : 系统级全局变量
/// 库依赖  : Standard

{attribute 'qualified_only'}
VAR_GLOBAL
    bSystemReady        : BOOL;         // 系统就绪
    bSystemFault        : BOOL;         // 系统故障
    eSystemState        : E_SystemState;// 系统状态
    iLineSpeedSetpoint  : INT := 1500;  // 产线目标速度 [rpm]
    iLineSpeedFeedback  : INT;          // 产线反馈速度 [rpm]
END_VAR
