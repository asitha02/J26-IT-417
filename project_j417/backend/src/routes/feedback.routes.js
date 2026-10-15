const router = require('express').Router();
const { z } = require('zod');
const validate = require('../middleware/validate');
const ctrl = require('../controllers/feedback.controller');

const analyzeSchema = z
  .object({
    videoId: z.string().min(1).optional(),
    videoIds: z.array(z.string().min(1)).min(1).optional(),
    force: z.boolean().optional(), // re-classify comments that were already analysed
  })
  .refine((b) => b.videoId || b.videoIds, { message: 'videoId or videoIds is required' });

router.post('/analyze', validate(analyzeSchema), ctrl.analyze);
router.get('/analysis/:id', ctrl.getById);
router.get('/video/:videoId/latest', ctrl.latestForVideo);

module.exports = router;
