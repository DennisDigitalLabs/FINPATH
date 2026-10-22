'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const profileScript = fs.readFileSync(
	path.join(__dirname, '..', 'frontend', 'js', 'profile.js'),
	'utf8'
);

function createElement() {
	return {
		hidden: false,
		attributes: {},
		textContent: '',
		setAttribute(name, value) { this.attributes[name] = value; }
	};
}

async function loadProfile(dashboardRequest) {
	const content = createElement();
	const elements = Object.fromEntries([
		'profile-error',
		'profile-assessment-count',
		'profile-assessment-status',
		'profile-risk-result',
		'profile-prediction-link',
		'profile-recommendations-link'
	].map((id) => [id, createElement()]));
	const selectors = new Map([
		['.profile-content', content],
		['[data-profile-name]', createElement()],
		['[data-profile-email]', createElement()],
		['.profile-grid', createElement()],
		['.security-panel', createElement()]
	]);
	const window = {
		location: { href: '' },
		FinpathAPI: {
			getToken: () => 'test-token',
			me: () => Promise.resolve({ full_name: 'Test User', email: 'user@example.test' }),
			getDashboard: dashboardRequest
		}
	};
	const document = {
		getElementById(id) { return elements[id]; },
		querySelector(selector) { return selectors.get(selector); }
	};

	vm.runInNewContext(profileScript, { window, document, encodeURIComponent });
	await new Promise((resolve) => setImmediate(resolve));
	return { content, elements, selectors };
}

test('profile displays the current account response and hides recommendations without a prediction', async () => {
	const result = await loadProfile(() => Promise.resolve({
		assessment_count: 0,
		latest_assessment: null,
		latest_prediction: null
	}));

	assert.equal(result.selectors.get('[data-profile-name]').textContent, 'Test User');
	assert.equal(result.selectors.get('[data-profile-email]').textContent, 'user@example.test');
	assert.equal(result.elements['profile-assessment-count'].textContent, '0');
	assert.equal(result.elements['profile-prediction-link'].href, '/assessment');
	assert.equal(result.elements['profile-recommendations-link'].hidden, true);
	assert.equal(result.content.attributes['aria-busy'], 'false');
});

test('profile hides loading content when account activity cannot be loaded', async () => {
	const result = await loadProfile(() => Promise.reject(new Error('Account activity unavailable')));

	assert.equal(result.elements['profile-error'].hidden, false);
	assert.equal(result.elements['profile-error'].textContent, 'Account activity unavailable');
	assert.equal(result.selectors.get('.profile-grid').hidden, true);
	assert.equal(result.selectors.get('.security-panel').hidden, true);
	assert.equal(result.content.attributes['aria-busy'], 'false');
});
