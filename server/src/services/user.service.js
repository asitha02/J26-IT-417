const User = require('../models/User');

exports.list = () => User.find().lean();
exports.getById = (id) => User.findById(id).lean();
exports.create = (data) => User.create(data);
