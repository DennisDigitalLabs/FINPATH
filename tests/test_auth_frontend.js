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
