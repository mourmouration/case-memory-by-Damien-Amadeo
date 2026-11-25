# Case Memory

[![Tests](https://github.com/mourmouration/case-memory-by-Damien-Amadeo/actions/workflows/tests.yml/badge.svg)](https://github.com/mourmouration/case-memory-by-Damien-Amadeo/actions/workflows/tests.yml) [![License: CM-NCL 1.0](https://img.shields.io/badge/license-CM--NCL%201.0-blue)](LICENSE)

Persistent Markdown-based project and legal case memory for AI agents. Created by Damien Amadeo.

[Русская версия](README.ru.md) | [License](LICENSE)

Case Memory separates project knowledge from personal preferences and preserves decisions, sources, open questions and reusable lessons across sessions. The instructions and memory schema are primarily in Russian.

## Modes

| Mode | Purpose |
|---|---|
| SAVE | Record session outcomes and approved lessons |
| LOAD | Restore project context |
| RECALL | Search lessons and positions across projects |
| COMPRESS | Prepare a session summary for continuity |
| CONSOLIDATE | Review and organize accumulated memory |

## Installation

Download the repository ZIP from [GitHub (Code > Download ZIP)](https://github.com/mourmouration/case-memory-by-Damien-Amadeo/archive/refs/heads/main.zip), extract it and copy the complete `case-memory` folder (including SKILL.md, references and scripts) into the agent's skills directory. Rename the extracted folder to `case-memory` if necessary.

- Claude Code: `~/.claude/skills/case-memory/` (personal) or `.claude/skills/case-memory/` (project).
- Codex: `.agents/skills/case-memory/` in the project. Restart or reload the agent if needed.
- Claude web/desktop: where custom skill upload is supported, upload a ZIP containing the skill folder. Persistent project storage must be available separately.
- Other agents: use their Agent Skills installation mechanism or explicitly ask the agent to read SKILL.md and its referenced files.

These are intended integration paths, not a claim of tested compatibility with every client. Python 3.8+ is recommended for the read-only helper; no third-party Python packages are required.

## Usage

Open an authorized working folder and ask the agent to use case-memory SAVE or LOAD. Confirm creation of `0.3. Memory/` when prompted. Keep using the same persistent working folder across sessions. COMPRESS creates a summary; it does not shrink the current model context.

Run helper tests from the repository root: `python -m unittest discover -s tests`.

## Privacy

Keep actual case files and memory outside the public repository. The helper does not write files or use the network; the agent itself may read and write files through its authorized tools. Do not upload confidential records to an unapproved service. Review staged files before every commit; .gitignore is not a security boundary.

## License

Source available, not open source. Free personal non-commercial use only under [CM-NCL 1.0](LICENSE). Organizations require a paid written license; commercial use requires written permission. Resale and distribution of modified versions are prohibited under the public license. Authorized derivative products must credit the author. Commercial licensing: damienamadeo@gmail.com.
