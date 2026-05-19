Cline rules directory

This directory contains modular rule files used in place of the single .clinerules file.

Files are YAML fragments describing rules; tools may merge them in lexicographic order. Suggested filenames:
- 5250.yaml
- yaml_actions.yaml
- python.yaml
- ci.yaml

Guidance:
- Keep each file focused on a single domain for easier review and ownership.
- Update .clinerules to point to this directory; leave .clinerules as a human-friendly pointer to the new layout.
