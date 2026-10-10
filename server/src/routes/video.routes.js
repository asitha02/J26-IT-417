const router = require('express').Router();
const { z } = require('zod');
const validate = require('../middleware/validate');
const ctrl = require('../controllers/video.controller');

const videoSchema = z.object({
  videoId: z.string().min(1),
  title: z.string().optional(),
  durationSec: z.number().positive().optional(),
  views: z.number().nonnegative().optional(),
  topics: z
    .array(z.object({
      name: z.string().min(1),
      startSec: z.number().nonnegative(),
      endSec: z.number().positive().optional(),
      keywords: z.array(z.string()).optional(),
    }))
    .optional(),
  retention: z.array(z.object({ second: z.number().nonnegative(), pct: z.number().min(0).max(100) })).optional(),
  audioSignals: z
    .array(z.object({
      startSec: z.number().nonnegative(),
      endSec: z.number().positive().optional(),
      emotion: z.string(),
      intensity: z.number().min(0).max(1).optional(),
    }))
    .optional(),
});

const commentsSchema = z.object({
  comments: z
    .array(z.object({
      text: z.string().min(1),
      commentId: z.string().optional(),
      author: z.string().optional(),
      likeCount: z.number().int().nonnegative().optional(),
      publishedAt: z.string().optional(),
    }))
    .min(1)
    .max(5000),
});

const youtubeSchema = z.object({ maxPages: z.number().int().min(1).max(20).optional() });

const importSchema = z.object({ url: z.string().min(1), maxPages: z.number().int().min(1).max(20).optional() });

router.get('/', ctrl.list);
router.post('/', validate(videoSchema), ctrl.upsert);
router.post('/import', validate(importSchema), ctrl.importVideo);
router.get('/:videoId', ctrl.get);
router.get('/:videoId/comments', ctrl.listComments);
router.post('/:videoId/comments', validate(commentsSchema), ctrl.addComments);
router.post('/:videoId/comments/youtube', validate(youtubeSchema), ctrl.importFromYoutube);

module.exports = router;
