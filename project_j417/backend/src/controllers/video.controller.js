const ingestion = require('../services/ingestion.service');
const youtube = require('../services/youtube.service');
const asyncHandler = require('../utils/asyncHandler');

exports.upsert = asyncHandler(async (req, res) => {
  res.status(201).json({ success: true, data: await ingestion.upsertVideo(req.body) });
});

exports.list = asyncHandler(async (req, res) => {
  res.json({ success: true, data: await ingestion.listVideos() });
});

exports.get = asyncHandler(async (req, res) => {
  const video = await ingestion.getVideo(req.params.videoId);
  if (!video) return res.status(404).json({ success: false, message: 'Video not found' });
  res.json({ success: true, data: video });
});

exports.addComments = asyncHandler(async (req, res) => {
  const data = await ingestion.addComments(req.params.videoId, req.body.comments);
  res.status(201).json({ success: true, data });
});

exports.listComments = asyncHandler(async (req, res) => {
  res.json({ success: true, data: await ingestion.listComments(req.params.videoId) });
});

/** One call: URL -> video metadata + chapters (topics) + comments. */
exports.importVideo = asyncHandler(async (req, res) => {
  const videoId = youtube.parseVideoId(req.body.url);
  const { topics, ...meta } = await youtube.fetchVideoMeta(videoId);
  const fields = Object.fromEntries(Object.entries(meta).filter(([, v]) => v !== undefined));
  if (topics.length) fields.topics = topics; // keep topics from other components if YouTube has no chapters
  const video = await ingestion.upsertVideo(fields);
  const comments = await youtube.fetchComments(videoId, req.body.maxPages);
  const stats = await ingestion.addComments(videoId, comments);
  res.status(201).json({ success: true, data: { video, comments: stats, chaptersFound: topics.length } });
});

exports.importFromYoutube =asyncHandler(async (req, res) => {
  const comments = await youtube.fetchComments(req.params.videoId, req.body.maxPages);
  const data = await ingestion.addComments(req.params.videoId, comments);
  res.status(201).json({ success: true, data });
});
