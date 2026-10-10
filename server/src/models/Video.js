const { Schema, model } = require('mongoose');

const topicSchema = new Schema(
  {
    name: { type: String, required: true },
    startSec: { type: Number, required: true, min: 0 },
    endSec: Number,
    keywords: [String],
  },
  { _id: false }
);

const videoSchema = new Schema(
  {
    videoId: { type: String, required: true, unique: true, trim: true },
    title: { type: String, default: '' },
    durationSec: Number,
    views: Number,
    // time-aligned topics, e.g. from the Knowledge Extraction / Fusion components
    topics: [topicSchema],
    // audience retention curve: percentage of viewers still watching at `second`
    retention: [new Schema({ second: Number, pct: Number }, { _id: false })],
    // affective audio signals from the Affective Audio component
    audioSignals: [
      new Schema(
        { startSec: Number, endSec: Number, emotion: String, intensity: { type: Number, min: 0, max: 1 } },
        { _id: false }
      ),
    ],
  },
  { timestamps: true }
);

module.exports = model('Video', videoSchema);
