const { Schema, model } = require('mongoose');

const userSchema = new Schema(
  {
    name: { type: String, required: true, trim: true, maxlength: 100 },
    email: { type: String, required: true, unique: true, lowercase: true, trim: true },
    googleId: { type: String, index: true, sparse: true },
    role: { type: String, enum: ['user', 'admin'], default: 'user' },
  },
  { timestamps: true }
);

module.exports = model('User', userSchema);
