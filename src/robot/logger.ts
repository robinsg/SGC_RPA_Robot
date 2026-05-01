import * as winston from 'winston';
import * as path from 'path';

// Get LPAR, Log Directory, and Log Level from environment variables
const lparName = process.env.TN5250_HOST || 'unknown-lpar';
const logDir = process.env.LOG_DIR || 'logs';
const logLevel = process.env.LOG_LEVEL || 'info'; // <-- Respect LOG_LEVEL
const logFile = path.join(logDir, `${lparName}.log`);

// Define our custom log format for the file
const fileFormat = winston.format.printf(({ timestamp, message }) => {
  // The format you requested: timestamp, lpar name, message
  return `${timestamp},${lparName},${message}`;
});

// Define a separate, more readable format for the console
const consoleFormat = winston.format.printf(({ timestamp, level, message }) => {
  return `${timestamp} ${level}: ${message}`;
});

// Create the logger instance
const logger = winston.createLogger({
  level: logLevel, // <-- Set the master log level here
  format: winston.format.combine(
    winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss.SSS' })
  ),
  transports: [
    // Transport 1: Log to a file with the custom CSV-like format
    new winston.transports.File({
      filename: logFile,
      format: fileFormat,
      // This transport will now correctly respect the master 'level'
    }),

    // Transport 2: Also log to the console with a more readable format
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        consoleFormat
      ),
    }),
  ],
});

export default logger;

