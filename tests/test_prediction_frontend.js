'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const predictionScript = fs.readFileSync(
	path.join(__dirname, '..', 'frontend', 'js', 'prediction.js'),
	'utf8'
);
const predictionHtml = fs.readFileSync(
	path.join(__dirname, '..', 'frontend', 'prediction.html'),
	'utf8'
);

function createElement() {
	return {
		childNodes: [{ textContent: '' }],
		hidden: false,
		style: {},
		appendChild() {},
		setAttribute() {},
		focus() {},
		querySelector() { return createElement(); }
	};
}

test('prediction recommendations link includes the selected prediction ID', async () => {
	const initialHref = predictionHtml.match(
		/<a class="btn btn-primary" href="([^"]+)">View recommendations/
	)[1];
	const recommendationsLink = { href: initialHref };
	const ids = [
		'processing-state',
		'result-state',
		'prediction-error',
		'processing-status',
		'result-heading'
	];
	const elements = Object.fromEntries(ids.map((id) => [id, createElement()]));
	elements['processing-state'].parentNode = { insertBefore() {} };
	elements['result-state'].querySelector = () => createElement();
	const selectors = new Map([
		['.result-header .panel-lede', createElement()],
		['.risk-badge', createElement()],
		['.score-ring span', createElement()],
		['.meter-track', createElement()],
		['.confidence-value', createElement()],
		['.confidence-card p', createElement()],
		['.confidence-track', createElement()],
		['.demo-badge', createElement()],
		['.factor-list', createElement()],
		['.result-actions a[href^="/recommendations"]', recommendationsLink],
		['.score-label', createElement()],
		['.tooltip-mark', createElement()],
		['.score-visual p', createElement()],
		['.factors-section .section-heading > p', createElement()]
	]);
	const window = {
		location: { search: '?prediction_id=42' },
		FinpathAPI: {
			me: () => Promise.resolve({ id: 7 }),
			getPrediction: () => Promise.resolve({
				id: 42,
				risk_level: 'medium',
				probability: 0.5,
				confidence: null,
				explanation: 'Prediction explanation',
				model_version: 'test',
				contributing_factors: []
			})
		}
	};
	const document = {
		getElementById(id) { return elements[id] || createElement(); },
		querySelector(selector) { return selectors.get(selector) || createElement(); },
		createElement
	};

	assert.equal(initialHref, '/recommendations');
	vm.runInNewContext(predictionScript, { window, document, URLSearchParams });
	await new Promise((resolve) => setImmediate(resolve));

	assert.equal(recommendationsLink.href, '/recommendations?prediction_id=42');
});
