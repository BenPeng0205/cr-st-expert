# STRUCT 模板

> 用途: 生成 `STRUCT`

```iecst
/// 功能    : <功能描述>
/// 库依赖  : 暂无

TYPE ST_<名称> :
STRUCT
    sModel          : STRING(32);       // 型号
    iRatedPower     : INT;              // 额定功率 [W]
    rRatedTorque    : REAL;             // 额定扭矩 [N.m]
    bBrakeEnabled   : BOOL;             // 抱闸配置
END_STRUCT
END_TYPE
```
