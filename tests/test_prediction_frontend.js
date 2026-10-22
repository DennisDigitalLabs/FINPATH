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
		children: [],
		hidden: false,
		style: {},
		appendChild(child) { this.children.push(child); },
		setAttribute(name, value) {
			this.attributes = this.attributes || {};
			this.attributes[name] = value;
		},
		focus() {},
		querySelector() { return createElement(); }
	};
}

async function loadPrediction(search, latestPrediction = {
	id: 42,
	risk_level: 'medium',
	probability: 0.5,
	confidence: null,
	explanation: 'Prediction explanation',
	model_version: 'test',
	contributing_factors: []
}, pending = false) {
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
	elements['processing-state'].hidden = true;
	elements['processing-state'].parentNode = { insertBefore() {} };
	elements['result-state'].querySelector = () => createElement();
	const selectors = new Map([
		['.result-header .panel-lede', createElement()],
		['.risk-badge', createElement()],
		['.score-ring span', createElement()],
		['.meter-track', createElement()],
		['.confidence-value', createElement()],
		['.confidence-card p', createElement()],
		['.confidence-card', createElement()],
		['.confidence-track', createElement()],
		['.model-badge', createElement()],
		['.factor-list', createElement()],
		['.result-actions a[href^="/recommendations"]', recommendationsLink],
		['.score-label', createElement()],
		['.tooltip-mark', createElement()],
		['.score-visual p', createElement()],
		['.factors-section .section-heading > p', createElement()]
	]);
	const calls = { dashboard: 0 };
	const window = {
		location: { search },
		FinpathAPI: {
			me: () => pending ? new Promise(() => {}) : Promise.resolve({ id: 7 }),
			getPrediction: (id) => Promise.resolve({ ...latestPrediction, id }),
			getDashboard: () => {
				calls.dashboard += 1;
				return Promise.resolve({ latest_prediction: latestPrediction });
			}
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
	return {
		calls,
		confidenceCard: selectors.get('.confidence-card'),
		errorState: elements['prediction-error'],
		factorList: selectors.get('.factor-list'),
		link: recommendationsLink,
		processingState: elements['processing-state'],
		resultState: elements['result-state']
	};
}

test('prediction recommendations link includes the selected prediction ID', async () => {
	const result = await loadPrediction('?prediction_id=42');

	assert.equal(result.link.href, '/recommendations?prediction_id=42');
	assert.equal(result.calls.dashboard, 0);
	assert.equal(result.processingState.hidden, true);
	assert.equal(result.processingState.attributes['aria-busy'], 'false');
});

test('prediction page loads the signed-in user latest result when no ID is selected', async () => {
	const result = await loadPrediction('');

	assert.equal(result.calls.dashboard, 1);
	assert.equal(result.resultState.hidden, false);
	assert.equal(result.link.href, '/recommendations?prediction_id=42');
});

test('prediction page explains when the user has no prediction yet', async () => {
	const result = await loadPrediction('', null);

	assert.equal(result.calls.dashboard, 1);
	assert.equal(result.resultState.hidden, true);
	assert.equal(result.errorState.hidden, false);
	assert.match(result.errorState.textContent, /complete an assessment/i);
});

test('prediction page shows an indeterminate loading state while fetching the result', async () => {
	const result = await loadPrediction('', undefined, true);

	assert.equal(result.processingState.hidden, false);
	assert.equal(result.processingState.attributes['aria-busy'], 'true');
	assert.doesNotMatch(predictionHtml, /aria-valuenow="40"|width: 40%/);
});

test('prediction page renders real SHAP impacts and hides confidence not returned by the model', async () => {
	const result = await loadPrediction('?prediction_id=42', {
		id: 42,
		risk_level: 'medium',
		probability: 0.4133,
		confidence: null,
		explanation: 'Model output',
		model_version: 'v1',
		contributing_factors: {
			top_factors: [{ feature: 'cat__loan_informal_0', impact: -0.125 }]
		}
	});
	const factorCard = result.factorList.children[0];

	assert.equal(factorCard.className, 'factor-card');
	assert.equal(factorCard.children[0].children[0].textContent, 'Loan informal (encoded category 0)');
	assert.equal(factorCard.children[0].children[1].textContent, 'SHAP impact for the predicted class: -0.1250');
	assert.equal(result.confidenceCard.hidden, true);
	assert.doesNotMatch(predictionHtml, /Illustrative demo data|moderate financial inclusion risk|<span>46<|<small>78/);
});
