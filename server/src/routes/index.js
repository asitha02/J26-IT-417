const router = require('express').Router();

router.get('/health', (req, res) => res.json({ success: true, data: { status: 'ok' } }));
router.use('/users', require('./user.routes'));
router.use('/videos', require('./video.routes'));
router.use('/feedback', require('./feedback.routes'));

module.exports = router;
