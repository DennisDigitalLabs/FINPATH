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
const landingStyles = fs.readFileSync(
	path.join(__dirname, '..', 'frontend', 'css', 'landing.css'),
	'utf8'
);
const renderConfig = fs.readFileSync(
	path.join(__dirname, '..', 'render.yaml'),
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

test('login returns standard users to supported internal destinations only', async () => {
	assert.equal((await submitLogin('user', '/login', '?next=%2Fassessment')).destination, '/assessment.html');
	assert.equal((await submitLogin('user', '/login', '?next=%2Fprofile')).destination, '/profile.html');
	assert.equal((await submitLogin('user', '/login', '?next=%2Fprediction')).destination, '/prediction.html');
	assert.equal((await submitLogin('user', '/login', '?next=%2Fprediction%3Fprediction_id%3D42')).destination, '/prediction.html?prediction_id=42');
	assert.equal((await submitLogin('user', '/login', '?next=%2Frecommendations')).destination, '/recommendations.html');
	assert.equal((await submitLogin('user', '/login', '?next=%2Frecommendations%3Fprediction_id%3D42')).destination, '/recommendations.html?prediction_id=42');
	assert.equal((await submitLogin('user', '/login', '?next=https%3A%2F%2Fexample.invalid')).destination, '/dashboard.html');
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

test('registration page excludes login and register tabs and explains standard-user access', () => {
	assert.doesNotMatch(registerHtml, /class="auth-tabs"|>Login<\/a>|>Register<\/a>/);
	const orderedContent = [
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
	assert.match(registerHtml, /Already have an account\? <a href="\/login">Sign In<\/a>/);
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

test('landing provides separate ordinary-user and protected-administrator access', () => {
	assert.match(landingHtml, /<section class="account-access-card" aria-labelledby="user-access-title">[\s\S]*<h3 id="user-access-title">Ordinary User<\/h3>[\s\S]*href="\/register">Create Account<\/a>[\s\S]*href="\/login">Log In<\/a>/);
	assert.match(landingHtml, /<section class="account-access-card" aria-labelledby="admin-access-title">[\s\S]*<h3 id="admin-access-title">Administrator<\/h3>[\s\S]*Sign in with your existing administrator account\.[\s\S]*href="\/admin\/login\?next=%2Fadmin">Log In<\/a>/);
	const adminAccessSection = landingHtml.match(/<section class="account-access-card" aria-labelledby="admin-access-title">([\s\S]*?)<\/section>/);
	assert.ok(adminAccessSection);
	assert.doesNotMatch(adminAccessSection[1], /Create Account|href="\/register"|href="\/admin"/);
	assert.ok(landingHtml.indexOf('class="account-access-section"') < landingHtml.indexOf('class="value-strip"'));
	assert.match(landingHtml, /<strong>Ordinary User<\/strong>[\s\S]*href="\/register">Create Account<\/a>[\s\S]*href="\/login">Log In<\/a>/);
	assert.match(landingHtml, /<strong>Administrator<\/strong>[\s\S]*href="\/admin\/login\?next=%2Fadmin">Log In<\/a>/);
	assert.doesNotMatch(landingHtml, /href="\/admin">Create Account<\/a>/);
	assert.match(landingStyles, /\.account-access-grid\s*\{[^}]*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/);
	assert.match(landingStyles, /@media \(max-width: 48rem\)[\s\S]*?\.account-access-grid\s*\{[^}]*grid-template-columns:\s*1fr/);
});

test('deployed authentication and recovery routes use the ordinary-user login page', () => {
	assert.match(renderConfig, /source: \/login\s+destination: \/login\/index\.html/);
	assert.match(renderConfig, /source: \/forgot-password\s+destination: \/login\/index\.html/);
	assert.doesNotMatch(renderConfig, /source: \/login\s+destination: \/admin\/login\/index\.html/);
});

test('landing and dashboard provide the requested navigation links', () => {
	assert.match(landingHtml, /class="btn btn-outline nav-admin" href="\/admin\/login\?next=%2Fadmin">Admin<\/a>/);
	assert.match(landingHtml, /class="mobile-menu-panel">[\s\S]*href="\/admin\/login\?next=%2Fadmin">Admin<\/a>[\s\S]*href="\/login">Log In<\/a>[\s\S]*href="\/register">Get Started<\/a>/);
	assert.match(landingHtml, /class="btn btn-outline nav-login" href="\/login">Log In<\/a>/);
	assert.doesNotMatch(adminLoginHtml, /href="\/register"/);
	assert.match(dashboardHtml, /class="nav-link" href="\/">Home<\/a>/);
});

test('all canonical application pages include the organization footer', () => {
	const pagePaths = [
		'frontend/admin.html',
		'frontend/index.html',
		'frontend/login.html',
		'frontend/register.html',
		'frontend/reset-password.html',
		'frontend/forgot-password.html',
		'frontend/forgot-password/index.html',
		'frontend/register/index.html',
		'frontend/login/index.html',
		'frontend/admin/login/index.html',
		'frontend/admin/index.html',
		'frontend/dashboard.html',
		'frontend/assessment.html',
		'frontend/prediction.html',
		'frontend/recommendations.html',
		'frontend/analytics.html',
		'frontend/profile.html',
		'frontend/reset-password/index.html'
	];
	const requiredFooterText = /Designed and Developed by[\s\S]{0,40}Dennis Digital Labs[\s\S]{0,30}&amp; AI[\s\S]*© 2026 Financial Inclusion, Brighter Futures\./;

	for (const pagePath of pagePaths) {
		const html = fs.readFileSync(path.join(__dirname, '..', pagePath), 'utf8');
		assert.match(html, /<footer\b/, `${pagePath} should have a footer`);
		assert.match(html, requiredFooterText, `${pagePath} should have the organization credit`);
	}
});
