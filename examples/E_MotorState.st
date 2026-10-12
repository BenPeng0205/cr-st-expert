/// 功能    : 电机状态枚举
/// 库依赖  : Standard

{attribute 'qualified_only'}
{attribute 'strict'}
TYPE E_MotorState :
(
    iIdle       := 0,                   // 空闲
    iStarting   := 10,                  // 启动中
    iRunning    := 20,                  // 运行中
    iStopping   := 30,                  // 停止中
    iFault      := 90                   // 故障
);
END_TYPE
