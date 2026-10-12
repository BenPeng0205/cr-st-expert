from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from protocol_validator import validate_file_content, validate_file_location


class ProtocolValidatorTests(unittest.TestCase):
    def test_rejects_public_object_name_with_extra_underscores(self) -> None:
        issues = validate_file_content(
            {
                "path": "FB_JSON_ToStruct.st",
                "family": "function_block",
            },
            "\n".join(
                [
                    "/// 功能    : JSON 解析",
                    "/// 库依赖  : 暂无",
                    "{attribute 'hide_all_locals'}",
                    "FUNCTION_BLOCK FB_JSON_ToStruct",
                    "// === IMPLEMENTATION ===",
                    "/// =======================================================================",
                    "/// 名称      : FB_JSON_ToStruct",
                    "/// 功能      : JSON 解析",
                    "/// 库依赖    : 暂无",
                    "/// 使用说明  : 主文件只保留声明区和主体实现区",
                    "/// =======================================================================",
                ]
            ),
        )

        self.assertTrue(issues)
        self.assertTrue(any("no extra underscores" in issue for issue in issues))

    def test_accepts_public_object_name_with_pascal_case_body(self) -> None:
        issues = validate_file_content(
            {
                "path": "FB_JsonParser.st",
                "family": "function_block",
            },
            "\n".join(
                [
                    "/// 功能    : JSON 解析",
                    "/// 库依赖  : 暂无",
                    "{attribute 'hide_all_locals'}",
                    "FUNCTION_BLOCK FB_JsonParser",
                    "// === IMPLEMENTATION ===",
                    "/// =======================================================================",
                    "/// 名称      : FB_JsonParser",
                    "/// 功能      : JSON 解析",
                    "/// 库依赖    : 暂无",
                    "/// 使用说明  : 主文件只保留声明区和主体实现区",
                    "/// =======================================================================",
                ]
            ),
        )

        self.assertEqual(issues, [])

    def test_rejects_public_function_name_with_mechanical_json_prefix(self) -> None:
        issues = validate_file_content(
            {
                "path": "F_JSON_ValueToString.st",
                "family": "function",
            },
            "\n".join(
                [
                    "/// 功能    : JSON 值转字符串",
                    "/// 库依赖  : 暂无",
                    "{attribute 'hide_all_locals'}",
                    "FUNCTION F_JSON_ValueToString : STRING",
                    "// === IMPLEMENTATION ===",
                    "/// =======================================================================",
                    "/// 名称      : F_JSON_ValueToString",
                    "/// 功能      : JSON 值转字符串",
                    "/// 库依赖    : 暂无",
                    "/// 使用说明  : 调用前必须确认输入值类型",
                    "/// =======================================================================",
                    "F_JSON_ValueToString := '';",
                ]
            ),
        )

        self.assertTrue(issues)
        self.assertTrue(any("no extra underscores" in issue for issue in issues))

    def test_rejects_public_program_name_with_extra_underscores(self) -> None:
        issues = validate_file_content(
            {
                "path": "PRG_Test_JSON_Array.st",
                "family": "program",
            },
            "\n".join(
                [
                    "/// 功能    : JSON 数组测试",
                    "/// 库依赖  : 暂无",
                    "PROGRAM PRG_Test_JSON_Array",
                    "// === IMPLEMENTATION ===",
                    "/// =======================================================================",
                    "/// 名称      : PRG_Test_JSON_Array",
                    "/// 功能      : JSON 数组测试",
                    "/// 库依赖    : 暂无",
                    "/// 使用说明  : 仅用于验证数组解析边界",
                    "/// =======================================================================",
                ]
            ),
        )

        self.assertTrue(issues)
        self.assertTrue(any("no extra underscores" in issue for issue in issues))

    def test_rejects_file_name_that_differs_from_declared_object_name(self) -> None:
        issues = validate_file_content(
            {
                "path": "FB_JsonToStruct.st",
                "family": "function_block",
            },
            "\n".join(
                [
                    "/// 功能    : JSON 解析",
                    "/// 库依赖  : 暂无",
                    "{attribute 'hide_all_locals'}",
                    "FUNCTION_BLOCK FB_JsonParser",
                    "// === IMPLEMENTATION ===",
                    "/// =======================================================================",
                    "/// 名称      : FB_JsonParser",
                    "/// 功能      : JSON 解析",
                    "/// 库依赖    : 暂无",
                    "/// 使用说明  : 主文件只保留声明区和主体实现区",
                    "/// =======================================================================",
                ]
            ),
        )

        self.assertTrue(issues)
        self.assertTrue(any("must match declared object name" in issue for issue in issues))

    def test_rejects_standalone_child_file_family(self) -> None:
        issues = validate_file_content(
            {
                "path": "FB_MotorController.A_ResetFault.st",
                "family": "action",
            },
            "// === IMPLEMENTATION ===\ndiState := 0;\n",
        )

        self.assertTrue(issues)
        self.assertTrue(any("must be aggregated inside parent FUNCTION_BLOCK mirror file" in issue for issue in issues))

    def test_accepts_function_block_with_mirror_child_segments(self) -> None:
        issues = validate_file_content(
            {
                "path": "FB_MotorController.st",
                "family": "function_block",
            },
            "\n".join(
                [
                    "/// 功能    : 电机控制",
                    "/// 库依赖  : Standard",
                    "{attribute 'hide_all_locals'}",
                    "FUNCTION_BLOCK FB_MotorController",
                    "VAR_INPUT",
                    "    bEnable : BOOL; // 系统允许电机控制逻辑运行",
                    "END_VAR",
                    "VAR",
                    "    iTargetSpeed : INT; // 目标速度[rpm]",
                    "END_VAR",
                    "// === IMPLEMENTATION ===",
                    "/// =======================================================================",
                    "/// 名称      : FB_MotorController",
                    "/// 功能      : 电机控制",
                    "/// 库依赖    : Standard",
                    "/// 使用说明  : Method、Action、Property 聚合在父 FB mirror 文件内。",
                    "/// =======================================================================",
                    "bRunning := bEnable;",
                    "",
                    "// === METHOD M_Init ===",
                    "METHOD PUBLIC M_Init : BOOL",
                    "VAR_INPUT",
                    "END_VAR",
                    "// === IMPLEMENTATION ===",
                    "M_Init := TRUE;",
                    "",
                    "// === ACTION A_ResetFault ===",
                    "// === IMPLEMENTATION ===",
                    "diFaultCode := 0;",
                    "",
                    "// === PROPERTY P_TargetSpeed ===",
                    "PROPERTY PUBLIC P_TargetSpeed : INT",
                    "// === GET ===",
                    "P_TargetSpeed := iTargetSpeed;",
                    "// === SET ===",
                    "iTargetSpeed := P_TargetSpeed;",
                ]
            ),
        )

        self.assertEqual(issues, [])

    def test_rejects_property_accessor_implementation_markers(self) -> None:
        issues = validate_file_content(
            {
                "path": "FB_MotorController.st",
                "family": "function_block",
            },
            "\n".join(
                [
                    "/// 功能    : 电机控制",
                    "/// 库依赖  : Standard",
                    "{attribute 'hide_all_locals'}",
                    "FUNCTION_BLOCK FB_MotorController",
                    "// === IMPLEMENTATION ===",
                    "/// =======================================================================",
                    "/// 名称      : FB_MotorController",
                    "/// 功能      : 电机控制",
                    "/// 库依赖    : Standard",
                    "/// 使用说明  : Method、Action、Property 聚合在父 FB mirror 文件内。",
                    "/// =======================================================================",
                    "// === PROPERTY P_TargetSpeed ===",
                    "PROPERTY PUBLIC P_TargetSpeed : INT",
                    "// === GET ===",
                    "// === IMPLEMENTATION ===",
                    "P_TargetSpeed := iTargetSpeed;",
                    "// === SET ===",
                    "// === IMPLEMENTATION ===",
                    "iTargetSpeed := P_TargetSpeed;",
                ]
            ),
        )

        self.assertTrue(issues)
        self.assertTrue(any("must not include implementation markers inside GET/SET" in issue for issue in issues))

    def test_rejects_mirror_segment_name_with_wrong_prefix(self) -> None:
        issues = validate_file_content(
            {
                "path": "FB_MotorController.st",
                "family": "function_block",
            },
            "\n".join(
                [
                    "/// 功能    : 电机控制",
                    "/// 库依赖  : Standard",
                    "{attribute 'hide_all_locals'}",
                    "FUNCTION_BLOCK FB_MotorController",
                    "// === IMPLEMENTATION ===",
                    "/// =======================================================================",
                    "/// 名称      : FB_MotorController",
                    "/// 功能      : 电机控制",
                    "/// 库依赖    : Standard",
                    "/// 使用说明  : Method、Action、Property 聚合在父 FB mirror 文件内。",
                    "/// =======================================================================",
                    "// === METHOD Init ===",
                    "METHOD PUBLIC Init : BOOL",
                    "// === IMPLEMENTATION ===",
                    "Init := TRUE;",
                ]
            ),
        )

        self.assertTrue(issues)
        self.assertTrue(any("METHOD segment Init must use M_PascalCase" in issue for issue in issues))

    def test_rejects_forbidden_header_metadata(self) -> None:
        issues = validate_file_content(
            {
                "path": "FB_MotorController.st",
                "family": "function_block",
            },
            "\n".join(
                [
                    "/// 功能    : 电机控制",
                    "/// 库依赖  : 暂无",
                    "/// 编程人员: Someone",
                    "{attribute 'hide_all_locals'}",
                    "FUNCTION_BLOCK FB_MotorController",
                    "// === IMPLEMENTATION ===",
                ]
            ),
        )

        self.assertTrue(issues)
        self.assertTrue(any("file header must not include 编程人员" in issue for issue in issues))

    def test_rejects_program_hide_all_locals(self) -> None:
        issues = validate_file_content(
            {
                "path": "PRG_Main.st",
                "family": "program",
            },
            "{attribute 'hide_all_locals'}\nPROGRAM PRG_Main\n// === IMPLEMENTATION ===\n",
        )

        self.assertTrue(issues)
        self.assertTrue(any("PROGRAM must not include hide_all_locals" in issue for issue in issues))

    def test_rejects_duplicate_enum_values(self) -> None:
        issues = validate_file_content(
            {
                "path": "E_State.st",
                "family": "enum",
            },
            "\n".join(
                [
                    "{attribute 'qualified_only'}",
                    "{attribute 'strict'}",
                    "TYPE E_State :",
                    "(",
                    "    iIdle := 0,",
                    "    iInit := 0",
                    ");",
                    "END_TYPE",
                ]
            ),
        )

        self.assertTrue(issues)
        self.assertTrue(any("ENUM explicit values must be unique" in issue for issue in issues))

    def test_rejects_multiple_dut_definitions_in_one_file(self) -> None:
        issues = validate_file_content(
            {
                "path": "ST_Data.st",
                "family": "struct",
            },
            "\n".join(
                [
                    "TYPE ST_Data :",
                    "STRUCT",
                    "END_STRUCT",
                    "END_TYPE",
                    "TYPE ST_Other :",
                    "STRUCT",
                    "END_STRUCT",
                    "END_TYPE",
                ]
            ),
        )

        self.assertTrue(issues)
        self.assertTrue(any("must contain exactly one DUT definition" in issue for issue in issues))

    def test_rejects_bare_physical_units_in_comments(self) -> None:
        issues = validate_file_content(
            {
                "path": "F_LimitSpeed.st",
                "family": "function",
            },
            "\n".join(
                [
                    "{attribute 'hide_all_locals'}",
                    "FUNCTION F_LimitSpeed : INT",
                    "VAR_INPUT",
                    "    iValue : INT; // 输入速度 rpm",
                    "END_VAR",
                    "// === IMPLEMENTATION ===",
                    "F_LimitSpeed := iValue;",
                ]
            ),
        )

        self.assertTrue(issues)
        self.assertTrue(any("physical units in comments must use [unit] format" in issue for issue in issues))

    def test_requires_library_dependency_header(self) -> None:
        issues = validate_file_content(
            {
                "path": "F_LimitSpeed.st",
                "family": "function",
            },
            "\n".join(
                [
                    "{attribute 'hide_all_locals'}",
                    "FUNCTION F_LimitSpeed : INT",
                    "// === IMPLEMENTATION ===",
                    "F_LimitSpeed := 0;",
                ]
            ),
        )

        self.assertTrue(issues)
        self.assertTrue(any("file header must include library dependency" in issue for issue in issues))

    def test_rejects_full_comment_block_before_implementation_marker(self) -> None:
        issues = validate_file_content(
            {
                "path": "FB_MotorController.st",
                "family": "function_block",
            },
            "\n".join(
                [
                    "/// 功能    : 电机控制",
                    "/// 库依赖  : Standard",
                    "{attribute 'hide_all_locals'}",
                    "FUNCTION_BLOCK FB_MotorController",
                    "/// =======================================================================",
                    "/// 名称      : FB_MotorController",
                    "/// =======================================================================",
                    "// === IMPLEMENTATION ===",
                ]
            ),
        )

        self.assertTrue(issues)
        self.assertTrue(any("must be placed after implementation marker" in issue for issue in issues))

    def test_rejects_code_before_full_comment_block_in_implementation(self) -> None:
        issues = validate_file_content(
            {
                "path": "PRG_Main.st",
                "family": "program",
            },
            "\n".join(
                [
                    "/// 功能    : 主程序",
                    "/// 库依赖  : Standard",
                    "PROGRAM PRG_Main",
                    "// === IMPLEMENTATION ===",
                    "GVL_System.bSystemReady := TRUE;",
                    "/// =======================================================================",
                    "/// 名称      : PRG_Main",
                    "/// =======================================================================",
                ]
            ),
        )

        self.assertTrue(issues)
        self.assertTrue(any("must be the first content after implementation marker" in issue for issue in issues))

    def test_rejects_full_comment_block_without_usage_notes(self) -> None:
        issues = validate_file_content(
            {
                "path": "FB_MotorController.st",
                "family": "function_block",
            },
            "\n".join(
                [
                    "/// 功能    : 电机控制",
                    "/// 库依赖  : Standard",
                    "{attribute 'hide_all_locals'}",
                    "FUNCTION_BLOCK FB_MotorController",
                    "// === IMPLEMENTATION ===",
                    "/// =======================================================================",
                    "/// 名称      : FB_MotorController",
                    "/// 功能      : 电机控制",
                    "/// 库依赖    : Standard",
                    "/// =======================================================================",
                ]
            ),
        )

        self.assertTrue(issues)
        self.assertTrue(any("must include 使用说明" in issue for issue in issues))

    def test_rejects_single_line_named_argument_call(self) -> None:
        issues = validate_file_content(
            {
                "path": "FB_MotorController.st",
                "family": "function_block",
            },
            "\n".join(
                [
                    "/// 功能    : 电机控制",
                    "/// 库依赖  : Standard",
                    "{attribute 'hide_all_locals'}",
                    "FUNCTION_BLOCK FB_MotorController",
                    "// === IMPLEMENTATION ===",
                    "/// =======================================================================",
                    "/// 名称      : FB_MotorController",
                    "/// =======================================================================",
                    "tonStartTimeout(IN := FALSE, PT := T#5s);",
                ]
            ),
        )

        self.assertTrue(issues)
        self.assertTrue(any("each pin on its own line" in issue for issue in issues))

    def test_rejects_unrecognized_library_dependency_header(self) -> None:
        issues = validate_file_content(
            {
                "path": "GVL_System.st",
                "family": "gvl",
            },
            "\n".join(
                [
                    "/// 功能    : 系统变量",
                    "/// 库依赖  : UnknownLib",
                    "{attribute 'qualified_only'}",
                    "VAR_GLOBAL",
                    "END_VAR",
                ]
            ),
        )

        self.assertTrue(issues)
        self.assertTrue(any("known explicit library" in issue for issue in issues))

    def test_requires_logical_project_path(self) -> None:
        issues = validate_file_location(
            {
                "path": "FB_MotorController.st",
                "family": "function_block",
            }
        )

        self.assertTrue(issues)
        self.assertTrue(any("logical_path is required" in issue for issue in issues))

    def test_rejects_codesys_export_folder_as_logical_path(self) -> None:
        issues = validate_file_location(
            {
                "path": "E_State.st",
                "logical_path": "Device/Application/Data Types/E_State.st",
                "family": "enum",
            }
        )

        self.assertTrue(issues)
        self.assertTrue(any("not CODESYS export folders" in issue for issue in issues))

    def test_rejects_wrong_logical_folder_for_function(self) -> None:
        issues = validate_file_location(
            {
                "path": "F_LimitSpeed.st",
                "logical_path": "POUs/FBs/F_LimitSpeed.st",
                "family": "function",
            }
        )

        self.assertTrue(issues)
        self.assertTrue(any("under POUs/FCs/" in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()
