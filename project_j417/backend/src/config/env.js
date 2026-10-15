require('dotenv').config();

const required = ['MONGODB_URI'];
for (const key of required) {
  if (!process.env[key]) throw new Error(`Missing required env var: ${key}`);
}

module.exports = {
  nodeEnv: process.env.NODE_ENV || 'development',
  port: Number(process.env.PORT) || 5000,
  mongoUri: process.env.MONGODB_URI,
  mongoDb: process.env.MONGODB_DB || undefined,
  clientOrigin: process.env.CLIENT_ORIGIN || 'http://localhost:5173',
  // Audience feedback mining
  analyzer: (process.env.ANALYZER || 'auto').toLowerCase(), // auto | llm | lexicon
  anthropicApiKey: process.env.ANTHROPIC_API_KEY || '',
  anthropicModel: process.env.ANTHROPIC_MODEL || 'claude-opus-5-5',
  youtubeApiKey: process.env.YOUTUBE_API_KEY || '',
};
