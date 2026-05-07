import { RobotEngine } from './engine';
import * as path from 'path';

async function main() {
  const yamlArg = process.argv[2];
  if (!yamlArg) {
    console.error('Usage: npx tsx src/robot/cli.ts <path_to_yaml>');
    process.exit(1);
  }

  try {
    const yamlPath = path.resolve(process.cwd(), yamlArg);
    const engine = new RobotEngine(yamlPath);
    await engine.run();
  } catch (error: any) {
    console.error(`Error: ${error.message}`);
    process.exit(1);
  }
}

main();
