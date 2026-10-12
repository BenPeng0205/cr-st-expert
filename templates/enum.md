# ENUM 模板

> 用途: 生成 `ENUM`

```iecst
/// 功能    : <功能描述>
/// 库依赖  : 暂无

{attribute 'qualified_only'}
{attribute 'strict'}
TYPE E_<名称> :
(
    iIdle       := 0,
    iRunning    := 10,
    iFault      := 90
);
END_TYPE
```
