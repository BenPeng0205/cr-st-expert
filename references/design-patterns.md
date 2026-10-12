# 设计模式参考

## 1. 状态机

适用于电机、气缸、工艺步骤等离散控制场景。

```iecst
CASE eState OF
    E_MotorState.iIdle:
        IF bRun THEN
            eState := E_MotorState.iStarting;
        END_IF;

    E_MotorState.iRunning:
        IF NOT bRun THEN
            eState := E_MotorState.iStopping;
        END_IF;
END_CASE;
```

## 2. 限幅函数

当输入来自 HMI、上位机或配方时，先限幅再写入内部状态。

## 3. 分层对象

- `GVL`：系统共享状态
- `ENUM / STRUCT`：数据建模
- `FUNCTION`：纯计算
- `FUNCTION_BLOCK`：控制逻辑
- `PROGRAM`：调度与调用
