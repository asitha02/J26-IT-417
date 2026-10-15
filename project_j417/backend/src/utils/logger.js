const fmt = (level, args) => [`[${new Date().toISOString()}] ${level}:`, ...args];

module.exports = {
  info: (...a) => console.log(...fmt('INFO', a)),
  warn: (...a) => console.warn(...fmt('WARN', a)),
  error: (...a) => console.error(...fmt('ERROR', a)),
};
