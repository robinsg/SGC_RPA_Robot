import os
import unittest
import yaml
from robot_py.schema import parse_robot_script, RobotScript, SendTextAction, WaitForTextAction

class TestYamlInclude(unittest.TestCase):
    def setUp(self):
        # Create temporary YAML files for testing
        with open('test_base.yaml', 'w') as f:
            f.write("""
tmux_session: "base_session"
defaults:
  wait_timeout: 20
steps:
  - type: "wait_for_text"
    text: "Base Start"
""")
        with open('test_include.yaml', 'w') as f:
            f.write("""
- type: "send_text"
  text: "Included Text"
- type: "send_key"
  key: "Enter"
""")
        with open('test_child.yaml', 'w') as f:
            f.write("""
include: test_base.yaml
name: "Child Robot"
defaults:
  typing_delay_ms: 150
steps:
  - !include test_include.yaml
  - type: "send_text"
    text: "Child Text"
""")

    def tearDown(self):
        for f in ['test_base.yaml', 'test_include.yaml', 'test_child.yaml']:
            if os.path.exists(f):
                os.remove(f)

    def test_full_features(self):
        script = parse_robot_script('test_child.yaml')

        self.assertEqual(script.name, "Child Robot")
        self.assertEqual(script.tmux_session, "base_session")
        self.assertEqual(script.defaults.wait_timeout, 20)
        self.assertEqual(script.defaults.typing_delay_ms, 150)

        # Steps should be:
        # 1. Included Text (from test_include.yaml)
        # 2. Enter (from test_include.yaml)
        # 3. Child Text (from test_child.yaml)
        # Note: test_base.yaml steps are OVERRIDDEN because child has its own steps.

        self.assertEqual(len(script.steps), 3)
        self.assertEqual(script.steps[0].type, "send_text")
        self.assertEqual(script.steps[0].text, "Included Text")
        self.assertEqual(script.steps[1].type, "send_key")
        self.assertEqual(script.steps[1].key, "Enter")
        self.assertEqual(script.steps[2].type, "send_text")
        self.assertEqual(script.steps[2].text, "Child Text")

    def test_env_substitution(self):
        os.environ['TEST_USER'] = 'testuser'
        with open('test_env.yaml', 'w') as f:
            f.write("""
- type: "send_text"
  text: "${TEST_USER}"
- type: "send_text"
  text: "${TEST_NONEXISTENT:-default_val}"
""")

        with open('test_main_env.yaml', 'w') as f:
            f.write("""
name: "Env Test"
steps:
  - !include test_env.yaml
""")

        try:
            script = parse_robot_script('test_main_env.yaml')
            self.assertEqual(script.steps[0].text, "testuser")
            self.assertEqual(script.steps[1].text, "default_val")
        finally:
            for f in ['test_env.yaml', 'test_main_env.yaml']:
                if os.path.exists(f):
                    os.remove(f)

if __name__ == '__main__':
    unittest.main()
