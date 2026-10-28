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
const adminCss = fs.readFileSync(
	path.join(__dirname, '..', 'frontend', 'css', 'admin.css'),
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
		focus() { this.focused = true; },
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
		'users-summary', 'user-page-summary', 'user-active-filter',
		'admin-records-section', 'record-list-state',
		'admin-records-table', 'admin-records-head', 'admin-records-body',
		'records-summary', 'record-page-summary', 'records-previous',
		'records-next', 'record-search-form', 'record-search', 'record-filter',
		'clear-record-search', 'admin-records-heading',
		'risk-category-distribution', 'assessment-completion-rate',
		'model-monitoring-state', 'model-monitoring-details',
		'model-runtime-status', 'model-runtime-version', 'model-prediction-count',
		'model-explanation-count', 'model-factor-count', 'model-version-distribution',
		'operational-events-state', 'operational-events-table', 'operational-events-body',
		'operational-summary', 'operational-events-page-summary',
		'operational-events-previous', 'operational-events-next',
		'audit-logs-state', 'audit-logs-table', 'audit-logs-body',
		'audit-logs-summary', 'audit-logs-page-summary',
		'audit-logs-previous', 'audit-logs-next',
		'operational-status-filter', 'operational-severity-filter',
		'audit-filter-form', 'audit-action-filter', 'audit-actor-filter',
		'audit-outcome-filter', 'audit-date-from', 'audit-date-to',
		'clear-audit-filters', 'admin-sidebar', 'admin-menu-toggle',
		'admin-menu-backdrop'
	];
	const elements = new Map(ids.map((id) => [id, createElement()]));
	const sidebarClasses = new Set();
	elements.get('admin-sidebar').classList = {
		toggle(name, force) {
			if (force) sidebarClasses.add(name);
			else sidebarClasses.delete(name);
		},
		contains(name) { return sidebarClasses.has(name); }
	};
	elements.get('admin-menu-toggle').attributes['aria-expanded'] = 'false';
	elements.get('admin-menu-toggle').closest = (selector) =>
		selector.includes('#admin-menu-toggle') ? elements.get('admin-menu-toggle') : null;
	elements.get('user-search').value = '';
	elements.get('user-active-filter').value = '';
	elements.get('operational-status-filter').value = '';
	elements.get('operational-severity-filter').value = '';
	elements.get('audit-action-filter').value = '';
	elements.get('audit-actor-filter').value = '';
	elements.get('audit-outcome-filter').value = '';
	elements.get('audit-date-from').value = '';
	elements.get('audit-date-to').value = '';
	elements.get('audit-filter-form').reset = function () {
		elements.get('audit-action-filter').value = '';
		elements.get('audit-actor-filter').value = '';
		elements.get('audit-outcome-filter').value = '';
		elements.get('audit-date-from').value = '';
		elements.get('audit-date-to').value = '';
	};
	elements.get('admin-dashboard').hidden = true;
	elements.get('admin-records-section').hidden = true;
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
	const statCards = [
		createElement({ dataset: { userActive: 'all' } }),
		createElement({ dataset: { userActive: 'true' } }),
		createElement({ dataset: { recordType: 'assessments' } }),
		createElement({ dataset: { recordType: 'assessments', recordFilter: 'completed' } }),
		createElement({ dataset: { recordType: 'predictions' } }),
		createElement({ dataset: { recordType: 'recommendations' } })
	];
	const recordsNavLink = createElement({ href: '#admin-records-section' });
	const sidebarLinks = [
		'#overview-section', '#admin-records-section', '#users-section',
		'#model-monitoring-section', '#health-section',
		'#operational-events-section', '#audit-logs-section'
	].map((href, index) => {
		const link = createElement({
			href,
			attributes: index === 0 ? { 'aria-current': 'page' } : {},
			classList: {
				active: index === 0,
				toggle(name, force) {
					if (name === 'active') this.active = Boolean(force);
				}
			},
			removeAttribute(name) { delete this.attributes[name]; }
		});
		return link;
	});
	const layout = createElement();
	const header = createElement();
	const documentListeners = {};
	const document = {
		createElement,
		addEventListener(name, callback) { documentListeners[name] = callback; },
		getElementById(id) { return elements.get(id); },
		querySelector(selector) {
			if (selector === '.admin-layout') return layout;
			if (selector === '.admin-header') return header;
			if (selector === '.admin-sidebar') return elements.get('admin-sidebar');
			return createElement();
		},
		querySelectorAll(selector) {
			if (selector === '[data-stat]') return statElements;
			if (selector === '.admin-stat-link') return statCards;
			if (selector === '.side-link[href="#admin-records-section"]') return [recordsNavLink];
			if (selector === '.admin-sidebar .side-link') return sidebarLinks;
			return [];
		}
	};
	return {
		document, elements, layout, header, statElements, statCards,
		recordsNavLink, sidebarLinks, documentListeners, sidebarClasses
	};
}

function emptyAdminEventApi() {
	return {
		getAdminOperationalSummary: () => Promise.resolve({
			recorded_error_count: 0,
			open_alert_count: 0,
			generated_at: '2026-10-22T10:00:00Z'
		}),
		listAdminOperationalEvents: (page, pageSize) => Promise.resolve({
			items: [], total: 0, page, page_size: pageSize
		}),
		acknowledgeAdminAlert: () => Promise.resolve({}),
		listAdminAuditLogs: (page, pageSize) => Promise.resolve({
			items: [], total: 0, page, page_size: pageSize
		})
	};
}

test('admin page styling stays scoped and exposes active responsive navigation', async () => {
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
			getSystemAnalytics: () => Promise.resolve({
				user_count: 0, active_user_count: 0, total_assessments: 0,
				completed_assessments: 0, prediction_count: 0, recommendation_count: 0,
				assessment_status_distribution: {}, risk_level_distribution: {},
				risk_category_distribution: {}, assessment_completion_rate: null,
				generated_at: '2026-10-22T10:00:00Z'
			}),
			getAdminHealth: () => Promise.resolve({
				status: 'healthy', database: 'available', checked_at: '2026-10-22T10:00:00Z'
			}),
			getAdminModelMonitoring: () => Promise.resolve({
				model_available: false, model_version: null, recorded_prediction_count: 0,
				recorded_model_versions: {}, explanation_available_count: 0,
				contributing_factors_available_count: 0, generated_at: '2026-10-22T10:00:00Z'
			}),
			...emptyAdminEventApi(),
			listAdminUsers: () => Promise.resolve({ items: [], total: 0, page: 1, page_size: 10 }),
			clearToken() {}
		}
	};

	assert.match(adminHtml, /href="\/css\/admin\.css"/);
	assert.doesNotMatch(adminHtml, /admin-redesign\.css/);
	assert.match(adminHtml, /class="admin-sidebar-brand"/);
	assert.match(adminCss, /\/\* Admin dashboard redesign: page shell \*\//);
	assert.match(adminCss, /\.admin-page \.admin-sidebar-brand/);
	assert.match(adminCss, /\.admin-page \.admin-layout\.container/);
	assert.match(adminCss, /@media \(max-width: 48rem\)/);
	assert.match(adminCss, /@media \(max-width: 36rem\)/);
	assert.match(adminCss, /\.admin-page \.admin-sidebar \{[^}]*overflow-y: auto/s);
	assert.match(adminCss, /\.admin-page \.admin-sidebar \.side-nav \{[^}]*flex: 0 0 auto/s);
	assert.match(adminCss, /\.admin-page \.admin-sidebar \.sidebar-note \{[^}]*margin-top: 1rem/s);
	assert.match(adminHtml, /id="admin-menu-toggle"[^>]*aria-expanded="false"[^>]*aria-controls="admin-sidebar"/);
	assert.match(adminCss, /\.admin-page \.admin-menu-toggle/);
	vm.runInNewContext(adminScript, { window, document: page.document });
	await new Promise((resolve) => setImmediate(resolve));

	const toggle = page.elements.get('admin-menu-toggle');
	const backdrop = page.elements.get('admin-menu-backdrop');
	toggle.listeners.click();
	assert.equal(toggle.attributes['aria-expanded'], 'true');
	assert.equal(toggle.attributes['aria-label'], 'Close admin navigation');
	assert.equal(page.sidebarClasses.has('is-open'), true);
	assert.equal(backdrop.hidden, false);
	toggle.listeners.click();
	assert.equal(toggle.attributes['aria-expanded'], 'false');
	assert.equal(backdrop.hidden, true);

	toggle.listeners.click();
	page.documentListeners.keydown({ key: 'Escape' });
	assert.equal(toggle.attributes['aria-expanded'], 'false');
	assert.equal(toggle.focused, true);

	toggle.listeners.click();
	backdrop.listeners.click();
	assert.equal(toggle.attributes['aria-expanded'], 'false');
	assert.equal(backdrop.hidden, true);

	toggle.listeners.click();
	page.sidebarLinks[2].listeners.click();
	assert.equal(toggle.attributes['aria-expanded'], 'false');
	assert.equal(backdrop.hidden, true);

	toggle.listeners.click();
	page.documentListeners.click({ target: { closest: () => null } });
	assert.equal(toggle.attributes['aria-expanded'], 'false');

	page.sidebarLinks[3].listeners.click();
	assert.equal(page.sidebarLinks[3].classList.active, true);
	assert.equal(page.sidebarLinks[0].classList.active, false);
	assert.equal(page.sidebarLinks[3].attributes['aria-current'], 'page');
	assert.equal(page.sidebarLinks[0].attributes['aria-current'], undefined);
});

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
				risk_category_distribution: {},
				assessment_completion_rate: null,
				generated_at: '2026-10-22T10:00:00Z'
			}),
			getAdminHealth: () => Promise.resolve({
				status: 'healthy',
				database: 'available',
				checked_at: '2026-10-22T10:00:00Z'
			}),
			getAdminModelMonitoring: () => Promise.resolve({
				model_available: true,
				model_version: 'v1',
				recorded_prediction_count: 3,
				recorded_model_versions: { v1: 3 },
				explanation_available_count: 2,
				contributing_factors_available_count: 1,
				generated_at: '2026-10-22T10:00:00Z'
			}),
			...emptyAdminEventApi(),
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
	assert.equal(page.elements.get('model-runtime-status').textContent, 'Loaded and available');
	assert.equal(page.elements.get('model-runtime-version').textContent, 'Loaded version: v1');
	assert.equal(page.elements.get('model-prediction-count').textContent, '3 predictions stored');
	assert.match(page.elements.get('model-explanation-count').textContent, /2 of 3/);
	assert.match(page.elements.get('model-factor-count').textContent, /1 recorded predictions/);
	assert.equal(page.elements.get('model-monitoring-details').hidden, false);
	assert.equal(page.elements.get('operational-summary').textContent, '0 recorded errors · 0 open alerts');
	assert.equal(page.elements.get('operational-events-state').textContent, 'No operational events have been recorded.');
	assert.match(adminHtml, /Accuracy, drift, and prediction latency are not measured/);
	assert.match(adminHtml, /Prediction failures are not comprehensively recorded/);
	assert.match(adminHtml, /Open warning, error, and critical events are actionable alerts/);
	assert.match(adminHtml, /Alert notifications are in-dashboard only/);
	assert.equal(page.elements.get('audit-logs-state').textContent, 'No audit records have been recorded.');
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

test('operational events distinguish informational and acknowledged alerts', async () => {
	const page = createAdminPage();
	const operationalApi = emptyAdminEventApi();
	const eventRequests = [];
	let acknowledgements = 0;
	let eventRefreshes = 0;
	let auditRefreshes = 0;
	let rejectAcknowledgement = true;
	operationalApi.listAdminOperationalEvents = (pageNumber, pageSize, statusFilter, severityFilter) => {
		eventRequests.push({ pageNumber, pageSize, statusFilter, severityFilter });
		eventRefreshes += 1;
		return Promise.resolve({
		items: [
			{
				id: 1, event_type: 'maintenance.note', source: 'admin', severity: 'info',
				summary: 'Recorded information', status: 'open',
				occurred_at: '2026-10-22T10:00:00Z', acknowledged_at: null
			},
			{
				id: 2, event_type: 'service.warning', source: 'admin', severity: 'warning',
				summary: 'Acknowledged warning', status: 'acknowledged',
				occurred_at: '2026-10-22T10:00:00Z',
				acknowledged_at: '2026-10-22T10:01:00Z', acknowledged_by_user_id: 23
			},
			{
				id: 3, event_type: 'service.warning', source: 'admin', severity: 'warning',
				summary: 'Open warning', status: 'open',
				occurred_at: '2026-10-22T10:00:00Z', acknowledged_at: null,
				acknowledged_by_user_id: null
			}
		],
		total: 3, page: pageNumber, page_size: pageSize
		});
	};
	operationalApi.acknowledgeAdminAlert = (eventId) => {
		assert.equal(eventId, 3);
		acknowledgements += 1;
		if (rejectAcknowledgement) {
			rejectAcknowledgement = false;
			return Promise.reject(Object.assign(
				new Error('Alert is not open for acknowledgement'),
				{ status: 409 }
			));
		}
		return Promise.resolve({});
	};
	operationalApi.listAdminAuditLogs = (pageNumber, pageSize) => {
		auditRefreshes += 1;
		return Promise.resolve({
			items: [], total: 0, page: pageNumber, page_size: pageSize
		});
	};
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
				user_count: 0, active_user_count: 0, total_assessments: 0,
				completed_assessments: 0, prediction_count: 0, recommendation_count: 0,
				assessment_status_distribution: {}, risk_level_distribution: {},
				risk_category_distribution: {}, assessment_completion_rate: null,
				generated_at: '2026-10-22T10:00:00Z'
			}),
			getAdminHealth: () => Promise.resolve({
				status: 'healthy', database: 'available', checked_at: '2026-10-22T10:00:00Z'
			}),
			getAdminModelMonitoring: () => Promise.resolve({
				model_available: true, model_version: 'v1', recorded_prediction_count: 0,
				recorded_model_versions: {}, explanation_available_count: 0,
				contributing_factors_available_count: 0, generated_at: '2026-10-22T10:00:00Z'
			}),
			...operationalApi,
			listAdminUsers: () => Promise.resolve({ items: [], total: 0, page: 1, page_size: 10 }),
			clearToken() {}
		}
	};
	vm.runInNewContext(adminScript, { window, document: page.document });
	await new Promise((resolve) => setImmediate(resolve));

	const rows = page.elements.get('operational-events-body').children;
	assert.equal(rows[0].children[0].textContent, 'Informational event');
	assert.equal(rows[0].children[2].textContent, 'admin');
	assert.equal(rows[0].children[6].textContent, '—');
	assert.equal(rows[1].children[0].textContent, 'Acknowledged alert · warning');
	assert.match(rows[1].children[6].textContent, /^Acknowledged by admin #23 · /);
	const acknowledgeButton = rows[2].children[6].children[0];
	assert.equal(acknowledgeButton.textContent, 'Acknowledge');
	page.elements.get('operational-events-body').listeners.click({
		target: { closest: () => acknowledgeButton }
	});
	await new Promise((resolve) => setImmediate(resolve));
	assert.equal(acknowledgements, 1);
	assert.equal(page.elements.get('operational-events-state').hidden, false);
	assert.equal(
		page.elements.get('operational-events-state').textContent,
		'Alert is not open for acknowledgement'
	);
	assert.equal(acknowledgeButton.disabled, false);
	await new Promise((resolve) => setImmediate(resolve));
	assert.equal(auditRefreshes, 2);
	page.elements.get('operational-events-body').listeners.click({
		target: { closest: () => acknowledgeButton }
	});
	await new Promise((resolve) => setImmediate(resolve));
	assert.equal(acknowledgements, 2);
	assert.equal(eventRefreshes, 2);
	assert.equal(auditRefreshes, 3);

	page.elements.get('operational-status-filter').value = 'acknowledged';
	page.elements.get('operational-severity-filter').value = 'warning';
	page.elements.get('operational-severity-filter').listeners.change();
	await new Promise((resolve) => setImmediate(resolve));
	assert.deepEqual(eventRequests.at(-1), {
		pageNumber: 1,
		pageSize: 10,
		statusFilter: 'acknowledged',
		severityFilter: 'warning'
	});
});

test('audit and operational pagination ignore stale responses', async () => {
	const page = createAdminPage();
	const operationalRequests = [];
	const auditRequests = [];
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
				user_count: 0,
				active_user_count: 0,
				total_assessments: 0,
				completed_assessments: 0,
				prediction_count: 0,
				recommendation_count: 0,
				assessment_status_distribution: {},
				risk_level_distribution: {},
				risk_category_distribution: {},
				assessment_completion_rate: null,
				generated_at: '2026-10-22T10:00:00Z'
			}),
			getAdminHealth: () => Promise.resolve({
				status: 'healthy',
				database: 'available',
				checked_at: '2026-10-22T10:00:00Z'
			}),
			getAdminModelMonitoring: () => Promise.resolve({
				model_available: true,
				model_version: 'v1',
				recorded_prediction_count: 0,
				recorded_model_versions: {},
				explanation_available_count: 0,
				contributing_factors_available_count: 0,
				generated_at: '2026-10-22T10:00:00Z'
			}),
			...emptyAdminEventApi(),
			listAdminOperationalEvents: (pageNumber, pageSize) => new Promise((resolve) => {
				operationalRequests.push({ pageNumber, pageSize, resolve });
			}),
			listAdminAuditLogs: (pageNumber, pageSize, filters) => new Promise((resolve) => {
				auditRequests.push({ pageNumber, pageSize, filters, resolve });
			}),
			listAdminUsers: () => Promise.resolve({ items: [], total: 0, page: 1, page_size: 10 }),
			clearToken() {}
		}
	};
	vm.runInNewContext(adminScript, { window, document: page.document });
	await new Promise((resolve) => setImmediate(resolve));

	assert.equal(operationalRequests.length, 1);
	assert.equal(auditRequests.length, 1);
	operationalRequests[0].resolve({
		items: [{
			id: 1, event_type: 'test', source: 'test', severity: 'info',
			summary: 'Initial event', status: 'acknowledged',
			occurred_at: '2026-10-22T10:00:00Z', acknowledged_at: null
		}],
		total: 20, page: 1, page_size: 10
	});
	auditRequests[0].resolve({
		items: [{
			id: 1, action: 'initial', actor_user_id: 1,
			target_type: 'test', target_id: '1', outcome: 'success',
			created_at: '2026-10-22T10:00:00Z'
		}],
		total: 20, page: 1, page_size: 10
	});
	await new Promise((resolve) => setImmediate(resolve));

	page.elements.get('operational-events-next').listeners.click();
	page.elements.get('audit-logs-next').listeners.click();
	page.elements.get('operational-events-previous').listeners.click();
	page.elements.get('audit-logs-previous').listeners.click();
	assert.deepEqual(operationalRequests.slice(1).map(({ pageNumber }) => pageNumber), [2, 1]);
	assert.deepEqual(auditRequests.slice(1).map(({ pageNumber }) => pageNumber), [2, 1]);

	operationalRequests[2].resolve({
		items: [{
			id: 3, event_type: 'test', source: 'test', severity: 'info',
			summary: 'Current event', status: 'acknowledged',
			occurred_at: '2026-10-22T10:00:00Z', acknowledged_at: null
		}],
		total: 20, page: 1, page_size: 10
	});
	auditRequests[2].resolve({
		items: [{
			id: 3, action: 'current', actor_user_id: 1,
			target_type: 'test', target_id: '3', outcome: 'success',
			created_at: '2026-10-22T10:00:00Z'
		}],
		total: 20, page: 1, page_size: 10
	});
	await new Promise((resolve) => setImmediate(resolve));

	operationalRequests[1].resolve({
		items: [{
			id: 2, event_type: 'test', source: 'test', severity: 'info',
			summary: 'Stale event', status: 'acknowledged',
			occurred_at: '2026-10-22T10:00:00Z', acknowledged_at: null
		}],
		total: 20, page: 2, page_size: 10
	});
	auditRequests[1].resolve({
		items: [{
			id: 2, action: 'stale', actor_user_id: 1,
			target_type: 'test', target_id: '2', outcome: 'success',
			created_at: '2026-10-22T10:00:00Z'
		}],
		total: 20, page: 2, page_size: 10
	});
	await new Promise((resolve) => setImmediate(resolve));

	assert.match(page.elements.get('operational-events-page-summary').textContent, /^Page 1 of 2/);
	assert.equal(page.elements.get('operational-events-body').children[0].children[3].textContent, 'Current event');
	assert.match(page.elements.get('audit-logs-page-summary').textContent, /^Page 1 of 2/);
	assert.equal(page.elements.get('audit-logs-body').children[0].children[0].textContent, 'current');

	page.elements.get('operational-events-next').listeners.click();
	page.elements.get('audit-logs-next').listeners.click();
	assert.deepEqual(operationalRequests.slice(3).map(({ pageNumber }) => pageNumber), [2]);
	assert.deepEqual(auditRequests.slice(3).map(({ pageNumber }) => pageNumber), [2]);
	operationalRequests[3].resolve({ items: [], total: 0, page: 2, page_size: 10 });
	auditRequests[3].resolve({ items: [], total: 0, page: 2, page_size: 10 });
	await new Promise((resolve) => setImmediate(resolve));
	assert.equal(operationalRequests.length, 5);
	assert.equal(operationalRequests[4].pageNumber, 1);
	assert.equal(auditRequests.length, 5);
	assert.equal(auditRequests[4].pageNumber, 1);
	operationalRequests[4].resolve({ items: [], total: 0, page: 1, page_size: 10 });
	auditRequests[4].resolve({ items: [], total: 0, page: 1, page_size: 10 });
	await new Promise((resolve) => setImmediate(resolve));
	assert.match(page.elements.get('operational-events-page-summary').textContent, /^Page 1 of 1/);
	assert.equal(page.elements.get('operational-events-state').textContent, 'No operational events have been recorded.');
	assert.match(page.elements.get('audit-logs-page-summary').textContent, /^Page 1 of 1/);
	assert.equal(page.elements.get('audit-logs-state').textContent, 'No audit records have been recorded.');

	page.elements.get('audit-action-filter').value = 'user.deactivated';
	page.elements.get('audit-actor-filter').value = '7';
	page.elements.get('audit-outcome-filter').value = 'success';
	page.elements.get('audit-date-from').value = '2026-10-01';
	page.elements.get('audit-date-to').value = '2026-10-27';
	page.elements.get('audit-filter-form').listeners.submit({ preventDefault() {} });
	assert.equal(auditRequests[5].pageNumber, 1);
	assert.equal(JSON.stringify(auditRequests[5].filters), JSON.stringify({
		action: 'user.deactivated',
		actorUserId: '7',
		outcome: 'success',
		createdAfter: '2026-10-01T00:00:00.000Z',
		createdBefore: '2026-10-27T23:59:59.999Z'
	}));
	auditRequests[5].resolve({ items: [], total: 0, page: 1, page_size: 10 });
	await new Promise((resolve) => setImmediate(resolve));
	assert.equal(page.elements.get('audit-logs-state').textContent, 'No audit records match these filters.');
	page.elements.get('clear-audit-filters').listeners.click();
	assert.equal(auditRequests[6].pageNumber, 1);
	assert.equal(JSON.stringify(auditRequests[6].filters), JSON.stringify({
		action: '', actorUserId: '', outcome: '', createdAfter: '', createdBefore: ''
	}));
});

test('overview record cards open the selected filtered record list', async () => {
	const page = createAdminPage();
	const calls = [];
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
				total_assessments: 1,
				completed_assessments: 1,
				prediction_count: 1,
				recommendation_count: 1,
				assessment_status_distribution: { completed: 1 },
				risk_level_distribution: { low: 1 },
				risk_category_distribution: { financial_access: 1 },
				assessment_completion_rate: 1,
				generated_at: '2026-10-22T10:00:00Z'
			}),
			getAdminHealth: () => Promise.resolve({
				status: 'healthy',
				database: 'available',
				checked_at: '2026-10-22T10:00:00Z'
			}),
			getAdminModelMonitoring: () => Promise.resolve({
				model_available: true,
				model_version: 'v1',
				recorded_prediction_count: 1,
				recorded_model_versions: { v1: 1 },
				explanation_available_count: 1,
				contributing_factors_available_count: 1,
				generated_at: '2026-10-22T10:00:00Z'
			}),
			...emptyAdminEventApi(),
			listAdminUsers: () => Promise.resolve({ items: [], total: 0, page: 1, page_size: 10 }),
			listAdminRecords(type, search, filter, pageNumber, pageSize) {
				calls.push({ type, search, filter, pageNumber, pageSize });
				return Promise.resolve({
					record_type: type,
					items: [{
						id: 42,
						user_id: 8,
						full_name: 'Account Holder',
						email: 'account@example.com',
						status: 'completed',
						created_at: '2026-10-22T10:00:00Z'
					}],
					total: 1,
					page: pageNumber,
					page_size: pageSize
				});
			},
			clearToken() {}
		}
	};
	vm.runInNewContext(adminScript, { window, document: page.document });
	await new Promise((resolve) => setImmediate(resolve));

	page.statCards[3].listeners.click();
	await new Promise((resolve) => setImmediate(resolve));
	assert.equal(calls.length, 1);
	assert.deepEqual(calls[0], {
		type: 'assessments',
		search: '',
		filter: 'completed',
		pageNumber: 1,
		pageSize: 10
	});
	assert.equal(page.elements.get('admin-records-section').hidden, false);
	assert.equal(page.elements.get('admin-records-table').hidden, false);
	assert.equal(page.elements.get('admin-records-body').children[0].children[0].textContent, '42');
});

test('records sidebar link opens assessments when no record view has been selected', async () => {
	const page = createAdminPage();
	const calls = [];
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
				user_count: 0,
				active_user_count: 0,
				total_assessments: 0,
				completed_assessments: 0,
				prediction_count: 0,
				recommendation_count: 0,
				assessment_status_distribution: {},
				risk_level_distribution: {},
				risk_category_distribution: {},
				assessment_completion_rate: null,
				generated_at: '2026-10-22T10:00:00Z'
			}),
			getAdminHealth: () => Promise.resolve({
				status: 'healthy',
				database: 'available',
				checked_at: '2026-10-22T10:00:00Z'
			}),
			getAdminModelMonitoring: () => Promise.resolve({
				model_available: true,
				model_version: 'v1',
				recorded_prediction_count: 0,
				recorded_model_versions: {},
				explanation_available_count: 0,
				contributing_factors_available_count: 0,
				generated_at: '2026-10-22T10:00:00Z'
			}),
			...emptyAdminEventApi(),
			listAdminUsers: () => Promise.resolve({ items: [], total: 0, page: 1, page_size: 10 }),
			listAdminRecords(type, search, filter, pageNumber, pageSize) {
				calls.push({ type, search, filter, pageNumber, pageSize });
				return Promise.resolve({
					record_type: type,
					items: [],
					total: 0,
					page: pageNumber,
					page_size: pageSize
				});
			},
			clearToken() {}
		}
	};
	vm.runInNewContext(adminScript, { window, document: page.document });
	await new Promise((resolve) => setImmediate(resolve));

	assert.equal(page.elements.get('admin-records-section').hidden, true);
	page.recordsNavLink.listeners.click();
	await new Promise((resolve) => setImmediate(resolve));
	assert.equal(page.elements.get('admin-records-section').hidden, false);
	assert.equal(page.elements.get('admin-records-heading').textContent, 'Assessments');
	assert.deepEqual(calls, [{
		type: 'assessments',
		search: '',
		filter: '',
		pageNumber: 1,
		pageSize: 10
	}]);
});

test('record views display explicit empty results', async () => {
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
			getSystemAnalytics: () => Promise.resolve({
				user_count: 0,
				active_user_count: 0,
				total_assessments: 0,
				completed_assessments: 0,
				prediction_count: 0,
				recommendation_count: 0,
				assessment_status_distribution: {},
				risk_level_distribution: {},
				risk_category_distribution: {},
				assessment_completion_rate: null,
				generated_at: '2026-10-22T10:00:00Z'
			}),
			getAdminHealth: () => Promise.resolve({
				status: 'healthy',
				database: 'available',
				checked_at: '2026-10-22T10:00:00Z'
			}),
			getAdminModelMonitoring: () => Promise.resolve({
				model_available: true,
				model_version: 'v1',
				recorded_prediction_count: 0,
				recorded_model_versions: {},
				explanation_available_count: 0,
				contributing_factors_available_count: 0,
				generated_at: '2026-10-22T10:00:00Z'
			}),
			...emptyAdminEventApi(),
			listAdminUsers: () => Promise.resolve({ items: [], total: 0, page: 1, page_size: 10 }),
			listAdminRecords(type, _search, _filter, pageNumber, pageSize) {
				return Promise.resolve({
					record_type: type,
					items: [],
					total: 0,
					page: pageNumber,
					page_size: pageSize
				});
			},
			clearToken() {}
		}
	};
	vm.runInNewContext(adminScript, { window, document: page.document });
	await new Promise((resolve) => setImmediate(resolve));
	page.statCards[5].listeners.click();
	await new Promise((resolve) => setImmediate(resolve));

	assert.equal(page.elements.get('admin-records-table').hidden, true);
	assert.equal(page.elements.get('record-list-state').hidden, false);
	assert.equal(page.elements.get('record-list-state').textContent, 'No records are available yet.');
	assert.equal(page.elements.get('record-page-summary').textContent, 'No records');
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
			getAdminModelMonitoring: () => Promise.resolve({
				model_available: false,
				model_version: null,
				recorded_prediction_count: 0,
				recorded_model_versions: {},
				explanation_available_count: 0,
				contributing_factors_available_count: 0,
				generated_at: '2026-10-22T10:00:00Z'
			}),
			...emptyAdminEventApi(),
			listAdminOperationalEvents: () => Promise.reject(new Error('Recorded events unavailable')),
			listAdminAuditLogs: () => Promise.reject(new Error('Audit records unavailable')),
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
	assert.equal(page.elements.get('assessment-distribution').textContent, 'Analytics unavailable');
	assert.equal(page.elements.get('risk-distribution').textContent, 'Analytics unavailable');
	assert.equal(page.elements.get('risk-category-distribution').textContent, 'Analytics unavailable');
	assert.equal(
		page.elements.get('assessment-completion-rate').textContent,
		'Unavailable: Analytics unavailable'
	);
	assert.match(page.elements.get('operational-events-state').textContent, /Recorded events unavailable/);
	assert.match(page.elements.get('audit-logs-state').textContent, /Audit records unavailable/);
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
				risk_category_distribution: {},
				assessment_completion_rate: null,
				generated_at: '2026-10-22T10:00:00Z'
			}),
			getAdminHealth: () => Promise.resolve({
				status: 'healthy',
				database: 'available',
				checked_at: '2026-10-22T10:00:00Z'
			}),
			getAdminModelMonitoring: () => Promise.resolve({
				model_available: true,
				model_version: 'v1',
				recorded_prediction_count: 0,
				recorded_model_versions: {},
				explanation_available_count: 0,
				contributing_factors_available_count: 0,
				generated_at: '2026-10-22T10:00:00Z'
			}),
			...emptyAdminEventApi(),
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
	await window.FinpathAPI.listAdminUsers('', 1, 10, true);
	await window.FinpathAPI.listAdminRecords('predictions', 'owner', 'high', 2, 20);
	await window.FinpathAPI.getAdminModelMonitoring();
	await window.FinpathAPI.getAdminOperationalSummary();
	await window.FinpathAPI.listAdminOperationalEvents(2, 20, 'open', 'error');
	await window.FinpathAPI.acknowledgeAdminAlert(17);
	await window.FinpathAPI.listAdminAuditLogs(3, 10, {
		action: 'user.deactivated',
		actorUserId: '4',
		outcome: 'success',
		createdAfter: '2026-10-01T00:00:00.000Z',
		createdBefore: '2026-10-31T23:59:59.999Z'
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
	assert.equal(calls[6].url, 'https://api.example.invalid/api/v1/admin/users?is_active=true&page=1&page_size=10');
	assert.equal(calls[7].url, 'https://api.example.invalid/api/v1/admin/records/predictions?search=owner&filter_value=high&page=2&page_size=20');
	assert.equal(calls[7].options.method, 'GET');
	assert.equal(calls[8].url, 'https://api.example.invalid/api/v1/admin/model');
	assert.equal(calls[8].options.method, 'GET');
	assert.equal(calls[9].url, 'https://api.example.invalid/api/v1/admin/operational-summary');
	assert.equal(calls[9].options.method, 'GET');
	assert.equal(calls[10].url, 'https://api.example.invalid/api/v1/admin/operational-events?status_filter=open&severity_filter=error&page=2&page_size=20');
	assert.equal(calls[10].options.method, 'GET');
	assert.equal(calls[11].url, 'https://api.example.invalid/api/v1/admin/alerts/17/acknowledge');
	assert.equal(calls[11].options.method, 'POST');
	assert.equal(calls[12].url, 'https://api.example.invalid/api/v1/admin/audit-logs?action=user.deactivated&actor_user_id=4&outcome=success&created_after=2026-10-01T00%3A00%3A00.000Z&created_before=2026-10-31T23%3A59%3A59.999Z&page=3&page_size=10');
	assert.equal(calls[12].options.method, 'GET');
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
	assert.match(adminHtml, /data-record-type="assessments"/);
	assert.match(adminHtml, /data-record-type="predictions"/);
	assert.match(adminHtml, /data-record-type="recommendations"/);
	assert.match(adminHtml, /id="admin-records-section"/);
	assert.match(adminHtml, /id="records-previous"/);
	assert.match(adminHtml, /id="records-next"/);
	assert.match(adminHtml, /id="model-monitoring-section"/);
	assert.match(adminHtml, /id="operational-events-section"/);
	assert.match(adminHtml, /id="audit-logs-section"/);
	assert.match(adminHtml, /id="audit-filter-form"/);
	assert.match(adminHtml, /id="audit-outcome-filter"/);
	assert.match(adminHtml, /id="operational-status-filter"/);
	assert.match(adminHtml, /id="operational-severity-filter"/);
	for (const section of [
		'overview-section',
		'admin-records-section',
		'model-monitoring-section',
		'health-section',
		'operational-events-section',
		'audit-logs-section',
		'users-section'
	]) {
		assert.match(adminHtml, new RegExp(`href="#${section}"`));
	}
});
