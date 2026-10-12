# 多任务安全规则


> 适用场景：多任务共享变量、竞争条件、优先级反转

---

## 1. 核心原则

**跨任务共享变量必须有同步保护。** 没有保护的共享变量在多任务环境中会产生竞争条件，导致数据撕裂（读到一半更新的值）。

---

## 2. 竞争条件识别

以下情况存在竞争风险：

```st
// 危险：高优先级任务和低优先级任务都访问同一变量
// Task1（高优先级）：写入
GVL.rSharedValue := rNewValue;

// Task2（低优先级）：读取
rLocalCopy := GVL.rSharedValue;
// 如果 Task1 在 Task2 读取中途抢占，rLocalCopy 可能读到中间值
```

**DINT/REAL（32位）在大多数 CoDeSys 平台上是原子操作，但 LREAL（64位）和结构体不是。**

---

## 3. 双缓冲模式（推荐）

适用于：高频写入 + 低频读取，或生产者-消费者模式。

```st
// 全局变量
VAR_GLOBAL
    aDataBuffer     : ARRAY[0..1] OF ST_ProcessData;  // 双缓冲
    iWriteIndex     : INT := 0;                        // 当前写缓冲索引
    iReadIndex      : INT := 1;                        // 当前读缓冲索引
    bNewDataReady   : BOOL := FALSE;                   // 新数据就绪标志
END_VAR

// 写任务（高优先级）：写入非活跃缓冲
aDataBuffer[iWriteIndex] := stNewData;
// 原子交换索引
iReadIndex  := iWriteIndex;
iWriteIndex := 1 - iWriteIndex;
bNewDataReady := TRUE;

// 读任务（低优先级）：读取活跃缓冲
IF bNewDataReady THEN
    bNewDataReady := FALSE;
    stLocalData := aDataBuffer[iReadIndex];
END_IF;
```

---

## 4. 标志位握手模式

适用于：简单的单次数据传递。

```st
VAR_GLOBAL
    rSharedValue    : REAL := 0.0;
    bDataValid      : BOOL := FALSE;    // 写方置位，读方清零
    bDataConsumed   : BOOL := FALSE;    // 读方置位，写方清零
END_VAR

// 写任务
IF bDataConsumed OR NOT bDataValid THEN
    rSharedValue  := rNewValue;
    bDataConsumed := FALSE;
    bDataValid    := TRUE;
END_IF;

// 读任务
IF bDataValid THEN
    rLocalValue   := rSharedValue;
    bDataValid    := FALSE;
    bDataConsumed := TRUE;
END_IF;
```

---

## 5. RETAIN 变量规则

```st
// RETAIN：掉电保持，重新上电后恢复
VAR RETAIN
    diProductionCount   : DINT := 0;    // 生产计数，掉电不丢失
    iCurrentRecipeID    : INT  := 0;    // 当前配方号
END_VAR

// 注意事项：
// 1. RETAIN 变量写入有额外开销，不要在高频循环中频繁写入
// 2. 下载新程序时 RETAIN 变量保留，PERSISTENT 变量也保留
// 3. 冷启动（Cold Reset）会清除 RETAIN 变量
// 4. 不要把大型数组声明为 RETAIN，影响启动时间
```

---

## 6. 任务优先级设计原则

| 任务类型 | 推荐优先级 | 周期 | 典型内容 |
|---|---|---|---|
| 安全任务 | 最高 | 1ms | 急停、安全门、安全 PLC |
| 运动控制 | 高 | 1-4ms | MC_* FB 调用、轴插补 |
| 过程控制 | 中 | 4-10ms | PID、PackML 状态机 |
| 通信任务 | 低 | 10-50ms | TCP/Modbus/OPC UA |
| HMI 更新 | 最低 | 50-100ms | 数据映射到 HMI 变量 |

**规则**：
- 高优先级任务不能调用耗时操作（文件 IO、大量字符串处理）
- 低优先级任务不能直接写高优先级任务的控制变量
- 跨优先级的数据交换必须使用同步机制

---

## 7. 禁止在高优先级任务中的操作

```st
// ❌ 禁止在运动控制任务（1ms）中执行
sLog := CONCAT(sLog, DINT_TO_STRING(diCount));  // 字符串操作耗时
fbFileWrite(
    Execute := TRUE,
    ...
    );                                          // 文件 IO 不确定延时
fbTcpSend(
    Execute := TRUE,
    ...
    );                                          // 网络操作不确定延时

// ✅ 正确：在低优先级任务中执行，通过标志位触发
// 高优先级任务：只设置标志
bLogRequired := TRUE;
stLogData := stCurrentData;

// 低优先级任务：执行实际操作
IF bLogRequired THEN
    bLogRequired := FALSE;
    // 执行文件写入
END_IF;
```

---

## 8. 优先级反转防护

```st
// 场景：低优先级任务持有资源，高优先级任务等待
// CoDeSys 没有内置互斥锁，使用标志位模拟

VAR_GLOBAL
    bResourceLocked : BOOL := FALSE;
END_VAR

// 访问共享资源前检查锁
IF NOT bResourceLocked THEN
    bResourceLocked := TRUE;
    // 访问共享资源
    bResourceLocked := FALSE;
END_IF;
// 注意：这不是真正的原子操作，仅适用于同优先级任务
// 跨优先级的真正保护需要使用双缓冲或标志位握手
```
