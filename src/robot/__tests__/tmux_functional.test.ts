import { describe, it, expect } from 'vitest';
import { execSync } from 'child_process';
import * as path from 'path';
import { fileURLToPath } from 'url';
import { KEY_MAP } from '../engine';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

describe('Tmux Functional Keys', () => {
  const keysToTest = [
    { key: 'Enter', expectedPattern: /DONE/ },
    { key: 'F1', expectedPattern: /\^\[OP/ },
    { key: 'F13', expectedPattern: /\^\[\[1;2P/ },
    { key: 'Page_up', expectedPattern: /\^\[\[5~/ },
    { key: 'Page_down', expectedPattern: /\^\[\[6~/ }
  ];

  it.each(keysToTest)('should produce expected escape sequence for $key', ({ key, expectedPattern }) => {
    const tmuxKey = KEY_MAP[key];
    const helperPath = path.join(__dirname, 'helpers', 'tmux_tester.py');

    const output = execSync(`python3 "${helperPath}" ${tmuxKey}`, { encoding: 'utf-8' }).trim();

    expect(output).toMatch(expectedPattern);
  });
});
