'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const recommendationsScript = fs.readFileSync(
	path.join(__dirname, '..', 'frontend', 'js', 'recommendations.js'),
	'utf8'
);
const authScript = fs.readFileSync(
	path.join(__dirname, '..', 'frontend', 'js', 'auth.js'),
	'utf8'
);
const apiScript = fs.readFileSync(
	path.join(__dirname, '..', 'frontend', 'js', 'api.js'),
	'utf8'
);

function createElement() {
	return {
		children: [],
		dataset: {},
		hidden: false,
		style: {},
		value: 'all',
		appendChild(child) { this.children.push(child); },
		addEventListener() {},
		setAttribute() {},
		get innerHTML() { return this._innerHTML || ''; },
		set innerHTML(value) { this._innerHTML = value; this.children = []; },
		querySelector() { return createElement(); }
	};
}

function executeLogin(next) {
	const listeners = {};
	function field(value) {
		return {
			value,
			addEventListener() {},
			closest() { return { classList: { toggle() {} } }; },
			setAttribute() {},
			classList: { toggle() {} }
		};
	}
	const fields = {
		'login-email': field('user@example.test'),
		'login-password': field('Password123'),
		'login-email-error': createElement(),
		'login-password-error': createElement(),
		'login-error': createElement(),
		'login-status': createElement()
	};
	const loginForm = {
		addEventListener(name, callback) { listeners[name] = callback; }
	};
	const window = {
		location: { search: '?next=' + encodeURIComponent(next), href: '' },
		FinpathAPI: {
			login: () => Promise.resolve({}),
			me: () => Promise.resolve({ role: 'user' })
		}
	};
	const document = {
		querySelectorAll: () => [],
		querySelector: () => null,
		getElementById(id) {
			if (id === 'auth-form') return loginForm;
			if (id === 'register-form') return null;
			return fields[id] || createElement();
		}
	};
	class FormDataMock {
		get(name) {
			if (name === 'email') return 'user@example.test';
			if (name === 'password') return 'Password123';
			if (name === 'remember') return null;
			return null;
		}
	}

	vm.runInNewContext(authScript, { window, document, FormData: FormDataMock, URLSearchParams });
	listeners.submit({ preventDefault() {} });
	return new Promise((resolve) => setImmediate(() => resolve(window.location.href)));
}

function executeRecommendations(search, token = 'test-token', scopedRequestFails = false) {
	const ids = [
		'recommendation-list',
		'category-filter',
		'empty-state',
		'recommendation-error',
		'total-count',
		'priority-count',
		'completed-count',
		'progress-value',
		'summary-bar',
		'demo-insight',
		'list-heading'
	];
	const elements = Object.fromEntries(ids.map((id) => [id, createElement()]));
	const selectors = new Map([
		['.summary-section', createElement()],
		['.insight-panel', createElement()],
		['.demo-pill', createElement()],
		['.demo-notice', createElement()],
		['.summary-note', createElement()],
		['.summary-track', createElement()]
	]);
	const calls = { scoped: [], unfiltered: 0 };
	const window = {
		location: { search, href: '' },
		FinpathAPI: {
			getToken: () => token,
			me: () => Promise.resolve({ id: 1 }),
			listRecommendations: () => {
				calls.unfiltered += 1;
				return Promise.resolve([]);
			},
			listRecommendationsForPrediction: (predictionId) => {
				calls.scoped.push(predictionId);
				if (scopedRequestFails) return Promise.reject(new Error('scoped request failed'));
				return Promise.resolve([]);
			}
		}
	};
	const document = {
		getElementById(id) { return elements[id]; },
		querySelector(selector) { return selectors.get(selector) || createElement(); },
		createElement
	};

	vm.runInNewContext(recommendationsScript, { window, document, URLSearchParams });
	return new Promise((resolve) => setImmediate(() => resolve({ calls, elements, window })));
}

test('API client targets the prediction-scoped endpoint', async () => {
	let request;
	const storage = {
		getItem: () => 'test-token',
		removeItem() {},
		setItem() {}
	};
	const window = {
		FINPATH_CONFIG: { API_BASE_URL: 'https://api.example.test' },
		localStorage: storage,
		sessionStorage: storage,
		fetch: (url, options) => {
			request = { url, options };
			return Promise.resolve({
				ok: true,
				text: () => Promise.resolve('[]')
			});
		}
	};

	vm.runInNewContext(apiScript, { window });
	await window.FinpathAPI.listRecommendationsForPrediction(42);

	assert.equal(
		request.url,
		'https://api.example.test/api/v1/recommendations/by-prediction/42'
	);
	assert.equal(request.options.headers.Authorization, 'Bearer test-token');
});

test('valid prediction ID uses the scoped API and never lists all recommendations', async () => {
	const { calls } = await executeRecommendations('?prediction_id=42');

	assert.deepEqual(calls.scoped, [42]);
	assert.equal(calls.unfiltered, 0);
});

test('scoped request failure shows an error without falling back to the unfiltered API', async () => {
	const { calls, elements } = await executeRecommendations('?prediction_id=42', 'test-token', true);

	assert.deepEqual(calls.scoped, [42]);
	assert.equal(calls.unfiltered, 0);
	assert.equal(elements['recommendation-error'].hidden, false);
	assert.equal(elements['recommendation-error'].children[0].href, 'prediction.html?prediction_id=42');
});

test('unauthenticated recommendations redirect preserves the selected prediction ID through login', async () => {
	const { window } = await executeRecommendations('?prediction_id=00042', null);
	const loginUrl = new URL(window.location.href, 'https://finpath.example.test');
	const next = loginUrl.searchParams.get('next');
	const returnedUrl = new URL(next, 'https://finpath.example.test');

	assert.equal(loginUrl.pathname, '/login');
	assert.equal(returnedUrl.pathname, '/recommendations');
	assert.equal(returnedUrl.searchParams.get('prediction_id'), '00042');

	const destination = await executeLogin(next);
	assert.equal(destination, '/recommendations?prediction_id=00042');
});

test('unsafe and invalid recommendation return destinations use the safe fallback', async () => {
	for (const next of [
		'https://attacker.example/recommendations?prediction_id=42',
		'//attacker.example/recommendations?prediction_id=42',
		'/recommendations?prediction_id=0',
		'/recommendations?prediction_id=not-a-number',
		'/recommendations?prediction_id=9007199254740992',
		'/recommendations?prediction_id=42&next=https://attacker.example',
		'/recommendations/../admin?prediction_id=42'
	]) {
		assert.equal(await executeLogin(next), '/dashboard', next);
	}
});

for (const [description, search] of [
	['missing', ''],
	['non-numeric', '?prediction_id=42x'],
	['zero', '?prediction_id=0'],
	['unsafe integer', '?prediction_id=9007199254740992']
]) {
	test(`${description} prediction ID shows an error without making a list request`, async () => {
		const { calls, elements } = await executeRecommendations(search);

		assert.deepEqual(calls.scoped, []);
		assert.equal(calls.unfiltered, 0);
		assert.equal(elements['recommendation-error'].hidden, false);
		assert.equal(elements['recommendation-error'].children[0].href, '/dashboard');
	});
}
