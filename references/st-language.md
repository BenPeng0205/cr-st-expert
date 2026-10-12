# ST 语言参考

> 适用平台：CODESYS / CODESYS

## 1. 变量声明

```iecst
VAR
    bEnable      : BOOL;
    iTargetSpeed : INT;
    rRatedTorque : REAL;
    sModel       : STRING(32);
    tStartDelay  : TIME;
END_VAR
```

## 2. 控制结构

```iecst
IF bEnable THEN
    iTargetSpeed := 1500;
END_IF;

CASE eState OF
    E_MotorState.iIdle:
        bRunning := FALSE;
    E_MotorState.iRunning:
        bRunning := TRUE;
    ELSE
        bRunning := FALSE;
END_CASE;
```

## 3. 属性与功能块

- `FUNCTION_BLOCK` 和 `FUNCTION` 必须带 `{attribute 'hide_all_locals'}`。
- `PROGRAM / PRG` 禁止带 `{attribute 'hide_all_locals'}`。
- `ENUM` 必须带 `{attribute 'qualified_only'}` 和 `{attribute 'strict'}`。
- `GVL` 必须带 `{attribute 'qualified_only'}`。

## 4. 当前技能特别说明

本技能重点是通用编程规范：

- 对象与变量命名、接口及类型边界
- 工程师级注释、缩进和对齐
- 状态型实例存储、调用周期及异常分支
- 内置模板另采用聚合文本约定；用户原生 IDE 工程不依赖该格式
