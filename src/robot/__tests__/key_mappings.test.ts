import { KEY_MAP } from '../engine';

function testKeyMappings() {
  const expectedKeys = [
    'Enter', 'Field_exit', 'Reset', 'Tab',
    'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12',
    'F13', 'F14', 'F15', 'F16', 'F17', 'F18', 'F19', 'F20', 'F21', 'F22', 'F23', 'F24',
    'Page_up', 'Page_down', 'Print', 'Help'
  ];

  console.log('Testing 5250 Key Mappings...');
  let passed = 0;
  let failed = 0;

  for (const key of expectedKeys) {
    if (KEY_MAP[key]) {
      console.log(`✅ [PASS] ${key} -> ${KEY_MAP[key]}`);
      passed++;
    } else {
      console.error(`❌ [FAIL] Missing mapping for key: ${key}`);
      failed++;
    }
  }

  // Specific value checks
  const specificChecks = [
    { key: 'Enter', expected: 'C-m' },
    { key: 'F13', expected: 'S-F1' },
    { key: 'Page_up', expected: 'PPage' },
    { key: 'Page_down', expected: 'NPage' },
    { key: 'Help', expected: 'S-F1' }
  ];

  for (const check of specificChecks) {
    if (KEY_MAP[check.key] === check.expected) {
      console.log(`✅ [PASS] ${check.key} correctly mapped to ${check.expected}`);
      passed++;
    } else {
      console.error(`❌ [FAIL] ${check.key} mapped to ${KEY_MAP[check.key]}, expected ${check.expected}`);
      failed++;
    }
  }

  console.log(`\nResults: ${passed} passed, ${failed} failed`);
  if (failed > 0) {
    process.exit(1);
  }
}

testKeyMappings();
