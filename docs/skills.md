# Project-bundled Hermes skill

ShyftR ships a compact Hermes skill for agents and operators working in this repository.

Canonical skill file:

```text
adapters/hermes/skills/shyftr/SKILL.md
```

The skill is intentionally a routing and operating guide, not a duplicate of the full ShyftR documentation. It points agents to the current repo files for capability claims, command syntax, public/private boundaries, MCP/CLI surfaces, carry/continuity behavior, live context, verification gates, and release posture.

Local Hermes runtime installations may copy or sync this file to:

```text
~/.hermes/skills/software-development/shyftr/SKILL.md
```

Keep the repo-bundled skill as the canonical file. If the local runtime copy changes during development, sync it back here and verify the two files are byte-identical before committing.

Verification from the repository root:

```bash
python - <<'PY'
from pathlib import Path
import yaml
p = Path('adapters/hermes/skills/shyftr/SKILL.md')
text = p.read_text()
assert text.startswith('---\n')
frontmatter = text.split('---', 2)[1]
meta = yaml.safe_load(frontmatter)
assert meta['name'] == 'shyftr'
assert 'shyftr' in meta.get('tags', [])
print('skill-frontmatter-ok')
PY
cmp adapters/hermes/skills/shyftr/SKILL.md ~/.hermes/skills/software-development/shyftr/SKILL.md
```
