from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from st_semantic_linter import lint_file_content, lint_project_root


def _chars(*codepoints: int) -> str:
    return "".join(chr(codepoint) for codepoint in codepoints)


STRICT_FB_SAMPLE = "\n".join(
    [
        "/// 功能    : 测试功能块",
        "/// 库依赖  : 暂无",
        "{attribute 'hide_all_locals'}",
        "FUNCTION_BLOCK FB_Test",
        "VAR_INPUT",
        "    bEnable : BOOL := FALSE; // 使能命令",
        "END_VAR",
        "VAR_OUTPUT",
        "    bError    : BOOL; // 错误标志",
        "    diErrorID : DINT; // 错误代码",
        "END_VAR",
        "// === IMPLEMENTATION ===",
        "",
        "/// =======================================================================",
        "/// 名称      : FB_Test",
        "/// 功能      : 验证语义门禁的最小功能块。",
        "/// 库依赖    : 暂无",
        "/// =======================================================================",
        "/// 使用说明  : 1. 由固定周期任务调用。",
        "///           : 2. 调用方通过诊断输出判断异常。",
        "/// =======================================================================",
        "// 使能命令只用于形成可执行语句，便于验证工程师级注释门禁。",
        "bError    := NOT bEnable;",
        "diErrorID := 0;",
    ]
)


class StSemanticLinterTests(unittest.TestCase):
    def test_rejects_missing_file_header_for_enum(self) -> None:
        issues = lint_file_content(
            "E_State.st",
            "enum",
            "\n".join(
                [
                    "{attribute 'qualified_only'}",
                    "{attribute 'strict'}",
                    "TYPE E_State :",
                    "(",
                    "    iIdle := 0",
                    ");",
                    "END_TYPE",
                ]
            ),
        )

        self.assertTrue(any("file header must include /// 功能" in issue for issue in issues))
        self.assertTrue(any("file header must include /// 库依赖" in issue for issue in issues))

    def test_rejects_mojibake_comment(self) -> None:
        mojibake_function = _chars(0x9354, 0x71BB, 0x5158)
        mojibake_library = _chars(0x6434, 0x64B2, 0x7DF7, 0x74A7)
        mojibake_test = _chars(0x5A34, 0x5B2D, 0x762F)
        mojibake_block = _chars(0x9367)

        issues = lint_file_content(
            "E_State.st",
            "enum",
            "\n".join(
                [
                    f"/// {mojibake_function}    : {mojibake_test}{mojibake_function}{mojibake_block}",
                    f"/// {mojibake_library}  : Standard",
                    "{attribute 'qualified_only'}",
                    "{attribute 'strict'}",
                    "TYPE E_State :",
                    "(",
                    "    iIdle := 0",
                    ");",
                    "END_TYPE",
                ]
            ),
        )

        self.assertTrue(any("comment appears mojibake" in issue for issue in issues))

    def test_rejects_tab_indentation(self) -> None:
        issues = lint_file_content(
            "FB_Test.st",
            "function_block",
            "\tFUNCTION_BLOCK FB_Test",
        )

        self.assertTrue(any("tab character is forbidden" in issue for issue in issues))

    def test_rejects_block_comment(self) -> None:
        issues = lint_file_content(
            "FB_Test.st",
            "function_block",
            "(* 禁止的块注释 *)\nFUNCTION_BLOCK FB_Test",
        )

        self.assertTrue(any("block comment" in issue for issue in issues))

    def test_rejects_every_line_blank_spacing(self) -> None:
        polluted = "\n\n".join(
            [
                "/// Function    : Matrix storage order.",
                "/// Dependency  : None",
                "{attribute 'qualified_only'}",
                "{attribute 'strict'}",
                "TYPE E_Order :",
                "(",
                "    iRowMajor := 0,",
                "    iColMajor := 1",
                ") INT;",
                "END_TYPE",
            ]
        ) + "\n"

        issues = lint_file_content("E_Order.st", "enum", polluted)

        self.assertTrue(any("suspicious every-line blank spacing" in issue for issue in issues))

    def test_rejects_multiple_consecutive_blank_lines(self) -> None:
        issues = lint_file_content(
            "FB_Test.st",
            "function_block",
            "FUNCTION_BLOCK FB_Test\n\n\nVAR\nEND_VAR",
        )

        self.assertTrue(any("more than one consecutive blank line" in issue for issue in issues))

    def test_rejects_unstable_comment_metadata_in_file_header(self) -> None:
        issues = lint_file_content(
            "FB_Test.st",
            "function_block",
            "\n".join(
                [
                    "/// 功能    : 测试功能块",
                    "/// 库依赖  : 暂无",
                    "/// 编程人员 : 张三",
                    "/// 时间    : 2025-01-01",
                    "{attribute 'hide_all_locals'}",
                    "FUNCTION_BLOCK FB_Test",
                ]
            ),
        )

        self.assertTrue(any("unstable author/time/version comment is forbidden" in issue for issue in issues))

    def test_allows_business_description_containing_time_word(self) -> None:
        issues = lint_file_content(
            "FB_CalendarCalc.st",
            "function_block",
            "\n".join(
                [
                    "/// 功能    : 执行日历时间计算，刷新星期和日期相关输出。",
                    "/// 库依赖  : Standard",
                    "{attribute 'hide_all_locals'}",
                    "FUNCTION_BLOCK FB_CalendarCalc",
                    "VAR_OUTPUT",
                    "    bError : BOOL := FALSE; // 当前扫描周期诊断标志，TRUE 表示本对象检测到异常。",
                    "END_VAR",
                    "// === IMPLEMENTATION ===",
                    "/// 名称      : FB_CalendarCalc",
                    "/// 功能      : 执行日历时间计算，刷新星期和日期相关输出。",
                    "/// 库依赖    : Standard",
                    "/// 使用说明  : 1. 每个扫描周期调用一次，输入在调用前写入。",
                    "///           : 2. 输出在本扫描周期刷新，诊断输出用于调用方定位故障。",
                    "// 按日期输入刷新星期输出，时间字样属于业务语义，不是作者或版本元数据。",
                    "bError := FALSE;",
                ]
            ),
        )

        self.assertFalse(any("unstable author/time/version comment is forbidden" in issue for issue in issues))

    def test_rejects_rewrite_boilerplate_comments_and_platform_dependencies(self) -> None:
        issues = lint_file_content(
            "FB_Test.st",
            "function_block",
            STRICT_FB_SAMPLE.replace(
                "/// 功能    : 测试功能块",
                "/// 功能    : OSCAT BASIC 功能块 FB_Test，保留 OSCAT BASIC 原始算法语义",
            ).replace(
                "/// 库依赖  : 暂无",
                "/// 库依赖  : CODESYS Standard 原生库",
            ),
        )

        self.assertTrue(any("legacy source library brand must not appear" in issue for issue in issues))
        self.assertTrue(any("function description must explain behavior" in issue for issue in issues))
        self.assertTrue(any("migration bookkeeping" in issue for issue in issues))
        self.assertTrue(any("library dependency must list concrete library names" in issue for issue in issues))
        self.assertTrue(any("library dependency must list library names only" in issue for issue in issues))

    def test_rejects_over_explained_numeric_tolerance_comments(self) -> None:
        issues = lint_file_content(
            "FB_Test.st",
            "function_block",
            STRICT_FB_SAMPLE.replace(
                "// 使能命令只用于形成可执行语句，便于验证工程师级注释门禁。",
                "// 1.0E-6 是边界公差，为什么不是 1.0E-7：后者接近精度边界，工程收益很小。",
            ),
        )

        self.assertTrue(any("comment is over-explained" in issue for issue in issues))

    def test_rejects_generic_filler_implementation_comments(self) -> None:
        issues = lint_file_content(
            "FB_Test.st",
            "function_block",
            STRICT_FB_SAMPLE.replace(
                "// 使能命令只用于形成可执行语句，便于验证工程师级注释门禁。",
                "// 本段刷新诊断、处理边界条件，并根据内部状态输出当前扫描周期结果。",
            ),
        )

        self.assertTrue(any("generic filler implementation comment is forbidden" in issue for issue in issues))

    def test_rejects_generic_assignment_explanation_comments(self) -> None:
        issues = lint_file_content(
            "FB_Test.st",
            "function_block",
            STRICT_FB_SAMPLE.replace(
                "// 使能命令只用于形成可执行语句，便于验证工程师级注释门禁。",
                "// rValue 由本周期输入和保持量计算得到，后续输出或状态判断直接使用该中间量。",
            ),
        )

        self.assertTrue(any("generic filler implementation comment is forbidden" in issue for issue in issues))

    def test_rejects_generic_special_logic_comments(self) -> None:
        issues = lint_file_content(
            "FB_Test.st",
            "function_block",
            STRICT_FB_SAMPLE.replace(
                "// 使能命令只用于形成可执行语句，便于验证工程师级注释门禁。",
                "// 执行 Test 专用功能逻辑，按该对象的输入契约刷新对应工程输出。",
            ),
        )

        self.assertTrue(any("generic filler implementation comment is forbidden" in issue for issue in issues))

    def test_rejects_generic_function_implementation_comments(self) -> None:
        issues = lint_file_content(
            "F_Test.st",
            "function",
            "\n".join(
                [
                    "/// 功能    : 测试函数",
                    "/// 库依赖  : Standard",
                    "{attribute 'hide_all_locals'}",
                    "FUNCTION F_Test : BOOL",
                    "VAR_INPUT",
                    "    bInputValue : BOOL := FALSE; // 布尔输入，参与触发、使能、选择或组合逻辑。",
                    "END_VAR",
                    "// === IMPLEMENTATION ===",
                    "/// 名称      : F_Test",
                    "/// 功能      : 测试函数。",
                    "/// 库依赖    : Standard",
                    "/// 使用说明  : 1. 调用前提供完整输入参数。",
                    "///           : 2. 函数无内部保持状态，返回值只由当前输入决定。",
                    "// F_Test 的实现区按当前输入刷新输出。",
                    "F_Test := bInputValue;",
                ]
            ),
        )

        self.assertTrue(any("generic filler implementation comment is forbidden" in issue for issue in issues))

    def test_rejects_missing_numbered_usage_lines_in_implementation_header(self) -> None:
        issues = lint_file_content(
            "FB_Test.st",
            "function_block",
            "\n".join(
                [
                    "/// 功能    : 测试功能块",
                    "/// 库依赖  : 暂无",
                    "{attribute 'hide_all_locals'}",
                    "FUNCTION_BLOCK FB_Test",
                    "VAR_OUTPUT",
                    "    bError    : BOOL; // 错误标志",
                    "    diErrorID : DINT; // 错误代码",
                    "END_VAR",
                    "// === IMPLEMENTATION ===",
                    "/// =======================================================================",
                    "/// 名称      : FB_Test",
                    "/// 功能      : 测试功能块。",
                    "/// 库依赖    : 暂无",
                    "/// 使用说明  : 仅描述一句话。",
                    "/// =======================================================================",
                ]
            ),
        )

        self.assertTrue(any("implementation usage note must include numbered item 1" in issue for issue in issues))
        self.assertTrue(any("implementation usage note must include numbered item 2" in issue for issue in issues))

    def test_accepts_complete_implementation_header_usage_lines(self) -> None:
        issues = lint_file_content("FB_Test.st", "function_block", STRICT_FB_SAMPLE)

        self.assertEqual([], issues)

    def test_rejects_implementation_code_without_engineering_comment(self) -> None:
        issues = lint_file_content(
            "FB_Test.st",
            "function_block",
            STRICT_FB_SAMPLE.replace("// 使能命令只用于形成可执行语句，便于验证工程师级注释门禁。\n", ""),
        )

        self.assertTrue(any("implementation code must include engineering" in issue for issue in issues))

    def test_rejects_case_without_else(self) -> None:
        issues = lint_file_content(
            "FB_Test.st",
            "function_block",
            "\n".join(
                [
                    "CASE eState OF",
                    "    E_State.iIdle:",
                    "        bDone := TRUE;",
                    "END_CASE;",
                ]
            ),
        )

        self.assertTrue(any("CASE must include ELSE" in issue for issue in issues))

    def test_ignores_case_word_inside_comment(self) -> None:
        issues = lint_file_content(
            "FB_Test.st",
            "function_block",
            "// 这里说明 CASE 的写法，但不是实际状态机。",
        )

        self.assertFalse(any("CASE must include ELSE" in issue for issue in issues))

    def test_rejects_timer_in_var_temp(self) -> None:
        issues = lint_file_content(
            "FB_Test.st",
            "function_block",
            "\n".join(
                [
                    "VAR_TEMP",
                    "    tonDelay : TON; // 临时定时器",
                    "END_VAR",
                ]
            ),
        )

        self.assertTrue(any("TON instance must not be declared in VAR_TEMP" in issue for issue in issues))

    def test_rejects_real_equality(self) -> None:
        issues = lint_file_content(
            "F_Test.st",
            "function",
            "\n".join(
                [
                    "VAR_INPUT",
                    "    rValue : REAL := 0.0; // 测试数值",
                    "END_VAR",
                    "IF rValue = 1.0 THEN",
                    "END_IF;",
                ]
            ),
        )

        self.assertTrue(any("REAL/LREAL equality" in issue for issue in issues))

    def test_rejects_empty_pin(self) -> None:
        issues = lint_file_content(
            "FB_Test.st",
            "function_block",
            "fbMotor(\n    bEnable := ,\n    );",
        )

        self.assertTrue(any("empty named argument pin" in issue for issue in issues))

    def test_rejects_unaligned_var_declarations(self) -> None:
        issues = lint_file_content(
            "FB_Test.st",
            "function_block",
            "\n".join(
                [
                    "VAR_INPUT",
                    "    bEnable : BOOL := FALSE; // 使能命令",
                    "    iTargetSpeed : INT := 0; // 目标速度",
                    "END_VAR",
                ]
            ),
        )

        self.assertTrue(any("declaration ':' columns must align" in issue for issue in issues))

    def test_rejects_variable_without_trailing_comment(self) -> None:
        issues = lint_file_content(
            "FB_Test.st",
            "function_block",
            "\n".join(
                [
                    "VAR_OUTPUT",
                    "    bRunning : BOOL;",
                    "    eState   : E_State; // 当前状态",
                    "END_VAR",
                ]
            ),
        )

        self.assertTrue(any("variable declaration must include trailing //" in issue for issue in issues))

    def test_rejects_var_input_without_default(self) -> None:
        issues = lint_file_content(
            "FB_Test.st",
            "function_block",
            "\n".join(
                [
                    "VAR_INPUT",
                    "    bEnable : BOOL; // 使能命令",
                    "END_VAR",
                ]
            ),
        )

        self.assertTrue(any("VAR_INPUT declaration must provide a safe default value" in issue for issue in issues))

    def test_allows_struct_var_input_without_default(self) -> None:
        issues = lint_file_content(
            "F_Test.st",
            "function",
            "\n".join(
                [
                    "/// 功能    : 按结构体输入计算测试结果。",
                    "/// 库依赖  : 暂无",
                    "{attribute 'hide_all_locals'}",
                    "FUNCTION F_Test : ST_Value",
                    "VAR_INPUT",
                    "    stValue : ST_Value; // 输入结构体。",
                    "END_VAR",
                    "// === IMPLEMENTATION ===",
                    "/// 名称      : F_Test",
                    "/// 功能      : 按结构体输入计算测试结果。",
                    "/// 库依赖    : 暂无",
                    "/// 使用说明  : 1. 调用前由调用方填充结构体字段。",
                    "///           : 2. 结构体输入不写默认值，避免 IDE 对结构体默认初始化产生告警。",
                    "// 结构体字段由调用方提供，本函数只透传字段用于验证结构体输入门禁例外。",
                    "F_Test := stValue;",
                ]
            ),
        )

        self.assertFalse(any("VAR_INPUT declaration must provide a safe default value" in issue for issue in issues))

    def test_rejects_pointer_in_var_input(self) -> None:
        issues = lint_file_content(
            "FB_Test.st",
            "function_block",
            "\n".join(
                [
                    "VAR_INPUT",
                    "    pBuffer : POINTER TO BYTE := 0; // 数据指针",
                    "END_VAR",
                ]
            ),
        )

        self.assertTrue(any("VAR_INPUT must not expose POINTER" in issue for issue in issues))

    def test_rejects_wrong_variable_prefix(self) -> None:
        issues = lint_file_content(
            "FB_Test.st",
            "function_block",
            "\n".join(
                [
                    "VAR",
                    "    value : INT; // 错误前缀",
                    "END_VAR",
                ]
            ),
        )

        self.assertTrue(any("should use 'i' prefix" in issue for issue in issues))

    def test_rejects_single_line_named_argument_call(self) -> None:
        issues = lint_file_content(
            "FB_Test.st",
            "function_block",
            "iLimitedSpeed := F_LimitSpeed(iValue := iTargetSpeed);",
        )

        self.assertTrue(any("named argument call must use multiline pin format" in issue for issue in issues))

    def test_rejects_call_closing_not_aligned_with_pins(self) -> None:
        issues = lint_file_content(
            "FB_Test.st",
            "function_block",
            "\n".join(
                [
                    "fbMotor(",
                    "    bEnable := bEnable,",
                    ");",
                ]
            ),
        )

        self.assertTrue(any("call closing ');' must align with pins" in issue for issue in issues))

    def test_rejects_unaligned_call_pin_operators(self) -> None:
        issues = lint_file_content(
            "FB_Test.st",
            "function_block",
            "\n".join(
                [
                    "fbMotor(",
                    "    bRun := bRun,",
                    "    iRequestedSpeed := iTargetSpeed",
                    "    );",
                ]
            ),
        )

        self.assertTrue(any("named argument ':=' columns must align" in issue for issue in issues))

    def test_rejects_blank_line_inside_named_argument_call(self) -> None:
        issues = lint_file_content(
            "FB_Test.st",
            "function_block",
            "\n".join(
                [
                    "fbMotor(",
                    "",
                    "    bRun := bRun",
                    "    );",
                ]
            ),
        )

        self.assertTrue(any("blank line inside named argument call" in issue for issue in issues))

    def test_accepts_strict_style_call_and_declarations(self) -> None:
        issues = lint_file_content(
            "FB_Test.st",
            "function_block",
            "\n".join(
                [
                    "VAR_INPUT",
                    "    bEnable      : BOOL := FALSE; // 使能命令",
                    "    iTargetSpeed : INT  := 0;     // 目标速度",
                    "END_VAR",
                    "",
                    "fbMotor(",
                    "    bEnable      := bEnable,",
                    "    iTargetSpeed := iTargetSpeed",
                    "    );",
                ]
            ),
        )

        self.assertEqual([], issues)

    def test_rejects_missing_function_block_error_contract(self) -> None:
        issues = lint_file_content(
            "FB_Test.st",
            "function_block",
            "\n".join(
                [
                    "/// 功能    : 测试功能块",
                    "/// 库依赖  : 暂无",
                    "{attribute 'hide_all_locals'}",
                    "FUNCTION_BLOCK FB_Test",
                    "VAR_OUTPUT",
                    "    bDone : BOOL; // 完成标志",
                    "END_VAR",
                ]
            ),
        )

        self.assertTrue(any("must expose bError/xError" in issue for issue in issues))
        self.assertTrue(any("must expose diErrorID/udiErrorID" in issue for issue in issues))

    def test_rejects_plcopen_style_public_pin_names_without_hungarian_prefix(self) -> None:
        issues = lint_file_content(
            "FB_Test.st",
            "function_block",
            "\n".join(
                [
                    "VAR_INPUT",
                    "    Execute : BOOL := FALSE; // 触发命令",
                    "END_VAR",
                    "VAR_OUTPUT",
                    "    Done    : BOOL; // 完成标志",
                    "    Busy    : BOOL; // 忙碌标志",
                    "    Error   : BOOL; // 错误标志",
                    "    ErrorID : DINT; // 错误代码",
                    "END_VAR",
                ]
            ),
        )

        self.assertTrue(any("variable 'Execute' should use 'b' prefix" in issue for issue in issues))
        self.assertTrue(any("variable 'Done' should use 'b' prefix" in issue for issue in issues))
        self.assertTrue(any("variable 'Busy' should use 'b' prefix" in issue for issue in issues))
        self.assertTrue(any("variable 'Error' should use 'b' prefix" in issue for issue in issues))
        self.assertTrue(any("variable 'ErrorID' should use 'di' prefix" in issue for issue in issues))

    def test_rejects_missing_hide_all_locals_for_function_block(self) -> None:
        issues = lint_file_content(
            "FB_Test.st",
            "function_block",
            "/// 功能    : 测试功能块\n/// 库依赖  : 暂无\nFUNCTION_BLOCK FB_Test",
        )

        self.assertTrue(any("hide_all_locals" in issue for issue in issues))

    def test_rejects_hide_all_locals_on_program(self) -> None:
        issues = lint_file_content(
            "PRG_Test.st",
            "program",
            "/// 功能    : 测试程序\n/// 库依赖  : 暂无\n{attribute 'hide_all_locals'}\nPROGRAM PRG_Test",
        )

        self.assertTrue(any("PROGRAM must not use" in issue for issue in issues))

    def test_rejects_enum_without_required_attributes(self) -> None:
        issues = lint_file_content(
            "E_State.st",
            "enum",
            "/// 功能    : 状态枚举\n/// 库依赖  : 暂无\nTYPE E_State :\n(\n    iIdle := 0\n) INT;\nEND_TYPE",
        )

        self.assertTrue(any("qualified_only" in issue for issue in issues))
        self.assertTrue(any("strict" in issue for issue in issues))

    def test_rejects_enum_value_without_base_type_prefix(self) -> None:
        issues = lint_file_content(
            "E_State.st",
            "enum",
            "\n".join(
                [
                    "/// 功能    : 状态枚举",
                    "/// 库依赖  : 暂无",
                    "{attribute 'qualified_only'}",
                    "{attribute 'strict'}",
                    "TYPE E_State :",
                    "(",
                    "    Idle := 0",
                    ") INT;",
                    "END_TYPE",
                ]
            ),
        )

        self.assertTrue(any("enum value 'Idle' must use 'i' prefix" in issue for issue in issues))

    def test_rejects_public_object_extra_underscore(self) -> None:
        issues = lint_file_content(
            "FB_Json_ToStruct.st",
            "function_block",
            "FUNCTION_BLOCK FB_Json_ToStruct",
        )

        self.assertTrue(any("public object body must not contain extra underscore" in issue for issue in issues))

    def test_rejects_redundant_library_domain_token_when_configured(self) -> None:
        issues = lint_file_content(
            "FB_CurveArchimedeanSpiral.st",
            "function_block",
            "FUNCTION_BLOCK FB_CurveArchimedeanSpiral",
            domain_tokens=["Curve"],
        )

        self.assertTrue(any("repeats library domain token 'Curve'" in issue for issue in issues))

    def test_project_root_infers_curve_domain_token_from_folder_name(self) -> None:
        with tempfile.TemporaryDirectory(prefix="00 曲线规划库") as temp_dir:
            root = Path(temp_dir)
            (root / "POUs" / "FBs").mkdir(parents=True)
            (root / "POUs" / "FBs" / "FB_CurveLine.st").write_text(
                "FUNCTION_BLOCK FB_CurveLine",
                encoding="utf-8",
            )

            result = lint_project_root(root)

        self.assertFalse(result.passed)
        self.assertTrue(any("repeats library domain token 'Curve'" in issue for issue in result.issues))

    def test_rejects_unguarded_unsigned_minus_one_loop(self) -> None:
        issues = lint_file_content(
            "FB_Test.st",
            "function_block",
            "\n".join(
                [
                    "VAR",
                    "    uiLength : UINT; // 数据长度",
                    "    uiIndex  : UINT; // 循环索引",
                    "END_VAR",
                    "FOR uiIndex := 0 TO uiLength - 1 DO",
                    "END_FOR;",
                ]
            ),
        )

        self.assertTrue(any("unsigned length loop upper bound" in issue for issue in issues))

    def test_accepts_guarded_unsigned_minus_one_loop(self) -> None:
        issues = lint_file_content(
            "FB_Test.st",
            "function_block",
            "\n".join(
                [
                    "VAR",
                    "    uiLength : UINT; // 数据长度",
                    "    uiIndex  : UINT; // 循环索引",
                    "END_VAR",
                    "IF uiLength > 0 THEN",
                    "    FOR uiIndex := 0 TO uiLength - 1 DO",
                    "    END_FOR;",
                    "END_IF;",
                ]
            ),
        )

        self.assertFalse(any("unsigned length loop upper bound" in issue for issue in issues))

    def test_project_root_scans_all_st_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "POUs" / "FBs").mkdir(parents=True)
            (root / "POUs" / "FBs" / "FB_Test.st").write_text(STRICT_FB_SAMPLE, encoding="utf-8")
            (root / "POUs" / "FBs" / "FB_BadName_Test.st").write_text(
                "FUNCTION_BLOCK FB_BadName_Test",
                encoding="utf-8",
            )

            result = lint_project_root(root)

        self.assertEqual(2, result.checked_files)
        self.assertFalse(result.passed)
        self.assertTrue(any("public object body must not contain extra underscore" in issue for issue in result.issues))


if __name__ == "__main__":
    unittest.main()
