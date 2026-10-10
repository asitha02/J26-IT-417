const crypto = require('crypto');
const Video = require('../models/Video');
const Comment = require('../models/Comment');
const { cleanText, detectLanguage, extractTimestamp } = require('../utils/text');

exports.upsertVideo = (data) =>
  Video.findOneAndUpdate({ videoId: data.videoId }, { $set: data }, { new: true, upsert: true, runValidators: true });

exports.getVideo = (videoId) => Video.findOne({ videoId }).lean();
exports.listVideos = async () => {
  const [videos, counts] = await Promise.all([
    Video.find().select('-retention -audioSignals').sort({ updatedAt: -1 }).lean(),
    Comment.aggregate([{ $group: { _id: '$videoId', n: { $sum: 1 } } }]),
  ]);
  const byId = new Map(counts.map((c) => [c._id, c.n]));
  return videos.map((v) => ({ ...v, commentCount: byId.get(v.videoId) || 0 }));
};

/** Clean, language-tag and de-duplicate raw comments, then store them. */
exports.addComments = async (videoId, rawComments) => {
  const ops = [];
  for (const raw of rawComments) {
    const clean = cleanText(raw.text);
    if (!clean) continue;
    const commentId =
      raw.commentId ||
      crypto.createHash('sha1').update(`${videoId}|${raw.author || ''}|${clean}`).digest('hex');
    ops.push({
      updateOne: {
        filter: { videoId, commentId },
        update: {
          $setOnInsert: {
            videoId,
            commentId,
            author: raw.author,
            text: raw.text,
            cleanText: clean,
            language: detectLanguage(clean),
            likeCount: raw.likeCount || 0,
            publishedAt: raw.publishedAt ? new Date(raw.publishedAt) : undefined,
            timestampSec: extractTimestamp(clean) ?? undefined,
          },
        },
        upsert: true,
      },
    });
  }
  if (!ops.length) return { received: rawComments.length, inserted: 0, duplicatesOrEmpty: rawComments.length };
  const res = await Comment.bulkWrite(ops, { ordered: false });
  return {
    received: rawComments.length,
    inserted: res.upsertedCount,
    duplicatesOrEmpty: rawComments.length - res.upsertedCount,
  };
};

exports.listComments = (videoId, limit = 200) => Comment.find({ videoId }).sort({ createdAt: -1 }).limit(limit).lean();
