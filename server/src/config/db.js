const mongoose = require('mongoose');
const { mongoUri, mongoDb } = require('./env');
const logger = require('../utils/logger');

mongoose.set('strictQuery', true);

const MAX_ATTEMPTS = 5;
const RETRY_DELAY_MS = 3000;
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function connectDB() {
  mongoose.connection.on('disconnected', () => logger.warn('MongoDB disconnected'));
  mongoose.connection.on('error', (err) => logger.error('MongoDB error:', err.message));

  // Retry: flaky DNS or a slow Atlas cold start should not kill the server on the first failure.
  for (let attempt = 1; ; attempt += 1) {
    try {
      await mongoose.connect(mongoUri, { dbName: mongoDb, serverSelectionTimeoutMS: 8000 });
      break;
    } catch (err) {
      if (attempt >= MAX_ATTEMPTS) throw err;
      logger.warn(`MongoDB connect attempt ${attempt}/${MAX_ATTEMPTS} failed (${err.message}); retrying...`);
      await sleep(RETRY_DELAY_MS);
    }
  }
  logger.info(`MongoDB connected: ${mongoose.connection.host}/${mongoose.connection.name}`);
}

async function disconnectDB() {
  await mongoose.connection.close();
}

module.exports = { connectDB, disconnectDB };
