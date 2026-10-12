# FUNCTION_BLOCK mirror 模板

> 用途：生成符合 CODESYS ST text 协议的 `FUNCTION_BLOCK`。一个父 FB 只输出一个 `.st` 文件，`Method / Action / Property` 作为内部段落聚合。

## 父文件模板

```iecst
/// 功能    : <功能描述>
/// 库依赖  : 暂无

{attribute 'hide_all_locals'}
FUNCTION_BLOCK FB_<名称>
VAR_INPUT
    bEnable : BOOL; // 系统允许该功能块运行
END_VAR

VAR_OUTPUT
    bDone : BOOL; // 功能块完成当前动作
END_VAR

VAR
    iValue : INT; // 内部示例变量
END_VAR

// === IMPLEMENTATION ===

/// =======================================================================
/// 名称      : FB_<名称>
/// 功能      : <功能描述>
/// 库依赖    : 暂无
/// 使用说明  : Method、Action、Property 聚合在父 FB mirror 文件内，由 CODESYS 解析并回写。
/// =======================================================================
IF NOT bEnable THEN
    bDone := FALSE;
    RETURN;
END_IF;

// === METHOD M_<方法名> ===
METHOD PUBLIC M_<方法名> : BOOL
VAR_INPUT
    iCandidateValue : INT; // 待校验的候选值
END_VAR
// === IMPLEMENTATION ===
M_<方法名> := iCandidateValue >= 0;

// === ACTION A_<动作名> ===
// === IMPLEMENTATION ===
iValue := 0;
bDone := FALSE;

// === PROPERTY P_<属性名> ===
PROPERTY PUBLIC P_<属性名> : INT
// === GET ===
P_<属性名> := iValue;
// === SET ===
iValue := P_<属性名>;
```

## 约束

- `FUNCTION_BLOCK` 主体、`METHOD`、`ACTION`、`PROPERTY` 必须在同一个父 `FB_*.st` 内。
- 每个子对象段必须使用 `// === METHOD M_Name ===`、`// === ACTION A_Name ===`、`// === PROPERTY P_Name ===` 标记。
- `PROPERTY` 必须同时包含 `GET` 和 `SET` 段。
