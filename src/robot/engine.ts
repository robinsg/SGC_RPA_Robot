import { spawnSync } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import * as yaml from 'js-yaml';
import { RobotScript, RobotScriptSchema } from './schema';
import logger from './logger'; // <-- IMPORT THE NEW LOGGER

// A mapping from logical, human-readable key names to the specific
// key codes that tmux expects for a 5250 session.
const KEY_MAP: { [key: string]: string } = {
  'Enter': 'C-m',
  'Field_exit': 'C-f',
  'Reset': 'C-r',
  'Tab': 'Tab',
  'F1': 'F1', 'F2': 'F2', 'F3': 'F3', 'F4': 'F4',
  'F5': 'F5', 'F6': 'F6', 'F7': 'F7', 'F8': 'F8',
  'F9': 'F9', 'F10': 'F10', 'F11': 'F11', 'F12': 'F12',
  'F13': 'S-F1', 'F14': 'S-F2', 'F15': 'S-F3', 'F16': 'S-F4',
  'F17': 'S-F5', 'F18': 'S-F6', 'F19': 'S-F7', 'F20': 'S-F8',
  'F21': 'S-F9', 'F22': 'S-F10', 'F23': 'S-F11', 'F24': 'S-F12',
  'Page_up': 'PPage',   // Roll Up in 5250
  'Page_down': 'NPage', // Roll Down in 5250
  'Print': 'C-p',
  'Help': 'S-F1', // Often F13 is Help, mapping to S-F1
};

const logLevel = process.env.LOG_LEVEL || 'info';

export class RobotEngine {
  private script: RobotScript;
  private session: string;
  private host: string;

  constructor(yamlPath: string) {
    const fileContents = fs.readFileSync(yamlPath, 'utf8');
    const rawData = yaml.load(fileContents);
    
    // Process environment variables in the YAML strings
    const processedData = JSON.parse(
      JSON.stringify(rawData).replace(/\${(\w+)}/g, (_, name) => {
        return process.env[name] || '';
      })
    );

    this.script = RobotScriptSchema.parse(processedData);
    // Use the session name from the environment variable, falling back to the script's definition
    this.session = process.env.TMUX_SESSION || this.script.tmux_session;
    this.host = process.env.TN5250_HOST || 'unknown_host';
  }

  private runTmux(args: string[]): string {
    const result = spawnSync('tmux', args, { encoding: 'utf-8' });

    if (result.status !== 0) {
      // Provide a more detailed error message
      const errorOutput = result.stderr || result.stdout || 'No output';
      throw new Error(`Tmux command failed: [tmux ${args.join(' ')}]. Error: ${errorOutput.trim()}`);
    }
    
    return result.stdout;
  }

  private checkSessionExists(): boolean {
    const result = spawnSync('tmux', ['has-session', '-t', this.session]);
    // 'has-session' returns 0 if it exists, and a non-zero status if it doesn't.
    return result.status === 0;
  }

  async run() {
    console.log(`Starting Robot: ${this.script.name}`);
    console.log(`Description: ${this.script.description || 'N/A'}`);

    if (!this.checkSessionExists()) {
      console.log(`Error: Tmux session '${this.session}' not found.`);
      console.log(`Hint: Start your 5250 session in tmux: tmux new-session -s ${this.session} "tn5250 <host>"`);
      process.exit(1);
    }

    for (let i = 0; i < this.script.steps.length; i++) {
      const step = this.script.steps[i];
      const desc = step.description ? ` (${step.description})` : '';
      console.log(`[Step ${i + 1}/${this.script.steps.length}] ${step.type}${desc}`);

      switch (step.type) {
        case 'send_text':
          // Use the -l flag to send the text literally, preventing shell interpolation.
          this.runTmux(['send-keys', '-l', '-t', this.session, step.text]);
          break;
        case 'send_key': {
          // Look up the logical key name in our map to get the correct tmux code.
          const keyToSend = KEY_MAP[step.key] || step.key;
          logger.debug(`[Key Send] Sending key: '${step.key}' -> tmux: '${keyToSend}'`);

          if (step.key === 'Enter' && logLevel === 'debug') {
            const beforeContent = this.runTmux(['capture-pane', '-t', this.session, '-p']);
            logger.debug(`\n--- Before Enter ---\n${beforeContent}\n--- End Before Enter ---`);
          }

          // Keys are not sent literally.
          this.runTmux(['send-keys', '-t', this.session, keyToSend]);

          if (step.key === 'Enter' && logLevel === 'debug') {
            await new Promise(resolve => setTimeout(resolve, 250)); // Allow screen to settle
            const afterContent = this.runTmux(['capture-pane', '-t', this.session, '-p']);
            logger.debug(`\n--- After Enter ---\n${afterContent}\n--- End After Enter ---`);
          }

          await this.captureDebugScreen(`after_send_key_${step.key}`);
          break;
        }
        case 'sleep':
          await new Promise(resolve => setTimeout(resolve, step.seconds * 1000));
          break;
        case 'capture':
          const capture = this.runTmux(['capture-pane', '-t', this.session, '-p']);
          const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
          const hostDir = path.join(process.cwd(), 'captures', this.host);
          
          if (!fs.existsSync(hostDir)) {
            fs.mkdirSync(hostDir, { recursive: true });
          }

          const baseName = step.filename || 'capture';
          const finalFilename = `${baseName}_${timestamp}.txt`;
          const savePath = path.join(hostDir, finalFilename);
          
          fs.writeFileSync(savePath, capture);
          logger.info(`[Capture] Saved to ${savePath}`);
          break;
        case 'wait_for_text':
          await this.waitForText(
            step.text, 
            step.timeout_seconds, 
            step.row, 
            step.col, 
            step.end_row, 
            step.end_col, 
            step.is_message_line
          );
          await this.logScreenTitle();
          await this.captureDebugScreen(`after_wait_for_${step.text.replace(/\s+/g, '_')}`);
          break;
        case 'press_key_if_text_present':
          const paneContent = this.runTmux(['capture-pane', '-t', this.session, '-p']);
          if (this.findTextInBuffer(
            paneContent,
            step.text,
            step.row,
            step.col,
            step.end_row,
            step.end_col,
            step.is_message_line
          )) {
            const pressKey = KEY_MAP[step.key] || step.key;
            logger.info(`[Condition] Text "${step.text}" found. Sending key: ${step.key} -> tmux: ${pressKey}`);
            this.runTmux(['send-keys', '-t', this.session, pressKey]);
          } else {
            console.log(`[Condition] Text "${step.text}" not found. Skipping.`);
          }
          break;
      }
    }

    logger.info('Automation complete!');
  }

  private findTextInBuffer(
    paneContent: string,
    text: string,
    row?: number,
    col?: number,
    endRow?: number,
    endCol?: number,
    isMessageLine?: boolean
  ): boolean {
    const lines = paneContent.split('\n');

    if (isMessageLine) {
      const messageLineIndex = lines.length >= 27 ? 26 : 23;
      const line = lines[messageLineIndex] || '';
      return line.includes(text);
    } else if (row !== undefined && col !== undefined && endRow !== undefined && endCol !== undefined) {
      const searchArea = lines
        .slice(row - 1, endRow)
        .map(line => line.substring(col - 1, endCol))
        .join('\n');
      return searchArea.includes(text);
    } else if (row !== undefined) {
      const line = lines[row - 1] || '';
      if (col !== undefined) {
        return line.substring(col - 1).includes(text);
      } else {
        return line.includes(text);
      }
    } else {
      return paneContent.includes(text);
    }
  }

  private async waitForText(
    text: string, 
    timeout: number, 
    row?: number, 
    col?: number, 
    endRow?: number, 
    endCol?: number, 
    isMessageLine?: boolean
  ) {
    const startTime = Date.now();
    const expiry = startTime + (timeout * 1000);

    while (Date.now() < expiry) {
      const paneContent = this.runTmux(['capture-pane', '-t', this.session, '-p']);
      if (this.findTextInBuffer(paneContent, text, row, col, endRow, endCol, isMessageLine)) {
        return;
      }

      await new Promise(resolve => setTimeout(resolve, 500));
    }

    throw new Error(`Timeout waiting for text: "${text}"`);
  }

  private async logScreenTitle() {
    try {
      // Give the screen a brief moment to settle before capturing
      await new Promise(resolve => setTimeout(resolve, 250)); // 250ms delay
      const paneContent = this.runTmux(['capture-pane', '-t', this.session, '-p']);
      const lines = paneContent.split('\n');
      if (lines.length > 0) {
        const title = lines[0].trim();
        if (title) {
          logger.info(`[Screen] ${title}`);
        }
      }
    } catch (error: any) {
      logger.warn(`Could not capture screen title: ${error.message}`);
    }
  }

  // NEW: Automatic screen capture for debug mode
  private async captureDebugScreen(actionName: string) {
    if (logLevel !== 'debug') {
      return; // Only run in debug mode
    }
    try {
      // Short delay to ensure screen has settled after the action
      await new Promise(resolve => setTimeout(resolve, 250)); // 250ms delay
      const paneContent = this.runTmux(['capture-pane', '-t', this.session, '-p']);
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');

      const captureDir = path.join(process.cwd(), 'logs', 'captures', this.host);
      if (!fs.existsSync(captureDir)) {
        fs.mkdirSync(captureDir, { recursive: true });
      }

      const filename = `${timestamp}_${actionName}.txt`;
      const savePath = path.join(captureDir, filename);

      fs.writeFileSync(savePath, paneContent);
      logger.debug(`[Debug Capture] Screen saved to ${path.relative(process.cwd(), savePath)}`);
    } catch (error: any) {
      logger.warn(`[Debug Capture] Failed to capture screen: ${error.message}`);
    }
  }
}

