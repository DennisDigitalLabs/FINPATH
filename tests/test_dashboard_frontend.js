'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const dashboardScript = fs.readFileSync(
	path.join(__dirname, '..', 'frontend', 'js', 'dashboard.js'),
	'utf8'
);

function createElement() {
	return {
		children: [],
		hidden: false,
		style: {},
		addEventListener() {},
		appendChild(child) { this.children.push(child); },
		insertBefore() {},
		setAttribute(name, value) { this[name] = value; }
	};
}

async function loadDashboard(prediction) {
	const selectors = new Map([
		['.dashboard-content', createElement()],
		['.welcome-band', createElement()],
		['#dashboard-title', createElement()],
		['.welcome-band .eyebrow', createElement()],
		['.demo-pill', createElement()],
		['.updated-label', createElement()],
		['.risk-card .status-tag', createElement()],
		['.risk-number', createElement()],
		['.risk-main strong', createElement()],
		['.risk-main p', createElement()],
		['.risk-meter', createElement()],
		['.risk-meter span', createElement()],
		['.confidence-card', createElement()],
		['.confidence-card .status-tag', createElement()],
		['.confidence-number', createElement()],
		['.confidence-card p', createElement()],
		['.confidence-meter', createElement()],
		['.confidence-meter span', createElement()],
		['.status-progress strong', createElement()],
		['.status-progress > span', createElement()],
		['.assessment-status-card p', createElement()],
		['.action-card[href="/prediction"]', createElement()],
		['.recommendation-preview', createElement()],
		['.activity-list', createElement()],
		['.activity-section .updated-label', createElement()]
	]);
	const errorState = createElement();
	const content = selectors.get('.dashboard-content');
	content.querySelector = (selector) => selectors.get(selector) || createElement();
	content.querySelectorAll = () => [];
	const document = {
		createElement,
		getElementById: () => createElement(),
		querySelector(selector) {
			if (selector === '.status-meter') throw new Error('Removed placeholder progress meter was queried');
			return selectors.get(selector) || createElement();
		},
		querySelectorAll(selector) {
			return selector === '.dashboard-notice' ? [errorState] : [];
		}
	};
	const window = {
		location: { href: '' },
		FinpathAPI: {
			getToken: () => 'test-token',
			me: () => Promise.resolve({ id: 7 }),
			getDashboard: () => Promise.resolve({
				user: { full_name: 'Test User' },
				assessment_count: 1,
				latest_assessment: { assessment_status: 'completed', updated_at: '2025-01-01T00:00:00Z' },
				latest_prediction: prediction,
				latest_recommendations: [],
				recent_activity: []
			}),
			clearToken() {}
		}
	};
	content.insertBefore = () => {};
	document.querySelector = (selector) => {
		if (selector === '.dashboard-content') return content;
		return selectors.get(selector) || createElement();
	};
	document.querySelectorAll = (selector) => selector === '.dashboard-notice' ? [errorState] : [];

	vm.runInNewContext(dashboardScript, { window, document });
	await new Promise((resolve) => setImmediate(resolve));
	return selectors;
}

test('dashboard renders model probability and omits the fabricated assessment progress meter', async () => {
	const selectors = await loadDashboard({
		id: 42,
		probability: 0.6734,
		confidence: null,
		risk_level: 'medium',
		risk_category: 'Example category',
		explanation: 'Model explanation'
	});

	assert.equal(selectors.get('.risk-number').textContent, '67');
	assert.equal(selectors.get('.risk-meter span').style.width, '67%');
	assert.equal(selectors.get('.confidence-card').hidden, true);
	assert.equal(selectors.get('.status-progress > span').textContent, 'completed');
	assert.match(selectors.get('.assessment-status-card p').textContent, /^Latest assessment updated /);
});

test('dashboard treats out-of-range model values as unavailable', async () => {
	const selectors = await loadDashboard({
		id: 42,
		probability: 1.2,
		confidence: -0.1,
		risk_level: 'medium',
		risk_category: 'Example category',
		explanation: 'Model explanation'
	});

	assert.equal(selectors.get('.risk-number').textContent, '—');
	assert.equal(selectors.get('.risk-meter span').style.width, '0%');
	assert.equal(selectors.get('.confidence-card').hidden, true);
});
