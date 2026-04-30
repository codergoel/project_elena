# Agent Skills (Deep Agents)

Each **skill** is a subdirectory with a required **`SKILL.md`** (YAML frontmatter + instructions), per the [Agent Skills spec](https://agentskills.io/specification).

Optional folders:

- `scripts/` — runnable helpers
- `references/` — extra docs loaded on demand
- `assets/` — templates, static files

At runtime, paths are passed to `create_deep_agent(skills=["/path/to/skills/"])` or bundled with the deployment; keep this folder as the **repo source of truth** for Elena-specific skills.

Example (future):

```text
skills/
├── jake-resume/
│   └── SKILL.md
└── one-page-fit/
    └── SKILL.md
```
