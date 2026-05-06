import { describe, it, expect } from 'vitest';
import { KEY_MAP } from '../engine';

describe('5250 Key Mappings', () => {
  const expectedKeys = [
    'Enter', 'Field_exit', 'Tab',
    'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12',
    'F13', 'F14', 'F15', 'F16', 'F17', 'F18', 'F19', 'F20', 'F21', 'F22', 'F23', 'F24',
    'Page_up', 'Page_down', 'Print'
  ];

  it('should have all expected 5250 keys mapped', () => {
    for (const key of expectedKeys) {
      expect(KEY_MAP[key], `Missing mapping for key: ${key}`).toBeDefined();
    }
  });

  it('should have correct mappings for core keys', () => {
    const specificChecks = [
      { key: 'Enter', expected: 'C-m' },
      { key: 'F13', expected: 'S-F1' },
      { key: 'Page_up', expected: 'PPage' },
      { key: 'Page_down', expected: 'NPage' }
    ];

    for (const check of specificChecks) {
      expect(KEY_MAP[check.key]).toBe(check.expected);
    }
  });
});
