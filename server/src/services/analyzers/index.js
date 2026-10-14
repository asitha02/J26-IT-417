const { analyzer, anthropicApiKey } = require('../../config/env');
const lexicon = require('./lexicon.analyzer');
const llm = require('./llm.analyzer');
const model = require('./model.analyzer');

// ANALYZER=auto uses Claude when ANTHROPIC_API_KEY is set, otherwise the offline lexicon.
const useLLM = analyzer === 'llm' || (analyzer === 'auto' && Boolean(anthropicApiKey));

// ANALYZER=model uses the locally trained model served by training/serve.py.
module.exports = analyzer === 'model' ? model : useLLM ? llm : lexicon;
