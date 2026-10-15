const { Schema, model } = require('mongoose');

const feedbackAnalysisSchema = new Schema(
  {
    videoIds: { type: [String], index: true },
    analyzer: String, // llm | lexicon
    result: Schema.Types.Mixed, // the JSON output contract
  },
  { timestamps: true }
);

module.exports = model('FeedbackAnalysis', feedbackAnalysisSchema);
