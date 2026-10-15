const feedback = require('../services/feedback.service');
const asyncHandler = require('../utils/asyncHandler');

exports.analyze = asyncHandler(async (req, res) => {
  const { videoId, videoIds, force } = req.body;
  const ids = videoIds?.length ? videoIds : [videoId];
  res.json({ success: true, data: await feedback.analyze({ videoIds: ids, force }) });
});

exports.getById = asyncHandler(async (req, res) => {
  const doc = await feedback.getById(req.params.id);
  if (!doc) return res.status(404).json({ success: false, message: 'Analysis not found' });
  res.json({ success: true, data: doc });
});

exports.latestForVideo = asyncHandler(async (req, res) => {
  const doc = await feedback.latestForVideo(req.params.videoId);
  if (!doc) return res.status(404).json({ success: false, message: 'No analysis for this video yet' });
  res.json({ success: true, data: doc });
});
