const userService = require('../services/user.service');

exports.list = async (req, res, next) => {
  try {
    res.json({ success: true, data: await userService.list() });
  } catch (err) {
    next(err);
  }
};

exports.create = async (req, res, next) => {
  try {
    res.status(201).json({ success: true, data: await userService.create(req.body) });
  } catch (err) {
    next(err);
  }
};
