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
const apiScript = fs.readFileSync(
	path.join(__dirname, '..', 'frontend', 'js', 'api.js'),
	'utf8'
);
const adminHtml = fs.readFileSync(
	path.join(__dirname, '..', 'frontend', 'admin', 'index.html'),
	'utf8'
);

function createElement(values = {}) {
	return {
		children: [],
		hidden: false,
		textContent: '',
		className: '',
		dataset: {},
		attributes: {},
		listeners: {},
		classList: { toggle() {} },
		addEventListener(name, callback) { this.listeners[name] = callback; },
		appendChild(child) { this.children.push(child); },
		insertBefore(child) { this.children.unshift(child); },
		replaceChildren(...children) { this.children = children; },
		setAttribute(name, value) { this.attributes[name] = value; },
		getAttribute(name) { return this.attributes[name]; },
		remove() { this.removed = true; },
		closest() { return null; },
		...values
	};
}

function createAdminPage() {
	const ids = [
		'admin-state', 'user-list-state', 'health-state', 'admin-users-body',
		'admin-users-table', 'refresh-admin', 'admin-logout', 'create-user-form',
		'create-user-submit', 'create-user-state', 'create-admin-form',
		'create-admin-submit', 'create-admin-state', 'user-search-form',
		'user-search', 'clear-user-search', 'users-previous', 'users-next',
		'admin-dashboard', 'first-admin-setup', 'first-admin-form',
		'first-admin-state', 'first-admin-submit', 'admin-bootstrap-unavailable',
		'assessment-distribution', 'risk-distribution', 'generated-at',
		'users-summary', 'user-page-summary'
	];
	const elements = new Map(ids.map((id) => [id, createElement()]));
	elements.get('user-search').value = '';
	elements.get('admin-dashboard').hidden = true;
	elements.get('first-admin-setup').hidden = true;
	elements.get('first-admin-form').elements = {
		full_name: { value: 'First Owner' },
		email: { value: 'owner@example.com' },
		password: { value: 'FirstOwner123' },
		bootstrap_token: { value: 'temporary-bootstrap-token' },
		confirm_existing_owner: { checked: false }
	};
	elements.get('first-admin-form').reset = function () { this.wasReset = true; };
	elements.get('create-user-form').elements = {
		full_name: { value: 'New Member' },
		email: { value: 'new-member@example.com' },
		password: { value: 'NewMember123' }
	};
	elements.get('create-user-form').reset = function () { this.wasReset = true; };
	elements.get('create-admin-form').elements = {
		full_name: { value: 'New Admin' },
		email: { value: 'new-admin@example.com' },
		password: { value: 'NewAdmin123' }
	};
	elements.get('create-admin-form').reset = function () { this.wasReset = true; };
	elements.get('admin-users-body').addEventListener = function (name, callback) {
		this.listeners[name] = callback;
	};
	const statElements = [
		'user_count', 'active_user_count', 'total_assessments',
		'completed_assessments', 'prediction_count', 'recommendation_count'
	].map((field) => createElement({ getAttribute() { return field; } }));
	const layout = createElement();
	const header = createElement();
	const document = {
		createElement,
		getElementById(id) { return elements.get(id); },
		querySelector(selector) {
			if (selector === '.admin-layout') return layout;
			if (selector === '.admin-header') return header;
			return createElement();
		},
		querySelectorAll(selector) { return selector === '[data-stat]' ? statElements : []; }
	};
	return { document, elements, layout, header, statElements };
}

test('admin page denies a normal account before requesting administrative data', async () => {
	const page = createAdminPage();
	const window = {
		location: { href: '' },
		FinpathAPI: {
			getToken: () => 'user-token',
			getAdminBootstrapStatus: () => Promise.resolve({
				setup_available: false,
				administrator_exists: true,
				setup_configured: true
			}),
			me: () => Promise.resolve({ role: 'user' }),
			getSystemAnalytics() { assert.fail('analytics must not be requested for normal users'); }
		}
	};

	vm.runInNewContext(adminScript, { window, document: page.document });
	await new Promise((resolve) => setImmediate(resolve));

	assert.equal(page.layout.children.length, 2);
	assert.match(page.layout.children[0].textContent, /Administrator access is required/i);
	assert.equal(page.layout.children[1].href, '/');
	assert.equal(page.header.removed, true);
});

test('admin page shows the first-owner form and redirects after successful setup', async () => {
	const page = createAdminPage();
	let submitted;
	const window = {
		location: { href: '' },
		FinpathAPI: {
			getToken: () => null,
			getAdminBootstrapStatus: () => Promise.resolve({
				setup_available: true,
				administrator_exists: false,
				setup_configured: true
			}),
			createFirstAdmin(admin) { submitted = admin; return Promise.resolve({ role: 'admin' }); }
		}
	};

	vm.runInNewContext(adminScript, { window, document: page.document });
	await new Promise((resolve) => setImmediate(resolve));
	assert.equal(page.elements.get('first-admin-setup').hidden, false);
	assert.equal(page.elements.get('admin-dashboard').hidden, true);

	page.elements.get('first-admin-form').listeners.submit({ preventDefault() {} });
	await new Promise((resolve) => setImmediate(resolve));
	assert.equal(JSON.stringify(submitted), JSON.stringify({
		full_name: 'First Owner',
		email: 'owner@example.com',
		password: 'FirstOwner123',
		bootstrap_token: 'temporary-bootstrap-token',
		confirm_existing_owner: false
	}));
	assert.equal(page.elements.get('first-admin-form').wasReset, true);
	assert.equal(window.location.href, '/admin/login?next=%2Fadmin');
});

test('an existing administrator is sent to admin login without showing bootstrap form', async () => {
	const page = createAdminPage();
	const window = {
		location: { href: '' },
		FinpathAPI: {
			getToken: () => null,
			getAdminBootstrapStatus: () => Promise.resolve({
				setup_available: false,
				administrator_exists: true,
				setup_configured: true
			})
		}
	};

	vm.runInNewContext(adminScript, { window, document: page.document });
	await new Promise((resolve) => setImmediate(resolve));

	assert.equal(page.elements.get('first-admin-setup').hidden, true);
	assert.equal(page.elements.get('admin-dashboard').hidden, false);
	assert.equal(window.location.href, '/admin/login?next=%2Fadmin');
});

test('authorized admin loads real overview, health, and paginated account data', async () => {
	const page = createAdminPage();
	let statusChanges = 0;
	const user = {
		id: 22,
		full_name: 'Account Holder',
		email: 'account@example.com',
		role: 'user',
		is_active: true,
		created_at: '2026-10-22T10:00:00Z'
	};
	const window = {
		location: { href: '' },
		confirm: () => true,
		FinpathAPI: {
			getToken: () => 'owner-token',
			getAdminBootstrapStatus: () => Promise.resolve({
				setup_available: false,
				administrator_exists: true,
				setup_configured: true
			}),
			me: () => Promise.resolve({ role: 'admin' }),
			getSystemAnalytics: () => Promise.resolve({
				user_count: 2,
				active_user_count: 2,
				total_assessments: 0,
				completed_assessments: 0,
				prediction_count: 0,
				recommendation_count: 0,
				assessment_status_distribution: {},
				risk_level_distribution: {},
				generated_at: '2026-10-22T10:00:00Z'
			}),
			getAdminHealth: () => Promise.resolve({
				status: 'healthy',
				database: 'available',
				checked_at: '2026-10-22T10:00:00Z'
			}),
			listAdminUsers: () => Promise.resolve({ items: [user], total: 1, page: 1, page_size: 10 }),
			setAdminUserActive(id, isActive) {
				statusChanges += 1;
				assert.equal(id, 22);
				assert.equal(isActive, false);
				return Promise.resolve({});
			},
			clearToken() {}
		}
	};

	vm.runInNewContext(adminScript, { window, document: page.document });
	await new Promise((resolve) => setImmediate(resolve));

	assert.equal(page.statElements[0].textContent, '2');
	assert.equal(page.elements.get('health-state').children[0].children[0].textContent, 'Healthy');
	assert.equal(page.elements.get('admin-users-body').children[0].children[0].children[0].textContent, 'Account Holder');
	assert.equal(page.elements.get('admin-users-table').hidden, false);

	const actionButton = createElement({
		dataset: { userId: '22', active: 'false' },
		disabled: false
	});
	page.elements.get('admin-users-body').listeners.click({
		target: { closest: () => actionButton }
	});
	await new Promise((resolve) => setImmediate(resolve));
	assert.equal(statusChanges, 1);
});

test('admin distinguishes empty accounts and unavailable services from loaded data', async () => {
	const page = createAdminPage();
	const window = {
		location: { href: '' },
		FinpathAPI: {
			getToken: () => 'owner-token',
			getAdminBootstrapStatus: () => Promise.resolve({
				setup_available: false,
				administrator_exists: true,
				setup_configured: true
			}),
			me: () => Promise.resolve({ role: 'admin' }),
			getSystemAnalytics: () => Promise.reject(Object.assign(new Error('Analytics unavailable'), { status: 503 })),
			getAdminHealth: () => Promise.reject(Object.assign(new Error('Database health check failed'), { status: 503 })),
			listAdminUsers: () => Promise.resolve({ items: [], total: 0, page: 1, page_size: 10 }),
			clearToken() {}
		}
	};

	vm.runInNewContext(adminScript, { window, document: page.document });
	await new Promise((resolve) => setImmediate(resolve));

	assert.match(page.elements.get('user-list-state').textContent, /No user accounts are available/);
	assert.match(page.elements.get('health-state').textContent, /Database health check failed/);
	assert.match(page.elements.get('generated-at').textContent, /Analytics unavailable/);
	assert.equal(page.statElements[0].textContent, 'Unavailable');
});

test('admin account form submits to the API and confirms only after success', async () => {
	const page = createAdminPage();
	let submitted;
	const window = {
		location: { href: '' },
		FinpathAPI: {
			getToken: () => 'owner-token',
			getAdminBootstrapStatus: () => Promise.resolve({
				setup_available: false,
				administrator_exists: true,
				setup_configured: true
			}),
			me: () => Promise.resolve({ role: 'admin' }),
			getSystemAnalytics: () => Promise.resolve({
				user_count: 1,
				active_user_count: 1,
				total_assessments: 0,
				completed_assessments: 0,
				prediction_count: 0,
				recommendation_count: 0,
				assessment_status_distribution: {},
				risk_level_distribution: {},
				generated_at: '2026-10-22T10:00:00Z'
			}),
			getAdminHealth: () => Promise.resolve({
				status: 'healthy',
				database: 'available',
				checked_at: '2026-10-22T10:00:00Z'
			}),
			listAdminUsers: () => Promise.resolve({ items: [], total: 0, page: 1, page_size: 10 }),
			createAdminUser(user) { submitted = user; return Promise.resolve({}); },
			createAdminAccount(admin) { submitted = admin; return Promise.resolve({}); },
			clearToken() {}
		}
	};
	vm.runInNewContext(adminScript, { window, document: page.document });
	await new Promise((resolve) => setImmediate(resolve));
	page.elements.get('create-user-form').listeners.submit({ preventDefault() {} });
	await new Promise((resolve) => setImmediate(resolve));

	assert.equal(JSON.stringify(submitted), JSON.stringify({
		full_name: 'New Member',
		email: 'new-member@example.com',
		password: 'NewMember123'
	}));
	assert.equal(page.elements.get('create-user-form').wasReset, true);
	assert.match(page.elements.get('create-user-state').textContent, /Account created/);

	page.elements.get('create-admin-form').listeners.submit({ preventDefault() {} });
	await new Promise((resolve) => setImmediate(resolve));
	assert.equal(JSON.stringify(submitted), JSON.stringify({
		full_name: 'New Admin',
		email: 'new-admin@example.com',
		password: 'NewAdmin123'
	}));
	assert.equal(page.elements.get('create-admin-form').wasReset, true);
	assert.match(page.elements.get('create-admin-state').textContent, /Administrator account created/);
});

test('admin API client uses search pagination and persisted status endpoint', async () => {
	const calls = [];
	const storage = {
		getItem() { return 'owner-token'; },
		removeItem() {},
		setItem() {}
	};
	const window = {
		FINPATH_CONFIG: { API_BASE_URL: 'https://api.example.invalid' },
		localStorage: storage,
		sessionStorage: storage,
		fetch(url, options) {
			calls.push({ url, options });
			return Promise.resolve({
				ok: true,
				status: 200,
				text: () => Promise.resolve('{}')
			});
		}
	};
	vm.runInNewContext(apiScript, { window, URLSearchParams });

	await window.FinpathAPI.listAdminUsers('Alice Smith', 2, 20);
	await window.FinpathAPI.createAdminUser({
		full_name: 'New Member',
		email: 'new-member@example.com',
		password: 'NewMember123'
	});
	await window.FinpathAPI.createAdminAccount({
		full_name: 'New Admin',
		email: 'new-admin@example.com',
		password: 'NewAdmin123'
	});
	await window.FinpathAPI.setAdminUserActive(9, false);
	await window.FinpathAPI.getAdminBootstrapStatus();
	await window.FinpathAPI.createFirstAdmin({
		full_name: 'First Owner',
		email: 'owner@example.com',
		password: 'FirstOwner123',
		bootstrap_token: 'temporary-bootstrap-token',
		confirm_existing_owner: false
	});

	assert.match(calls[0].url, /\/api\/v1\/admin\/users\?search=Alice\+Smith&page=2&page_size=20$/);
	assert.equal(calls[0].options.method, 'GET');
	assert.equal(calls[1].url, 'https://api.example.invalid/api/v1/admin/users');
	assert.equal(calls[1].options.method, 'POST');
	assert.equal(calls[1].options.body, '{"full_name":"New Member","email":"new-member@example.com","password":"NewMember123"}');
	assert.equal(calls[2].url, 'https://api.example.invalid/api/v1/admin/admins');
	assert.equal(calls[2].options.method, 'POST');
	assert.equal(calls[2].options.body, '{"full_name":"New Admin","email":"new-admin@example.com","password":"NewAdmin123"}');
	assert.equal(calls[3].url, 'https://api.example.invalid/api/v1/admin/users/9/status');
	assert.equal(calls[3].options.method, 'PATCH');
	assert.equal(calls[3].options.body, '{"is_active":false}');
	assert.equal(calls[4].url, 'https://api.example.invalid/api/v1/admin/bootstrap/status');
	assert.equal(calls[4].options.method, 'GET');
	assert.equal(calls[5].url, 'https://api.example.invalid/api/v1/admin/bootstrap');
	assert.equal(calls[5].options.method, 'POST');
	assert.equal(calls[5].options.body, '{"full_name":"First Owner","email":"owner@example.com","password":"FirstOwner123","bootstrap_token":"temporary-bootstrap-token","confirm_existing_owner":false}');
});

test('admin page exposes working search, pagination, health, refresh, and logout controls', () => {
	assert.match(adminHtml, /id="refresh-admin"/);
	assert.match(adminHtml, /id="admin-logout"/);
	assert.match(adminHtml, /id="user-search-form"/);
	assert.match(adminHtml, /id="create-user-form"/);
	assert.match(adminHtml, /id="create-admin-form"/);
	assert.match(adminHtml, /id="first-admin-form"/);
	assert.match(adminHtml, /Create First Admin Account/);
	assert.match(adminHtml, /id="users-previous"/);
	assert.match(adminHtml, /id="users-next"/);
	assert.match(adminHtml, /id="health-section"/);
});
