from robot_py.schema import parse_robot_script, SendTextAction, WaitForTextAction


def test_parse_robot_script_with_include(tmp_path):
    common_yaml = tmp_path / "common.yaml"
    common_yaml.write_text("""
- type: wait_for_text
  text: "Login"
- type: send_text
  text: "user"
""")

    main_yaml = tmp_path / "main.yaml"
    main_yaml.write_text(f"""
name: Main Robot
steps:
  - !include {common_yaml.name}
  - type: send_text
    text: "password"
""")

    script = parse_robot_script(str(main_yaml))

    assert len(script.steps) == 3
    assert isinstance(script.steps[0], WaitForTextAction)
    assert script.steps[0].text == "Login"
    assert isinstance(script.steps[1], SendTextAction)
    assert script.steps[1].text == "user"
    assert isinstance(script.steps[2], SendTextAction)
    assert script.steps[2].text == "password"


def test_nested_include(tmp_path):
    inner_yaml = tmp_path / "inner.yaml"
    inner_yaml.write_text("""
- type: send_text
  text: "inner"
""")

    outer_yaml = tmp_path / "outer.yaml"
    outer_yaml.write_text("""
- type: wait_for_text
  text: "outer"
- !include inner.yaml
""")

    main_yaml = tmp_path / "main.yaml"
    main_yaml.write_text("""
name: Nested Include Robot
steps:
  - !include outer.yaml
""")

    script = parse_robot_script(str(main_yaml))
    assert len(script.steps) == 2
    assert script.steps[0].text == "outer"
    assert script.steps[1].text == "inner"


def test_include_env_substitution(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_USER", "robot_user")

    common_yaml = tmp_path / "common.yaml"
    common_yaml.write_text("""
- type: send_text
  text: "${TEST_USER}"
""")

    main_yaml = tmp_path / "main.yaml"
    main_yaml.write_text("""
name: Env Robot
steps:
  - !include common.yaml
""")

    script = parse_robot_script(str(main_yaml))
    assert script.steps[0].text == "robot_user"


def test_top_level_include_inheritance(tmp_path):
    parent_yaml = tmp_path / "parent.yaml"
    parent_yaml.write_text("""
name: Parent Robot
defaults:
  wait_timeout: 30
steps:
  - type: wait_for_text
    text: "Parent Step"
""")

    child_yaml = tmp_path / "child.yaml"
    child_yaml.write_text("""
include: parent.yaml
name: Child Robot
steps:
  - type: send_text
    text: "Child Step"
""")

    script = parse_robot_script(str(child_yaml))
    assert script.name == "Child Robot"
    assert script.defaults.wait_timeout == 30
    assert len(script.steps) == 2
    assert script.steps[0].text == "Parent Step"
    assert script.steps[1].text == "Child Step"


def test_relative_include_resolution(tmp_path):
    subdir = tmp_path / "subdir"
    subdir.mkdir()

    common_yaml = subdir / "common.yaml"
    common_yaml.write_text("""
- type: send_text
  text: "subdir_text"
""")

    main_yaml = subdir / "main.yaml"
    main_yaml.write_text("""
name: Subdir Robot
steps:
  - !include common.yaml
""")

    # Even if we parse from a different CWD, it should resolve relatively
    script = parse_robot_script(str(main_yaml))
    assert script.steps[0].text == "subdir_text"
