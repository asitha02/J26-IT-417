const { Schema, model } = require('mongoose');

const commentSchema = new Schema(
  {
    videoId: { type: String, required: true, index: true },
    commentId: { type: String, required: true },
    author: String,
    text: { type: String, required: true },
    cleanText: String,
    language: { type: String, enum: ['si', 'en', 'mixed', 'other'] },
    likeCount: { type: Number, default: 0 },
    publishedAt: Date,
    timestampSec: Number, // time reference found in the comment text, if any
    // analysis results
    analyzed: { type: Boolean, default: false },
    sentiment: { type: String, enum: ['positive', 'negative', 'neutral'] },
    emotions: [String],
    isQuestion: Boolean,
  },
  { timestamps: true }
);

commentSchema.index({ videoId: 1, commentId: 1 }, { unique: true });

module.exports = model('Comment', commentSchema);
