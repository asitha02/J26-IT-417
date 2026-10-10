const logger = require('../utils/logger');

exports.notFound = (req, res) =>
  res.status(404).json({ success: false, message: `Not found: ${req.originalUrl}` });

// eslint-disable-next-line no-unused-vars
exports.errorHandler = (err, req, res, next) => {
  const status = err.name === 'ValidationError' ? 400 : err.status || 500;
  if (status >= 500) logger.error(err);
  res.status(status).json({
    success: false,
    message: status >= 500 ? 'Internal server error' : err.message,
  });
};
