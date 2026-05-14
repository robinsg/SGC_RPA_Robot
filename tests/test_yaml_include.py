import pytest
import os
from robot_py.schema import parse_robot_script, SendTextAction, SendKeyAction

def test_yaml_include_basic(tmp_path):
    # Create an included file
    included_content = """
- type: send_text
  text: "included text"
"""
    included_file = tmp_path / "included.yaml"
    included_file.write_text(included_content)

    # Create main file
    main_content = """
name: Main Robot
steps:
  - !include included.yaml
  - type: send_key
    key: Enter
"""
    main_file = tmp_path / "main.yaml"
    main_file.write_text(main_content)

    script = parse_robot_script(str(main_file))

    assert len(script.steps) == 2
    assert isinstance(script.steps[0], SendTextAction)
    assert script.steps[0].text == "included text"
    assert isinstance(script.steps[1], SendKeyAction)
    assert script.steps[1].key == "Enter"

def test_yaml_include_recursive(tmp_path):
    # Create second level inclusion
    level2_content = """
- type: send_text
  text: "level 2"
"""
    level2_file = tmp_path / "level2.yaml"
    level2_file.write_text(level2_content)

    # Create first level inclusion
    level1_content = """
- !include level2.yaml
- type: send_text
  text: "level 1"
"""
    level1_file = tmp_path / "level1.yaml"
    level1_file.write_text(level1_content)

    # Create main file
    main_content = """
name: Recursive Robot
steps:
  - !include level1.yaml
"""
    main_file = tmp_path / "main.yaml"
    main_file.write_text(main_content)

    script = parse_robot_script(str(main_file))

    assert len(script.steps) == 2
    assert script.steps[0].text == "level 2"
    assert script.steps[1].text == "level 1"

def test_yaml_include_with_env_vars(tmp_path, monkeypatch):
    monkeypatch.setenv("INCLUDED_VAR", "from_env")

    included_content = """
- type: send_text
  text: "${INCLUDED_VAR}"
"""
    included_file = tmp_path / "included.yaml"
    included_file.write_text(included_content)

    main_content = """
name: Env Robot
steps:
  - !include included.yaml
"""
    main_file = tmp_path / "main.yaml"
    main_file.write_text(main_content)

    script = parse_robot_script(str(main_file))
    assert script.steps[0].text == "from_env"

def test_yaml_top_level_include_inheritance(tmp_path):
    # Base configuration
    base_content = """
tmux_session: base_session
defaults:
  wait_timeout: 20
  typing_delay_ms: 100
"""
    base_file = tmp_path / "base.yaml"
    base_file.write_text(base_content)

    # LPAR-specific file inheriting and overriding
    lpar_content = """
include: base.yaml
name: Overriding Robot
defaults:
  wait_timeout: 30
steps: []
"""
    lpar_file = tmp_path / "lpar.yaml"
    lpar_file.write_text(lpar_content)

    script = parse_robot_script(str(lpar_file))

    assert script.name == "Overriding Robot"
    assert script.tmux_session == "base_session"
    assert script.defaults.wait_timeout == 30  # Overridden
    assert script.defaults.typing_delay_ms == 100  # Inherited

def test_yaml_include_subdir(tmp_path):
    subdir = tmp_path / "shared"
    subdir.mkdir()

    included_content = """
- type: send_text
  text: "subdir text"
"""
    included_file = subdir / "common.yaml"
    included_file.write_text(included_content)

    main_content = """
name: Subdir Robot
steps:
  - !include shared/common.yaml
"""
    main_file = tmp_path / "main.yaml"
    main_file.write_text(main_content)

    script = parse_robot_script(str(main_file))
    assert script.steps[0].text == "subdir text"
