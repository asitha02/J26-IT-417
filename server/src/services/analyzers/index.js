const { analyzer, anthropicApiKey } = require('../../config/env');
const lexicon = require('./lexicon.analyzer');
const llm = require('./llm.analyzer');

// ANALYZER=auto uses Claude when ANTHROPIC_API_KEY is set, otherwise the offline lexicon.
const useLLM = analyzer === 'llm' || (analyzer === 'auto' && Boolean(anthropicApiKey));

module.exports = useLLM ? llm : lexicon;
