/// 功能    : 系统状态枚举
/// 库依赖  : Standard

{attribute 'qualified_only'}
{attribute 'strict'}
TYPE E_SystemState :
(
    iInit       := 0,                   // 初始化
    iReady      := 10,                  // 就绪
    iRunning    := 20,                  // 运行中
    iStopping   := 30,                  // 停止中
    iFault      := 90                   // 故障
);
END_TYPE
