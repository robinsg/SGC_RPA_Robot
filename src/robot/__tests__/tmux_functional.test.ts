import { execSync } from 'child_process';
import * as path from 'path';
import { fileURLToPath } from 'url';
import { KEY_MAP } from '../engine';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function testTmuxFunctional() {
  const keysToTest = [
    { key: 'Enter', expectedPattern: /DONE/ }, // Enter (C-m) might be invisible or consumed, but sentinel DONE follows
    { key: 'F1', expectedPattern: /\^\[OP/ },
    { key: 'F13', expectedPattern: /\^\[\[1;2P/ },
    { key: 'Page_up', expectedPattern: /\^\[\[5~/ },
    { key: 'Page_down', expectedPattern: /\^\[\[6~/ }
  ];

  console.log('Running Tmux Functional Tests...');
  let passed = 0;
  let failed = 0;

  for (const item of keysToTest) {
    const { key, expectedPattern } = item;
    const tmuxKey = KEY_MAP[key];
    console.log(`Testing key: ${key} (tmux: ${tmuxKey})`);

    try {
      const helperPath = path.join(__dirname, 'helpers', 'tmux_tester.py');
      const output = execSync(`python3 "${helperPath}" ${tmuxKey}`, { encoding: 'utf-8' }).trim();

      if (expectedPattern.test(output)) {
        console.log(`✅ [PASS] ${key} produced expected output matching ${expectedPattern}`);
        passed++;
      } else {
        console.error(`❌ [FAIL] ${key} produced unexpected output: ${output}`);
        failed++;
      }
    } catch (error: any) {
      console.error(`❌ [ERROR] Failed to test ${key}: ${error.message}`);
      failed++;
    }
  }

  console.log(`\nTmux Functional Results: ${passed} passed, ${failed} failed`);
  if (failed > 0) {
    process.exit(1);
  }
}

testTmuxFunctional();
