import { execSync } from 'child_process';
import * as path from 'path';
import { fileURLToPath } from 'url';
import { KEY_MAP } from '../engine';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function testTmuxFunctional() {
  const keysToTest = [
    'Enter',
    'F1',
    'F13',
    'Page_up',
    'Page_down'
  ];

  console.log('Running Tmux Functional Tests...');
  let passed = 0;
  let failed = 0;

  for (const key of keysToTest) {
    const tmuxKey = KEY_MAP[key];
    console.log(`Testing key: ${key} (tmux: ${tmuxKey})`);

    try {
      const helperPath = path.join(__dirname, 'helpers', 'tmux_tester.py');
      const output = execSync(`python3 "${helperPath}" ${tmuxKey}`, { encoding: 'utf-8' }).trim();

      // C-m (Enter) might result in an empty string if cat -v consumes it and nothing else is there,
      // but our tool sends Enter after the key.
      if (output.length > 0 || key === 'Enter') {
        console.log(`✅ [PASS] ${key} produced output: ${output || '(newline)'}`);
        passed++;
      } else {
        console.error(`❌ [FAIL] ${key} produced no output`);
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
