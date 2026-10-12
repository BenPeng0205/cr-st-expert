# cr-st-expert

**English** | [简体中文](README.zh-CN.md)

### Give your AI assistant a consistent engineering rulebook for CODESYS Structured Text.

`cr-st-expert` is a standalone programming-guidelines skill for writing, modifying, and reviewing CODESYS ST code. It packages reusable engineering conventions, selected platform-specific rules, templates, and examples so you can apply the same expectations across coding tasks.

The goal is practical: clearer names, better interfaces, meaningful comments, predictable state handling, and reviews that explain what needs attention. You still define the requirements and check the result.

**The skill is not a compiler. It can help reduce mistakes; it does not guarantee error-free code or correct machine behavior.**

## What it brings to your workflow

An AI assistant may know general IEC 61131-3 syntax yet overlook a CODESYS-specific restriction or mix conventions from different platforms. Even valid ST can be difficult to maintain when names, comments, interfaces, and call patterns vary from one task to the next.

This skill gives the assistant a written basis for its work. Instead of repeating every convention in every prompt, ask it to use `cr-st-expert`, provide your requirements or code, and review its changes against the same rules.

| Area | Rules and checks | Why it matters |
| --- | --- | --- |
| Naming and interfaces | PascalCase object names; Hungarian-style variable prefixes; input defaults; units and interface semantics | Identify types, responsibilities, and expected inputs without guessing |
| Comments and formatting | Four-space indentation; aligned declarations and named arguments; comments explaining conditions and constraints | Make code easier to read, compare, and hand over |
| Object organization | Single responsibility; deliberate FB, FUNCTION, and PROGRAM selection; object-to-file conventions | Find the right place to change code and reuse suitable components |
| Types and calculations | Explicit conversions; range checks; floating-point tolerances; division guards | Expose assumptions that otherwise surface during debugging |
| Scan-cycle behavior | Stable calls to stateful instances; suitable instance lifetime; trigger and timer usage | Check how state changes when inputs change across scans |
| States and diagnostics | Qualified, strict enums; CASE fallback; diagnostic context; reset boundaries | Explain which state failed and why |
| Boundaries and shared data | Array and string limits; pointer constraints; shared-data ownership and synchronization checks | Identify unsafe access and unclear task interactions |
| Dependencies and review scope | Actual library identifiers; unknown versions marked for confirmation; findings with locations and reasons | Keep unverified assumptions visible |

These rules combine project conventions with standard-language practices and selected CODESYS extensions. They are not an official IEC certification or a universal vendor coding standard. For example, `BOOL_TO_INT` follows a standard conversion form; it should not be presented as a CODESYS-only feature. CODESYS documents `AND_THEN` as an IEC extension.

## Install once, then confirm it is loaded

1. Download the repository or the [standalone ZIP](https://github.com/BenPeng0205/cr-st-expert/raw/refs/heads/main/downloads/cr-st-expert-4.0.0-standalone.zip).
2. Keep the complete folder and name it `cr-st-expert`. `SKILL.md` must be directly inside it, alongside the supporting directories.
3. Place it in the skill directory supported by your assistant. For Codex, current documentation lists `~/.agents/skills` for personal skills and `.agents/skills` for repository skills. If your installation uses another recognized location, follow its configuration rather than installing duplicate copies.
4. Refresh skill discovery or start a new session, then explicitly ask the assistant to load `cr-st-expert` and its referenced rules.

**Basic use requires no Python, CODESYS IDE, CLI, graph service, companion skill, or external memory service.** It does require an AI assistant that can discover the skill and read its supporting files.

See the [deployment guide](deploy/README.md) for installation, upgrades, and removal, and the [official Codex customization documentation](https://learn.chatgpt.com/docs/customization/overview) for current skill locations.

The entry point and detailed rule resources are currently mostly in Chinese. The English homepage introduces the product; it is not a complete English localization of the rule library. You can request an English response from an assistant capable of reading those resources.

## Three ways to use it

**Write a new component**

> Use cr-st-expert to write a CODESYS ST function block for [requirements]. The inputs, outputs, and operating conditions are [details]. Explain missing information before making assumptions. Respond in English.

**Modify existing code**

> Use cr-st-expert to improve this ST code. Preserve the public interfaces and intended behavior. Explain each change, and propose behavior changes separately before applying them.

**Review without editing**

> Review this ST code using cr-st-expert. Report the location, reason, and suggested fix for each finding. Do not edit the code. List anything that cannot be confirmed from the supplied files.

For an existing project, agree on interface compatibility and project conventions first. A review of a snippet cannot establish that the whole project is correct.

## What it does not do

- It does not create or write IDE projects, compile, simulate, connect to devices, or download programs.
- It does not supply complete motion-control, communication, or other domain-library API knowledge. Provide the actual library documentation when those interfaces matter.
- It does not prove that a library is installed, a signature is correct, or a control sequence is safe.
- It does not automatically upload code or record external memory. Your AI assistant's own data handling still applies.

Review the proposed changes, compile in the target environment, and test the required behavior separately.

## Optional static checks

The bundled scripts are optional. They use the Python standard library and require Python 3.10 or later. From the skill folder:

```sh
python -X utf8 scripts/st_semantic_linter.py --root <st-source-directory> --strict --output <report.json>
python -X utf8 scripts/protocol_validator.py
```

The linter checks the rules it implements; other rules still require review. The protocol validator checks the included text examples. Neither is a CODESYS compiler.

The bundled `codesys_st_text_v1` layout is a text-exchange convention, not a native IDE project or a guarantee of direct import. It groups Method, Action, and Property sections with their parent FB. Existing projects can retain their native organization.

## Repository contents

- `SKILL.md`: entry point, workflow, and boundaries.
- `references/`, `rules/`: detailed programming guidelines.
- `templates/`, `examples/`: reusable starting points and illustrative samples.
- `scripts/`: optional planning, checking, and package-building utilities.
- `test/`, `evals/`: maintainer tests and evaluation cases.
- `deploy/`, `docs/`: installation and public product contracts.
- `downloads/`: the standalone installation archive and its hash manifest.

## Validation and contributions

Repository checks and local artifact testing do not establish compatibility with every computer, assistant, compiler, or target device. Independent clean-machine acceptance is not complete; the package metadata retains `NOT_RELEASE_ELIGIBLE`. This publication shares the source and rule resources without claiming a validated production release.

To run the maintainer tests:

```sh
python -m unittest discover -s test -p "test_*.py"
python -X utf8 scripts/public_asset_guard.py
```

Feedback is especially useful when it includes a small reproducible example, the expected behavior, the relevant rule, and the platform or compiler version when applicable. Remove credentials, device addresses, and proprietary project data before sharing.

## License

[MIT](LICENSE). Third-party product names are used for identification. This repository does not redistribute third-party libraries or imply vendor endorsement.
