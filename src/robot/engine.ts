import { execSync } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import * as yaml from 'js-yaml';
import { RobotScript, RobotScriptSchema } from './schema';

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
    this.session = this.script.tmux_session;
    this.host = process.env.TN5250_HOST || 'unknown_host';
  }

  private runTmux(args: string[]): string {
    try {
      return execSync(`tmux ${args.join(' ')}`).toString();
    } catch (error: any) {
      // If session doesn't exist and we're not trying to create it, that might be an error
      if (error.message.includes('can\'t find session')) {
        throw new Error(`Tmux session '${this.session}' not found. Please start it first.`);
      }
      throw error;
    }
  }

  private checkSessionExists(): boolean {
    try {
      execSync(`tmux has-session -t ${this.session} 2>/dev/null`);
      return true;
    } catch {
      return false;
    }
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
          this.runTmux(['send-keys', '-t', this.session, `"${step.text}"`]);
          break;
        case 'send_key':
          this.runTmux(['send-keys', '-t', this.session, step.key]);
          break;
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
          console.log(`[Capture] Saved to ${savePath}`);
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
            console.log(`[Condition] Text "${step.text}" found. Sending key: ${step.key}`);
            this.runTmux(['send-keys', '-t', this.session, step.key]);
          } else {
            console.log(`[Condition] Text "${step.text}" not found. Skipping.`);
          }
          break;
      }
    }

    console.log('Automation complete!');
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
}
