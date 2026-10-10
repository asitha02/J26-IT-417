// Usage: router.post('/', validate(zodSchema), ctrl.create)
module.exports = (schema) => (req, res, next) => {
  const result = schema.safeParse(req.body);
  if (!result.success) {
    return res.status(400).json({ success: false, message: 'Validation failed', errors: result.error.flatten() });
  }
  req.body = result.data;
  next();
};
