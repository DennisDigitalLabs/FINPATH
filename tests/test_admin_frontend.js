'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const adminScript = fs.readFileSync(
	path.join(__dirname, '..', 'frontend', 'js', 'admin.js'),
	'utf8'
);

function createElement() {
	return {
		children: [],
		hidden: false,
		className: '',
		textContent: '',
		attributes: {},
		insertBefore(child) { this.children.unshift(child); },
		replaceChildren(...children) { this.children = children; },
		setAttribute(name, value) { this.attributes[name] = value; },
		remove() { this.removed = true; }
	};
}

test('admin page replaces its content with a denial message for a normal account', async () => {
	const layout = createElement();
	const content = createElement();
	content.querySelector = () => createElement();
	content.querySelectorAll = () => [createElement(), createElement()];
	const header = createElement();
	const selectors = new Map([
		['.admin-layout', layout],
		['.admin-content', content],
		['.admin-header', header]
	]);
	let analyticsRequests = 0;
	const window = {
		location: { href: '' },
		FinpathAPI: {
			getToken: () => 'user-token',
			me: () => Promise.resolve({ role: 'user' }),
			getSystemAnalytics() {
				analyticsRequests += 1;
				return Promise.resolve({});
			}
		}
	};
	const document = {
		createElement,
		querySelector(selector) { return selectors.get(selector); },
		querySelectorAll() { return []; }
	};

	vm.runInNewContext(adminScript, { window, document });
	await new Promise((resolve) => setImmediate(resolve));

	assert.equal(analyticsRequests, 0);
	assert.equal(layout.children.length, 2);
	assert.match(layout.children[0].textContent, /Administrator access is required/i);
	assert.equal(layout.children[1].href, '/dashboard');
	assert.equal(header.removed, true);
});
