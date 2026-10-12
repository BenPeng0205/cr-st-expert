# 类型系统规则


> 适用场景：类型声明、类型转换、数组、字符串、指针

---

## 1. 基本类型选择原则

| 需求 | 推荐类型 | 禁止 |
|---|---|---|
| 布尔标志 | `BOOL` | 用 INT 模拟 |
| 计数器（小） | `INT`（-32768~32767） | 超范围不升级 |
| 计数器（大） | `DINT`（±2.1×10⁹） | — |
| 无符号计数 | `UDINT` | 用负数表示无效 |
| 速度/位置/温度 | `REAL` | 用 INT 存小数 |
| 高精度计算 | `LREAL` | — |
| 时间值 | `TIME` | 用 DINT 存毫秒 |
| 位操作 | `BYTE`/`WORD`/`DWORD` | 用 INT 做位操作 |
| 文本 | `STRING[n]` | 用数字编码文本 |

---

## 2. 类型转换规则

`BOOL_TO_INT`、`INT_TO_REAL`、`REAL_TO_INT` 等采用 IEC 类型转换的源类型_TO_目标类型形式，不是 CODESYS 独有关键字。标准形式不代表任意转换组合、扩展类型或所有编译器版本都必然支持。类型转换函数、平台扩展和第三方库函数应分开核对；真实取值范围、舍入与超范围行为仍按目标平台确认。

### 必须使用显式转换函数

```st
// ❌ 禁止隐式转换
iResult := rFloat;        // REAL → INT，禁止依赖隐式转换
rResult := iInt * 2.0;    // INT * REAL，隐式提升

// ✅ 必须显式转换
iResult := REAL_TO_INT(rFloat);          // 按转换规则舍入，先检查范围
iResult := TRUNC_INT(rFloat);            // 向零取整，先检查范围
rResult := INT_TO_REAL(iInt) * 2.0;
```

### 常用转换函数速查

CODESYS V3 的截断操作使用 `TRUNC_INT`（返回 INT）或 `TRUNC`（返回 DINT）；超范围结果不可依赖。依据：[浮点转换](https://content.helpme-codesys.com/en/CODESYS%20Development%20System/_cds_operator_real_to.html)、[TRUNC_INT](https://content.helpme-codesys.com/en/CODESYS%20Development%20System/_cds_operator_trunc_int.html)。

| 转换方向 | 函数 | 说明 |
|---|---|---|
| REAL → INT | `REAL_TO_INT` | 舍入，边界按目标版本确认 |
| REAL → INT | `TRUNC_INT` | 向零取整，先检查范围 |
| INT → REAL | `INT_TO_REAL` | 精确转换 |
| DINT → INT | `DINT_TO_INT` | 注意溢出 |
| INT → DINT | `INT_TO_DINT` | 安全扩展 |
| BOOL → INT | `BOOL_TO_INT` | TRUE=1, FALSE=0 |
| INT → BOOL | `INT_TO_BOOL` | 0=FALSE, 其他=TRUE |
| DINT → STRING | `DINT_TO_STRING` | 数字转字符串 |
| STRING → DINT | `STRING_TO_DINT` | 字符串转数字 |

---

## 3. 整数溢出防护

```st
// INT 范围：-32768 ~ 32767
// 不依赖溢出结果；目标平台与中间计算宽度可能影响行为

// ❌ 危险：累加可能溢出
iCount := iCount + 1;

// ✅ 安全：检查上限
IF iCount < 32767 THEN
    iCount := iCount + 1;
ELSE
    bOverflow := TRUE;
END_IF;

// DINT 扩大计数范围，仍须检查上限
IF diCount < 2147483647 THEN
    diCount := diCount + 1;
ELSE
    bOverflow := TRUE;
END_IF;
```

---

## 4. 数组规则

### 声明

```st
VAR
    // 固定大小数组，索引从 0 开始（推荐）
    aSpeed      : ARRAY[0..9] OF REAL := [10 * (0.0)];
    // 或从 1 开始（注意索引习惯）
    aNames      : ARRAY[1..5] OF STRING[80];
    // 二维数组
    aMatrix     : ARRAY[0..3, 0..3] OF REAL;
END_VAR
```

### 访问前必须检查边界

```st
FUNCTION_BLOCK FB_SafeArrayAccess
VAR_INPUT
    iIndex  : INT := 0;
    rValue  : REAL := 0.0;
END_VAR
VAR_OUTPUT
    bError  : BOOL;
END_VAR
VAR
    aData   : ARRAY[0..99] OF REAL;
END_VAR

IF iIndex >= 0 AND iIndex <= 99 THEN
    aData[iIndex] := rValue;
    bError := FALSE;
ELSE
    bError := TRUE;
END_IF;
```

### 数组大小计算

```st
// 获取数组元素数量
iSize := SIZEOF(aData) / SIZEOF(aData[0]);
```

---

## 5. STRING 规则

### 默认长度

CoDeSys 中 `STRING` 默认长度为 80 字符（`STRING[80]`）。PackML 规范也明确为 80 字符。短单位字段用 `STRING[6]`。

### 操作前检查长度

```st
// 字符串函数索引从 1 开始（不是 0！）
sPart := MID(sSource, 3, 1);   // 从第1个字符取3个：参数顺序为 STR、LEN、POS

// CONCAT 前检查长度
IF LEN(sA) + LEN(sB) <= 80 THEN
    sResult := CONCAT(sA, sB);
ELSE
    bError := TRUE;
END_IF;

// 常用字符串函数
iLen    := LEN(sStr);                    // 字符串长度
iPos    := FIND(sStr, sSubStr);          // 查找子串，返回位置（1起），0=未找到
sSub    := MID(sStr, iLen, iStart);      // 截取子串
sResult := INSERT(sStr, sInsert, iPos);  // 插入
sResult := DELETE(sStr, iLen, iPos);     // 删除
sResult := REPLACE(sStr, sNew, iLen, iPos); // 替换
```

`MID` 参数顺序依据：[Standard MID](https://content.helpme-codesys.com/en/libs/Standard/Current/String-Functions/MID.html)。`UPPER`、`LOWER` 等不是 Standard 库默认字符串函数；大小写转换需核对实际依赖库和接口，不能直接套用其他平台名称。

---

## 6. 用户自定义类型规范

每个 DUT 文件只允许定义一个 `STRUCT` 或一个 `ENUM`。禁止在同一个 `.st` 文件中同时定义多个结构体、多个枚举，或结构体与枚举混写；每个 DUT 独占一个文件，便于 CODESYS 导入、回读和差异审查。

### STRUCT

```st
TYPE ST_AxisData :
STRUCT
    rPosition       : LREAL := 0.0;     // 当前位置 [mm]
    rVelocity       : REAL  := 0.0;     // 当前速度 [mm/s]
    bEnabled        : BOOL  := FALSE;   // 轴已使能
    bError          : BOOL  := FALSE;   // 轴故障
    diErrorID       : DINT  := 0;       // 错误代码
END_STRUCT
END_TYPE
```

### ENUM

```st
{attribute 'qualified_only'}
{attribute 'strict'}
TYPE E_MachineState :
(
    iUnknown    := 0,   // 未知状态，上电默认
    iIdle       := 1,
    iRunning    := 2,
    iFault      := 3
) INT;                  // 底层类型为 INT
END_TYPE
```

ENUM 中每个元素的显式值必须唯一，禁止两个元素使用相同值。

### 大型结构体传递用 VAR_IN_OUT

```st
// ❌ 错误：VAR_INPUT 会复制整个结构体
FUNCTION_BLOCK FB_ProcessData
VAR_INPUT
    stData : ST_LargeStruct;  // 每次调用复制，性能差
END_VAR

// ✅ 正确：VAR_IN_OUT 传引用，零复制
FUNCTION_BLOCK FB_ProcessData
VAR_IN_OUT
    stData : ST_LargeStruct;  // 引用传递
END_VAR
```

---

## 7. 变量作用域规则

| 关键字 | 作用域 | 生命周期 | 典型用途 |
|---|---|---|---|
| `VAR` | POU 内部 | 跨周期保持 | FB 状态、计数器 |
| `VAR_INPUT` | 外部可写 | 跨周期保持 | FB 输入参数 |
| `VAR_OUTPUT` | 外部只读 | 跨周期保持 | FB 输出结果 |
| `VAR_IN_OUT` | 外部读写 | 跨周期保持 | 大型结构体引用 |
| `VAR_TEMP` | POU 内部 | 每次调用重置 | 临时计算变量（禁止放 FB 实例！） |
| `VAR_STAT` | POU 内部 | 跨周期保持（函数内） | 函数内的静态变量 |
| `VAR RETAIN` | POU 内部 | 掉电保持 | 生产计数、配方号 |
| `VAR PERSISTENT` | POU 内部 | 下载后保持 | 机器参数、校准值 |
