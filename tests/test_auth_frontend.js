'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const authScript = fs.readFileSync(
	path.join(__dirname, '..', 'frontend', 'js', 'auth.js'),
	'utf8'
);
const apiScript = fs.readFileSync(
	path.join(__dirname, '..', 'frontend', 'js', 'api.js'),
	'utf8'
);
const landingHtml = fs.readFileSync(
	path.join(__dirname, '..', 'frontend', 'index.html'),
	'utf8'
);
const dashboardHtml = fs.readFileSync(
	path.join(__dirname, '..', 'frontend', 'dashboard.html'),
	'utf8'
);
const registerHtml = fs.readFileSync(
	path.join(__dirname, '..', 'frontend', 'register.html'),
	'utf8'
);

function createElement(values = {}) {
	return {
		addEventListener(name, callback) { this['on' + name] = callback; },
		checkValidity() { return true; },
		focus() {},
		reportValidity() {},
		...values
	};
}

async function submitForgotPassword(requestPasswordReset) {
	const elements = new Map();
	const loginForm = createElement();
	const forgotForm = createElement({ reset() {} });
	const submitButton = createElement();
	const forgotStatus = createElement({ textContent: '' });
	const emailField = createElement({ value: 'test@example.invalid' });
	const loginStatus = createElement({ textContent: '' });
	const forgotLink = createElement();
	const forgotView = createElement();
	const forgotBack = createElement();
	const loginHeading = createElement({ textContent: '' });
	const loginDescription = createElement({ textContent: '' });
	const loginSwitch = createElement();

	for (const [id, element] of Object.entries({
		'auth-form': loginForm,
		'login-email': createElement({ value: '' }),
		'login-password': createElement({ value: '' }),
		'login-email-error': createElement(),
		'login-password-error': createElement(),
		'login-error': createElement(),
		'login-status': loginStatus,
		'forgot-password-link': forgotLink,
		'forgot-password-view': forgotView,
		'forgot-password-form': forgotForm,
		'forgot-password-back': forgotBack,
		'forgot-password-status': forgotStatus,
		'forgot-password-submit': submitButton,
		'login-title': loginHeading,
		'auth-heading-description': loginDescription,
		'forgot-password-email': emailField
	})) {
		elements.set(id, element);
	}

	const document = {
		getElementById(id) { return elements.get(id) || createElement(); },
		querySelectorAll() { return []; },
		querySelector() { return loginSwitch; }
	};
	const window = {
		FinpathAPI: { requestPasswordReset },
		location: { hash: '#forgot-password', pathname: '/login', search: '' },
		history: { replaceState() {} }
	};

	vm.runInNewContext(authScript, { document, window, URLSearchParams });
	forgotLink.onclick({ preventDefault() {} });
	forgotForm.onsubmit({ preventDefault() {} });
	await new Promise((resolve) => setImmediate(resolve));

	return { status: forgotStatus.textContent, buttonDisabled: submitButton.disabled };
}

test('forgot password reports unavailable service instead of implying success', async () => {
	const result = await submitForgotPassword(() => Promise.reject(
		Object.assign(new Error('Password reset is temporarily unavailable.'), { status: 503 })
	));

	assert.equal(result.status, 'Password reset is temporarily unavailable. Please try again later.');
	assert.equal(result.buttonDisabled, false);
});

test('forgot password keeps the account-enumeration-safe success message', async () => {
	const result = await submitForgotPassword(() => Promise.resolve({
		message: 'If an account exists for that email, a password reset link will be sent shortly.'
	}));

	assert.equal(result.status, 'If an account exists for that email, a password reset link will be sent shortly. Check your inbox, or try again later.');
	assert.equal(result.buttonDisabled, false);
});

test('registration does not require acknowledgement of unpublished policy pages', () => {
	assert.doesNotMatch(registerHtml, /name="terms"/);
	assert.doesNotMatch(registerHtml, /href="#(?:terms|privacy)"/);
	assert.doesNotMatch(authScript, /a\[href="#terms"\]/);
});

function createApiHarness(responseStatus, responseBody) {
	const values = new Map();
	const storage = {
		getItem(key) { return values.get(key) || null; },
		setItem(key, value) { values.set(key, value); },
		removeItem(key) { values.delete(key); }
	};
	const window = {
		FINPATH_CONFIG: { API_BASE_URL: 'https://api.example.invalid' },
		localStorage: storage,
		sessionStorage: storage,
		fetch() {
			return Promise.resolve({
				ok: responseStatus >= 200 && responseStatus < 300,
				status: responseStatus,
				text() { return Promise.resolve(JSON.stringify(responseBody)); }
			});
		}
	};
	vm.runInNewContext(apiScript, { window });
	return { api: window.FinpathAPI, storage };
}

test('login 401 reports incorrect credentials without clearing an existing session', async () => {
	const { api, storage } = createApiHarness(401, { detail: 'Invalid email or password' });
	storage.setItem('finpath_access_token', 'existing-session');

	await assert.rejects(api.login({ email: 'user@example.invalid', password: 'wrong' }), {
		message: 'Incorrect email or password.'
	});
	assert.equal(api.getToken(), 'existing-session');
});

test('protected-resource 401 still reports an expired session and clears its token', async () => {
	const { api, storage } = createApiHarness(401, { detail: 'Not authenticated' });
	storage.setItem('finpath_access_token', 'expired-session');

	await assert.rejects(api.getAuthenticated('/api/v1/auth/me'), {
		message: 'Your session has expired. Please sign in again.'
	});
	assert.equal(api.getToken(), null);
});

test('landing and dashboard provide the requested navigation links', () => {
	assert.match(landingHtml, /class="btn btn-outline nav-admin" href="\/admin">Admin<\/a>/);
	assert.match(landingHtml, /class="mobile-menu-panel">[\s\S]*href="\/admin">Admin<\/a>/);
	assert.match(dashboardHtml, /class="nav-link" href="\/">Home<\/a>/);
});
