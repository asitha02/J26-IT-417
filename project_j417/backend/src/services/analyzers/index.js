const { analyzer, anthropicApiKey } = require('../../config/env');
const lexicon = require('./lexicon.analyzer');
const llm = require('./llm.analyzer');
const bert = require('./bert.analyzer');

// ANALYZER=bert uses the RoBERTa service in ml_service/.
// ANALYZER=auto uses Claude when ANTHROPIC_API_KEY is set, otherwise the offline lexicon.
const useLLM = analyzer === 'llm' || (analyzer === 'auto' && Boolean(anthropicApiKey));

module.exports = analyzer === 'bert' ? bert : useLLM ? llm : lexicon;
