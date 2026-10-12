/// 功能    : 电机参数结构体
/// 库依赖  : Standard

TYPE ST_MotorData :
STRUCT
    sModel          : STRING(32);       // 型号
    iRatedPower     : INT;              // 额定功率 [W]
    iRatedSpeed     : INT;              // 额定转速 [rpm]
    rRatedTorque    : REAL;             // 额定扭矩 [N.m]
    rRatedCurrent   : REAL;             // 额定电流 [A]
    bBrakeEnabled   : BOOL;             // 是否带抱闸
END_STRUCT
END_TYPE
