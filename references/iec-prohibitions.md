# CODESYS 平台用法、规范约定与高风险写法

> 本文件包含 IEC 标准用法、CODESYS 扩展与实现约束，以及本技能选择的工程约定。不能把全部条目都称为厂家独有语法；分类需考虑 IEC 标准版次、编译器版本、目标平台和实际库接口。

## 标准与平台扩展的分类

- `BOOL_TO_INT`、`INT_TO_REAL`、`REAL_TO_INT` 等采用 IEC 类型转换函数的源类型_TO_目标类型形式，不是 CODESYS 独有的关键字。不能因为名称含 `_TO_`，就认定任意类型组合或涉及平台扩展类型的转换都由标准规定。
- IEC 61131-3:2013 已包含新的转换函数、引用、命名空间和面向对象功能。不能把 METHOD、接口或继承一概宣传为 CODESYS 独有；实际语法与实现支持仍需核对。
- CODESYS 官方明确将 `AND_THEN`、`OR_ELSE` 和 `ADR` 标为 IEC 扩展。这些扩展可能也被其他平台支持，不能据此称为 CODESYS 厂家专享语法。
- CODESYS 属性名、方法变量存储规则和位变量传参约束应按官方资料核对。规范选择和语法限制分开说明：违反本技能的命名、注释约定，不代表编译器必然拒绝。
- `TO_INT` 等重载转换在不同版次标准与厂商资料中有分类差异。本技能优先使用明确的源类型_TO_目标类型，不把重载形式一概认定为永久非标准语法。

依据：[IEC 第三版说明](https://webstore.iec.ch/en/publication/4552)、[标准符合性表 21–25](https://cache.industry.siemens.com/dl/files/748/109476748/att_845621/v1/IEC_61131_compliance_en_US.pdf)、[CODESYS 转换说明](https://content.helpme-codesys.com/en/CODESYS%20Development%20System/_cds_operator_bool_to.html)。

---

## 一、命名空间与属性声明

### 1.1 枚举必须加 `qualified_only` + `strict`

```st
{attribute 'qualified_only'}
{attribute 'strict'}
TYPE E_Mode :
(
    iStop   := 0,
    iRun    := 1,
    iError  := 2
) INT;
END_TYPE
```

**`qualified_only` 的作用**：要求限定访问枚举成员，例如 `E_Mode.iStop`。不得将未加属性的同名成员解析一概描述为编译器静默选择；遮蔽与歧义按实际作用域和编译器规则判断。

**`strict` 的作用**（V3.5 SP7 起新建枚举默认添加）：严格检查枚举使用，禁止枚举算术运算、赋入未定义的常量值，以及赋入其他类型的非常量变量。优先赋值已声明成员，例如 `eState := E_Mode.iRun`。外部整数应先通过 CASE 等方式核对合法值，再映射到枚举成员；不能把强制转换当作合法状态校验。

依据：[枚举严格规则](https://content.helpme-codesys.com/en/CODESYS%20Development%20System/_cds_datatype_enum.html)。

**枚举引用规则**：始终使用完整命名空间，`E_Mode.iRun`，不能裸用 `iRun`。

**枚举值唯一规则**：同一个 ENUM 中禁止两个元素使用相同显式值。重复值会让状态诊断、CASE 分支和日志解析失去唯一性。

---

### 1.2 GVL 必须加 `qualified_only`

```st
{attribute 'qualified_only'}
VAR_GLOBAL
    iSystemState    : INT;
    bMachineReady   : BOOL;
END_VAR
```

**原因**：本技能采用限定访问，明确变量归属。加上 `qualified_only` 后，应使用 `GVL_System.iState`；不满足限定要求的裸名访问会报错。同名变量的歧义可由编译器报告，不能宣称必然静默选取某一个。

依据：[qualified_only](https://content.helpme-codesys.com/en/CODESYS%20Development%20System/_cds_pragma_attribute_qualified_only.html)、[名称解析规则](https://content.helpme-codesys.com/en/CODESYS%20Development%20System/_cds_shadowing_rules.html)。

---

### 1.3 FB / FC 必须加 `hide_all_locals`

```st
{attribute 'hide_all_locals'}
FUNCTION_BLOCK FB_MotorControl
```

**原因**：本技能采用此属性隐藏局部变量在输入助手、组件列表、在线声明和符号配置中的显示。它不是访问控制机制，不能据此认定外部代码无法访问局部变量；业务接口仍需明确约束。

**注意**：隐藏显示不等于禁止代码访问，也不自动建立持久化限制。调试显示和 RETAIN / PERSISTENT 的支持分别按目标编译器、属性和声明位置核对。

本技能约定 PRG / PROGRAM 不使用 `{attribute 'hide_all_locals'}`，便于任务入口调试；这是规范选择，不宣称为平台的语法禁令。

依据：[hide_all_locals](https://content.helpme-codesys.com/en/CODESYS%20Development%20System/_cds_pragma_attribute_hide_all_locals.html)。

---

### 1.4 库命名空间冲突

本地对象与库对象可能出现遮蔽或歧义。应按实际库命名空间使用限定访问，例如 `LibraryNamespace.F_Name`，并核对库占位符及符号是否可见。CODESYS 官方允许通过限定访问区分库元素，不能将重命名描述为唯一办法。

---

## 二、类型系统禁忌

### 2.1 禁止使用 CHAR 类型

```st
// 禁止
sChar : CHAR;

// 正确
sChar : STRING(1);
```

**原因**：本技能在字符串函数的单字符文本场景采用 `STRING(1)`，避免把单字节数据直接当 STRING 传入。不要在未确认支持时自行声明 `CHAR`，也不要把此规范选择说成 IEC 标准从未定义字符类型。`STRING(1)` 的容量与编码有关，不适用于任意一个中文字符；标准版次和目标平台支持需分别核对。

---

### 2.2 禁止用 `+` 拼接字符串

```st
// 禁止：IEC 61131-3 未定义 STRING 的 + 运算符
sResult := sA + sB;

// 正确
sResult := CONCAT(sA, sB);

// 多段拼接
sResult := CONCAT(CONCAT(sA, sB), sC);
```

**原因**：CODESYS ADD 的允许类型不包含普通 STRING，应使用已确认的字符串函数。CONCAT 仍需检查目标容量，不能用正确函数名代替长度校验。此例属于标准用法和平台支持核对，不宣称为 CODESYS 独有语法。

---

### 2.3 LOWERCASE / TRIM / UPPERCASE 不是标准库函数

这三个函数不在 CoDeSys 标准库（`Standard.library`）中。它们的可用性取决于：
- 是否安装了 CoDeSys String Libraries 扩展库
- 目标 PLC 厂商是否提供了对应实现（如 Beckhoff 的 `Tc2_Standard`）

**规则**：`UPPER`、`LOWER`、`ASC`、`CHR` 也不能未经核对就当作 Standard 库的默认函数。需要大小写或去空白处理时，确认实际库、命名空间、参数和编码；未知时列为待确认，不编造替代接口。依赖的函数在文件头声明对应库。

依据：[Standard 库函数列表](https://content.helpme-codesys.com/en/libs/Standard/Current/index.html)。

---

### 2.4 禁止使用 VAR_STAT（在 FB 中）

```st
// 禁止：VAR_STAT 在 FB 中是所有实例共享的静态变量
FUNCTION_BLOCK FB_Counter
VAR_STAT
    iSharedCount : INT;   // 所有 FB_Counter 实例共享同一个 iSharedCount！
END_VAR
```

**原因**：`VAR_STAT` 在 FB 中声明的变量是**类级别**的，所有实例共享同一份数据，不是每个实例独立的。这与大多数开发者的预期完全相反。在 FB 中需要跨周期保持的状态，应使用普通 `VAR`。

`VAR_STAT` 在**函数（FC）**中是合法且有用的——FC 没有实例，`VAR_STAT` 给函数提供了跨调用的持久状态。

---

### 2.5 VAR_INST 的正确用法

`VAR_INST` 用于 FB 的**方法（METHOD）**内部，声明的变量存储在 FB 实例的内存上（而非方法调用栈），因此在方法调用之间保持值：

```st
METHOD M_Process
VAR_INST
    iCallCount : INT;   // 每个 FB 实例独立，跨方法调用保持
END_VAR
```

与 `VAR_STAT` 的区别：`VAR_INST` 是**每实例独立**的，`VAR_STAT` 是**所有实例共享**的。

---

### 2.6 隐式类型转换的危险

窄化隐式转换（如 `DINT → INT`）可能丢失数值。是否允许、是否提示和结果必须按目标编译器与平台确认：

```st
// 危险：diLargeValue = 100000，超出 INT 范围（-32768~32767）
// 危险：不能依赖超范围转换的结果或诊断
iResult := diLargeValue;

// 仅明确转换意图；执行前仍须检查 INT 范围
iResult := DINT_TO_INT(diLargeValue);
```

同样危险的隐式转换：
- `REAL → INT`：必须明确舍入策略并检查范围，不将转换一律解释为截断
- 负 `INT` → `UINT`：必须先拒绝负值
- 枚举与整数互转：必须检查合法枚举值

**规则**：所有窄化转换必须使用显式转换函数。

---

### 2.7 不依赖整数溢出结果

中间计算宽度、溢出结果和诊断受目标平台影响。规范要求计算前检查边界，不假定所有平台都静默回绕或抛异常。

```st
// 危险：结果超出 INT 范围
iCount := 32767;
iCount := iCount + 1;   // 不依赖超范围结果
```

需要防溢出时，必须手动检查边界：

```st
IF iCount < 32767 THEN
    iCount := iCount + 1;
ELSE
    bOverflow := TRUE;
END_IF;
```

---

## 三、RETAIN / PERSISTENT 变量陷阱

### 3.1 RETAIN vs PERSISTENT 的区别

| 机制                  | 暖启动保持 | 冷启动保持 | 下载后保持 | 掉电保持       |
|---------------------|-------|-------|-------|------------|
| `RETAIN`            | ✅     | ❌     | ❌（重置为初始值） | 取决于硬件     |
| `PERSISTENT RETAIN` | ✅     | ✅     | ✅     | 取决于硬件     |

**常见误解**：RETAIN 不等于"永久保持"。全量下载会将 RETAIN 变量重置为初始值。需要跨下载保持的数据（如生产计数、校准值），必须用 `PERSISTENT RETAIN`。

---

### 3.2 结构体布局变更使 RETAIN 数据失效

如果修改了包含 RETAIN 变量的结构体（增删成员、改变顺序），内存中保存的旧数据不再与新布局对应，读出的值是垃圾。CoDeSys 不会自动迁移 RETAIN 数据。

**规则**：修改 RETAIN 结构体后，必须执行冷启动（或手动清零 RETAIN 区域）。

---

### 3.3 FB 内不能单独声明 PERSISTENT

在 FB 内部，必须写 `PERSISTENT RETAIN` 或 `RETAIN PERSISTENT`，不能只写 `PERSISTENT`（编译报错）。

---

## 四、指针安全规则

### 4.1 指针算术单位是字节

CoDeSys 的指针加减以**字节**为单位，不是以元素大小为单位（与 C 不同）：

```st
// 错误：以为 +1 移动一个 INT（2字节），实际只移动 1 字节
pInt := pInt + 1;

// 正确：移动一个 INT 的大小
pInt := pInt + SIZEOF(INT);   // = pInt + 2
```

---

### 4.2 Online Change 后指针失效

Online Change 后，静态变量可能在内存中移动。跨周期保存的指针（`ADR()` 的结果）可能指向错误地址。

**规则**：不要跨周期保存指针。每个扫描周期用 `ADR()` 重新获取地址。

---

### 4.3 不要在 VAR_INPUT 中传递指针

指针作为 VAR_INPUT 传入 FB 时，FB 无法控制指针的生命周期，也无法保证 Online Change 后指针仍然有效。使用 `VAR_IN_OUT` 传递引用代替。

### 4.4 不把普通 AND / OR 当作短路保护

在 CODESYS ST 中，普通 `AND` / `OR` 会计算各操作数；`AND_THEN` / `OR_ELSE` 才提供相应的短路求值。不能用 `pValue <> 0 AND pValue^ > 0` 作为空指针保护。可分层 IF 先核对指针，再访问；选择 CODESYS 扩展时可使用 `AND_THEN`。`OR_ELSE` 适用于左侧成立后无需执行右侧的场景。两者为官方标注的 IEC 扩展，不是保证逻辑正确的自动修复。

`ADR(variable)` 获取地址也是官方标注的扩展。在线修改后地址可能变化，指针类型、存储期、长度和重新获取策略仍须核对；不要混用其他厂商或其他语言的取址语法。

依据：[AND_THEN](https://content.helpme-codesys.com/en/CODESYS%20Development%20System/_cds_operator_and_then.html)、[OR_ELSE](https://content.helpme-codesys.com/en/CODESYS%20Development%20System/_cds_operator_or_else.html)、[ADR](https://content.helpme-codesys.com/en/CODESYS%20Development%20System/_cds_operator_adr.html)。

### 4.5 VAR_IN_OUT 的实参约束

普通 `VAR_IN_OUT` 需要有可写存储位置的实参，不能直接传入常量、字符串字面量或位变量；不要与 `VAR_IN_OUT CONSTANT` 混为一谈。位变量可按实际读写语义通过普通 BOOL 中间变量传入，调用后需要时回写原位。参数必需时不可遗漏；字符串实参长度需与形参相匹配。普通位访问本身可以合法，禁止的是不满足引用传参约束的用法。

依据：[VAR_IN_OUT 及官方 C0201、C0417 示例](https://content.helpme-codesys.com/en/CODESYS%20Development%20System/_cds_vartypes_var_in_out.html)。

---

## 五、多任务安全

### 5.1 FB 实例不能被多个任务同时调用

如果两个不同优先级的任务都调用同一个 FB 实例，高优先级任务可以在低优先级任务执行 FB 中途抢占，导致 FB 内部状态被部分更新，产生数据损坏。

**规则**：每个 FB 实例只分配给一个任务。跨任务共享数据通过全局变量 + 原子操作或临界区保护。

---

### 5.2 64 位变量读写不是原子操作

在 32 位目标上，`LREAL`、`LINT`、`ULINT`（64 位类型）的读写不是原子的。一个任务可能读到另一个任务写了一半的值。

**规则**：跨任务共享 64 位变量时，必须使用临界区（`IecCriticalSection` 或平台等效机制）保护。

---

## 六、ANY 类型使用限制

`ANY` 类型只能用于函数、FB 和方法的输入参数，不能用于程序（PRG）。

`ANY` 输入不能接收常量或属性（Property）——必须是变量引用。

用户自定义代码中实现泛型算法时，`ANY` 的内部类型描述符结构未公开文档化，跨版本和跨目标不保证兼容。安全用法是将变量传递给标准库中声明了 `ANY` 输入的函数（如 `MemCpy`）。
