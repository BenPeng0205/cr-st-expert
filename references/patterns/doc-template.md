# 说明文档模板

> 适用场景：为 FB / FC / PRG / STRUCT 生成配套说明文档时使用。

---

## 文档结构

```
# [程序单元名称] 说明文档

类型 / 文件路径

## 概述
## 功能说明
## 技术规格
## 接口定义
## 使用示例
## 注意事项
```

---

## 完整模板

```markdown
# FB_MotorControl 说明文档

**类型**: FUNCTION_BLOCK
**文件路径**: POUs/FBs/FB_MotorControl.st

---

## 概述

### 功能简介

[一句话描述该程序单元的核心功能]

### 适用场景

- [场景1]
- [场景2]

### 核心特点

- [特点1]
- [特点2]

---

## 功能说明

[详细描述功能逻辑，包括状态机流程、关键算法、边界条件处理]

---

## 技术规格

| 参数         | 值              |
|------------|----------------|
| 扫描周期       | 10ms           |
| 库依赖        | Standard       |
| 内存占用（估算）   | ~200 bytes     |

---

## 接口定义

### 输入（VAR_INPUT）

| 变量名       | 类型   | 默认值     | 说明          |
|-----------|------|---------|-------------|
| bEnable   | BOOL | FALSE   | 使能信号        |
| rSetSpeed | REAL | 0.0     | 目标速度 [rpm] |

### 输出（VAR_OUTPUT）

| 变量名        | 类型   | 说明          |
|------------|------|-------------|
| bRunning   | BOOL | 运行中         |
| bError     | BOOL | 故障标志        |
| diErrorID  | DINT | 错误代码，0=无故障  |

---

## 使用示例

```st
VAR
    fbMotor : FB_MotorControl;
END_VAR

fbMotor(
    bEnable   := bMotorEnable,
    rSetSpeed := rTargetSpeed
    );

IF fbMotor.bError THEN
    diAlarmCode := fbMotor.diErrorID;
END_IF;
```

---

## 注意事项

1. [注意事项1]
2. [注意事项2]

```
