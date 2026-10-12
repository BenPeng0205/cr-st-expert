# 格式规范

> 状态：强制执行。

## 1. 缩进与对齐

- 缩进使用 4 个空格。
- 变量声明中的 `:` 和注释列尽量纵向对齐。
- 禁止使用 Tab。

## 2. 语法风格

- 赋值符前后保留空格：`iValue := 100;`
- 功能块调用参数使用命名参数：`PT := T#5s`
- 功能块调用引脚每行一个。
- `);` 与引脚缩进对齐。
- 结束关键字保留 IEC 分号：`END_IF;`

## 3. 实现区

以下对象或段落必须带实现区标记：

- `FUNCTION_BLOCK`
- `FUNCTION`
- `PROGRAM`
- `METHOD`
- `ACTION`
- `PROPERTY` 的 `GET / SET`

统一使用：

```iecst
// === IMPLEMENTATION ===
```

## 4. Property 聚合段

Property 段必须严格为：

```iecst
// === PROPERTY P_Name ===
PROPERTY PUBLIC P_Name : INT
// === GET ===
P_Name := iValue;
// === SET ===
iValue := P_Name;
```

## 5. 禁止项

- 禁止把多个声明挤在同一行。
- 禁止把注释和代码错误拼接为同一行。
- 禁止省略可执行对象和聚合段的实现区 marker。
- 禁止整文件出现“非空行、空行、非空行、空行”的交替空行污染；人工审查需核对空行密度，可选脚本可辅助检查。
- 禁止超过一个连续空行；段落分隔只允许保留一个真实空行。
- 维护者确保 `st_semantic_linter.py` 能拦截异常空行密度；普通用户不要求运行脚本。
