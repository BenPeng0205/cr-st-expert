# GVL 模板

> 用途: 生成 `GVL`

```iecst
/// 功能    : <功能描述>
/// 库依赖  : 暂无

{attribute 'qualified_only'}
VAR_GLOBAL
    bSystemReady        : BOOL;         // 系统就绪
    iLineSpeedSetpoint  : INT := 1500;  // 产线目标速度 [rpm]
END_VAR
```
