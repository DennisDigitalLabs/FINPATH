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
	path.join(__dirname, '..', 'frontend', 'register', 'index.html'),
	'utf8'
);
const adminLoginHtml = fs.readFileSync(
	path.join(__dirname, '..', 'frontend', 'admin', 'login', 'index.html'),
	'utf8'
);
const userLoginHtml = fs.readFileSync(
	path.join(__dirname, '..', 'frontend', 'login', 'index.html'),
	'utf8'
);

function createElement(values = {}) {
	return {
		addEventListener(name, callback) { this['on' + name] = callback; },
		setAttribute() {},
		closest() { return null; },
		classList: { toggle() {} },
		checkValidity() { return true; },
		focus() {},
		reportValidity() {},
		...values
	};
}

async function submitLogin(role, pathname = '/admin/login', search = '?next=%2Fadmin', loginStatus) {
	const elements = new Map();
	const loginForm = createElement();
	const email = createElement({ value: 'owner@example.com' });
	const password = createElement({ value: 'OwnerPassword123' });
	const loginError = createElement({ hidden: true, textContent: '' });
	const status = createElement({ textContent: '' });
	const loginSuccess = createElement({ hidden: true });
	let token = 'existing-session';
	const document = {
		getElementById(id) { return elements.get(id); }
	};
	[
		['auth-form', loginForm],
		['login-email', email],
		['login-password', password],
		['login-email-error', createElement()],
		['login-password-error', createElement()],
		['login-error', loginError],
		['login-success', loginSuccess],
		['auth-account-label', createElement({ textContent: '' })],
		['login-title', createElement({ textContent: '' })],
		['auth-heading-description', createElement({ textContent: '' })],
		['login-tab', createElement({ href: '' })],
		['login-status', status]
	].forEach(([id, element]) => elements.set(id, element));
	const window = {
		location: { pathname, search, href: '' },
		FinpathAPI: {
			login: () => {
				if (loginStatus) {
					return Promise.reject(Object.assign(new Error('Incorrect email or password.'), {
						status: loginStatus
					}));
				}
				token = 'attempt-session';
				return Promise.resolve({});
			},
			me: () => Promise.resolve({ role }),
			clearToken() { token = null; }
		}
	};
	class FormDataStub {
		get(name) {
			return ({ email: email.value, password: password.value, remember: null })[name];
		}
	}
	vm.runInNewContext(authScript, { document, window, URLSearchParams, FormData: FormDataStub });
	loginForm.onsubmit({ preventDefault() {} });
	await new Promise((resolve) => setImmediate(resolve));
	return {
		destination: window.location.href,
		heading: elements.get('login-title').textContent,
		description: elements.get('auth-heading-description').textContent,
		loginLink: elements.get('login-tab').href,
		errorMessage: loginError.textContent,
		errorHidden: loginError.hidden,
		token
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

test('successful registration return displays a clear sign-in message', () => {
	const elements = new Map([
		['auth-form', createElement()],
		['login-email', createElement()],
		['login-password', createElement()],
		['login-email-error', createElement()],
		['login-password-error', createElement()],
		['login-error', createElement()],
		['login-success', createElement({ hidden: true })],
		['login-status', createElement()],
		['login-title', createElement({ textContent: '' })],
		['auth-heading-description', createElement({ textContent: '' })]
	]);
	const document = {
		getElementById(id) { return elements.get(id); }
	};
	const window = { location: { search: '?registered=1' } };

	vm.runInNewContext(authScript, { document, window, URLSearchParams });

	assert.equal(elements.get('login-success').hidden, false);
	assert.equal(elements.get('login-success').textContent, 'Your account was created. Sign in to continue.');
});

test('login preserves admin destination for administrators and denies it to normal users', async () => {
	assert.equal((await submitLogin('admin')).destination, '/admin');
	const userOnAdminLogin = await submitLogin('user');
	assert.equal(userOnAdminLogin.destination, '');
	assert.equal(userOnAdminLogin.errorMessage, 'Invalid administrator credentials or insufficient privileges.');
	assert.equal(userOnAdminLogin.token, null);
});

test('public login uses standard-user wording while admin accounts still reach admin dashboard', async () => {
	const admin = await submitLogin('admin', '/login', '?next=%2Fdashboard');
	const user = await submitLogin('user', '/login', '?next=%2Fdashboard');

	assert.equal(admin.destination, '/admin');
	assert.equal(admin.heading, 'Welcome Back');
	assert.equal(admin.description, 'Sign in to continue to your FINPATH account.');
	assert.equal(admin.loginLink, '/login');
	assert.equal(user.destination, '/dashboard.html');
	assert.equal(user.heading, 'Welcome Back');
});

test('administrator login gives identical generic errors and clears sessions for every rejected attempt', async () => {
	const standardUser = await submitLogin('user');
	const unknownEmail = await submitLogin('admin', '/admin/login', '?next=%2Fadmin', 401);
	const wrongPassword = await submitLogin('admin', '/admin/login', '?next=%2Fadmin', 401);
	const failureMessage = 'Invalid administrator credentials or insufficient privileges.';

	for (const attempt of [standardUser, unknownEmail, wrongPassword]) {
		assert.equal(attempt.errorMessage, failureMessage);
		assert.equal(attempt.errorHidden, false);
		assert.equal(attempt.token, null);
		assert.equal(attempt.destination, '');
	}
});

test('public login page uses the shared auth flow and exposes only user registration', () => {
	assert.match(userLoginHtml, /<title>FINPATH \| Sign In<\/title>/);
	assert.match(userLoginHtml, /id="auth-form"[\s\S]*name="email"[\s\S]*name="password"[\s\S]*href="#forgot-password"[\s\S]*>Login <span/);
	assert.match(userLoginHtml, /href="\/register">Register<\/a>/);
	assert.match(userLoginHtml, /src="\/js\/auth\.js"/);
	assert.doesNotMatch(userLoginHtml, /window\.location\.replace/);
});

test('admin login has no public registration and explains protected provisioning', () => {
	assert.match(adminLoginHtml, /<title>FINPATH Admin Panel \| Administrator Login<\/title>/);
	assert.match(adminLoginHtml, /FINPATH administration[\s\S]*Manage FINPATH\.[\s\S]*Protected administration/);
	assert.match(adminLoginHtml, /id="login-title">Administrator Login/);
	assert.match(adminLoginHtml, /name="email"[\s\S]*name="password"[\s\S]*Remember me[\s\S]*Forgot password\?[\s\S]*>Login <span/);
	assert.match(adminLoginHtml, /<\/form>\s*<p class="auth-switch">Administrator accounts are created through protected setup or by an existing administrator/);
	assert.doesNotMatch(adminLoginHtml, /href="\/register"|Create (?:a|an) account|Sign up/i);
	assert.doesNotMatch(adminLoginHtml, /href="[^"]*\.html/);
});

test('admin login identifies the FINPATH Admin Panel', async () => {
	await submitLogin('admin');
	const elements = new Map();
	const loginHeading = createElement({ textContent: '' });
	const description = createElement({ textContent: '' });
	const form = createElement();
	const email = createElement({ value: 'owner@example.com' });
	const password = createElement({ value: 'OwnerPassword123' });
	for (const [id, element] of [
		['auth-form', form],
		['login-email', email],
		['login-password', password],
		['login-email-error', createElement()],
		['login-password-error', createElement()],
		['login-error', createElement()],
		['login-status', createElement({ textContent: '' })],
		['login-title', loginHeading],
		['auth-heading-description', description],
		['login-tab', createElement()]
	]) elements.set(id, element);
	const document = { getElementById(id) { return elements.get(id); } };
	const window = {
		location: { pathname: '/admin/login', search: '?next=%2Fadmin', href: '' },
		FinpathAPI: {
			login: () => Promise.resolve({}),
			me: () => Promise.resolve({ role: 'admin' })
		}
	};
	class FormDataStub {
		get(name) { return ({ email: email.value, password: password.value, remember: null })[name]; }
	}

	vm.runInNewContext(authScript, { document, window, URLSearchParams, FormData: FormDataStub });
	form.onsubmit({ preventDefault() {} });
	await new Promise((resolve) => setImmediate(resolve));

	assert.equal(loginHeading.textContent, 'Administrator Login');
	assert.equal(description.textContent, 'Sign in to continue to the FINPATH Admin Panel.');
	assert.equal(window.location.href, '/admin');
});

test('registration page follows the reference order and explains standard-user access', () => {
	const orderedContent = [
		registerHtml.indexOf('>Login</a>'),
		registerHtml.indexOf('>Register</a>'),
		registerHtml.indexOf('id="register-title">Create Account'),
		registerHtml.indexOf('Public registration creates a standard FINPATH user account.'),
		registerHtml.indexOf('for="register-name">Full Name'),
		registerHtml.indexOf('for="register-email">Email Address'),
		registerHtml.indexOf('for="register-password">Password'),
		registerHtml.indexOf('for="register-confirm-password">Confirm password'),
		registerHtml.indexOf('>Create Account <span')
	];

	assert.ok(orderedContent.every((position) => position >= 0));
	assert.deepEqual(orderedContent, [...orderedContent].sort((left, right) => left - right));
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
	assert.match(landingHtml, /class="btn btn-outline nav-admin" href="\/admin\/login\?next=%2Fadmin">Admin<\/a>/);
	assert.match(landingHtml, /class="mobile-menu-panel">[\s\S]*href="\/admin\/login\?next=%2Fadmin">Admin<\/a>[\s\S]*href="\/login">Log In<\/a>[\s\S]*href="\/register">Get Started<\/a>/);
	assert.match(landingHtml, /href="\/register">Get Started<\/a>/);
	assert.match(landingHtml, /class="btn btn-outline nav-login" href="\/login">Log In<\/a>/);
	assert.doesNotMatch(adminLoginHtml, /href="\/register"/);
	assert.match(dashboardHtml, /class="nav-link" href="\/">Home<\/a>/);
});
