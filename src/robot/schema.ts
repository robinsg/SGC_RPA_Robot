import { z } from 'zod';

export const ActionSchema = z.discriminatedUnion('type', [
  z.object({
    type: z.literal('send_text'),
    text: z.string(),
    description: z.string().optional(),
  }),
  z.object({
    type: z.literal('send_key'),
    key: z.string(), // e.g., 'Enter', 'F3', 'Tab'
    description: z.string().optional(),
  }),
  z.object({
    type: z.literal('wait_for_text'),
    text: z.string(),
    row: z.number().optional(),
    col: z.number().optional(),
    end_row: z.number().optional(),
    end_col: z.number().optional(),
    is_message_line: z.boolean().optional(),
    timeout_seconds: z.number().default(10),
    description: z.string().optional(),
  }),
  z.object({
    type: z.literal('sleep'),
    seconds: z.number(),
    description: z.string().optional(),
  }),
  z.object({
    type: z.literal('capture'),
    filename: z.string().optional(),
    description: z.string().optional(),
  }),
  z.object({
    type: z.literal('press_key_if_text_present'),
    text: z.string(),
    key: z.string(),
    row: z.number().optional(),
    col: z.number().optional(),
    end_row: z.number().optional(),
    end_col: z.number().optional(),
    is_message_line: z.boolean().optional(),
    wait_ms: z.number().optional(),
    timeout_seconds: z.number().default(2),
    description: z.string().optional(),
  })
]);

export const RobotScriptSchema = z.object({
  name: z.string(),
  description: z.string().optional(),
  tmux_session: z.string().default('5250_robot'),
  defaults: z.object({
    wait_timeout: z.number().default(5),
    typing_delay_ms: z.number().default(50),
  }).optional(),
  steps: z.array(ActionSchema),
});

export type RobotAction = z.infer<typeof ActionSchema>;
export type RobotScript = z.infer<typeof RobotScriptSchema>;
