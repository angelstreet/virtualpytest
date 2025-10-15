/**
 * Cron Utilities
 * Functions for validating and working with cron expressions
 */

/**
 * Validate cron expression format (basic validation)
 */
export function validateCronExpression(cron: string): { valid: boolean; error?: string } {
  if (!cron || !cron.trim()) {
    return { valid: false, error: 'Cron expression is required' };
  }
  
  const parts = cron.trim().split(/\s+/);
  if (parts.length !== 5) {
    return { valid: false, error: 'Cron must have 5 parts: minute hour day month day_of_week' };
  }
  
  const [minute, hour, day, month, dayOfWeek] = parts;
  
  // Basic validation for each part
  const validations = [
    { part: minute, name: 'minute', min: 0, max: 59 },
    { part: hour, name: 'hour', min: 0, max: 23 },
    { part: day, name: 'day', min: 1, max: 31 },
    { part: month, name: 'month', min: 1, max: 12 },
    { part: dayOfWeek, name: 'day_of_week', min: 0, max: 6 },
  ];
  
  for (const { part, name, min, max } of validations) {
    if (!isValidCronPart(part, min, max)) {
      return { valid: false, error: `Invalid ${name}: ${part}` };
    }
  }
  
  return { valid: true };
}

/**
 * Check if a single cron part is valid
 */
function isValidCronPart(part: string, min: number, max: number): boolean {
  // Asterisk is always valid
  if (part === '*') return true;
  
  // Check for step values (*/5)
  if (part.startsWith('*/')) {
    const step = parseInt(part.substring(2));
    return !isNaN(step) && step > 0 && step <= max;
  }
  
  // Check for ranges (1-5)
  if (part.includes('-')) {
    const [start, end] = part.split('-').map(n => parseInt(n));
    return !isNaN(start) && !isNaN(end) && start >= min && end <= max && start <= end;
  }
  
  // Check for lists (1,2,3)
  if (part.includes(',')) {
    const numbers = part.split(',').map(n => parseInt(n));
    return numbers.every(n => !isNaN(n) && n >= min && n <= max);
  }
  
  // Check for specific number
  const num = parseInt(part);
  return !isNaN(num) && num >= min && num <= max;
}

/**
 * Convert cron expression to human-readable description
 */
export function cronToHuman(cron: string): string {
  const parts = cron.trim().split(/\s+/);
  if (parts.length !== 5) return 'Invalid cron expression';
  
  const [minute, hour, day, month, dayOfWeek] = parts;
  
  // Common patterns
  if (cron.match(/^\*\/\d+ \* \* \* \*$/)) {
    const mins = minute.substring(2);
    return `Every ${mins} minutes`;
  }
  
  if (cron === '0 * * * *') return 'Every hour';
  if (cron.match(/^0 \*\/\d+ \* \* \*$/)) {
    const hrs = hour.substring(2);
    return `Every ${hrs} hours`;
  }
  
  if (cron.match(/^\d+ \d+ \* \* \*$/)) {
    return `Daily at ${hour}:${minute.padStart(2, '0')}`;
  }
  
  if (cron.match(/^\d+ \d+ \* \* [0-6]$/)) {
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    return `Weekly on ${days[parseInt(dayOfWeek)]} at ${hour}:${minute.padStart(2, '0')}`;
  }
  
  if (cron.match(/^\d+ \d+-\d+ \* \* \d-\d$/)) {
    return `Business hours (Mon-Fri, ${hour})`;
  }
  
  return `Cron: ${cron}`;
}

/**
 * Convert old schedule format to cron
 */
export function legacyToCron(
  scheduleType: string,
  scheduleConfig: { hour?: number; minute?: number; day?: number }
): string {
  const minute = scheduleConfig.minute || 0;
  const hour = scheduleConfig.hour || 0;
  const day = scheduleConfig.day || 0;
  
  switch (scheduleType) {
    case 'hourly':
      return `${minute} * * * *`;
    case 'daily':
      return `${minute} ${hour} * * *`;
    case 'weekly':
      return `${minute} ${hour} * * ${day}`;
    default:
      return '0 * * * *'; // default: every hour
  }
}

