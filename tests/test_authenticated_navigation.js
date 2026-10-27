'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const frontend = path.join(__dirname, '..', 'frontend');
const apiScript = fs.readFileSync(path.join(frontend, 'js', 'api.js'), 'utf8');

test('authenticated workspace pages expose a shared logout control', () => {
	for (const file of [
		'assessment.html',
		'prediction.html',
		'recommendations.html',
		'analytics.html',
		'profile.html'
	]) {
		const html = fs.readFileSync(path.join(frontend, file), 'utf8');
		assert.match(html, /<button[^>]*data-logout[^>]*>Log out<\/button>/, file);
	}
});

test('shared logout clears persistent and session tokens before navigating to login', () => {
	const handlers = [];
	const removals = [];
	const button = {
		addEventListener(name, callback) {
			assert.equal(name, 'click');
			handlers.push(callback);
		}
	};
	const storage = {
		getItem() { return 'stored-token'; },
		removeItem(key) { removals.push(key); },
		setItem() {}
	};
	const window = {
		localStorage: storage,
		sessionStorage: storage,
		location: { href: '' }
	};
	const document = {
		querySelectorAll(selector) {
			assert.equal(selector, '[data-logout]');
			return [button];
		}
	};

	vm.runInNewContext(apiScript, { window, document, URLSearchParams });
	assert.equal(handlers.length, 1);
	handlers[0]();

	assert.deepEqual(removals, ['finpath_access_token', 'finpath_access_token']);
	assert.equal(window.location.href, '/login');
});
