(function () {
	'use strict';

	document.querySelectorAll('a[href="#terms"], a[href="#privacy"]').forEach(function (link) { link.remove(); });

	function showError(element, message) {
		element.textContent = message;
		element.hidden = false;
	}

	function clearError(element) {
		element.textContent = '';
		element.hidden = true;
	}

	function setFieldState(field, errorElement, isValid, message) {
		var wrap = field.closest('.input-wrap');
		field.setAttribute('aria-invalid', String(!isValid));
		field.classList.toggle('is-invalid', !isValid);
		if (wrap) {
			wrap.classList.toggle('is-invalid', !isValid);
		}
		if (!isValid && message) {
			showError(errorElement, message);
		} else {
			clearError(errorElement);
		}
	}

	var loginForm = document.getElementById('auth-form');
	if (loginForm) {
		var emailField = document.getElementById('login-email');
		var passwordField = document.getElementById('login-password');
		var emailError = document.getElementById('login-email-error');
		var passwordError = document.getElementById('login-password-error');
		var loginError = document.getElementById('login-error');
		var status = document.getElementById('login-status');

		function validateEmailField(forceDisplay) {
			var value = (emailField.value || '').trim();
			var isEmpty = value.length === 0;
			var isValid = !isEmpty && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
			if (isEmpty && !forceDisplay) {
				setFieldState(emailField, emailError, true, '');
				return false;
			}
			setFieldState(emailField, emailError, isValid, isValid ? '' : 'Enter a valid email address.');
			return isValid;
		}

		function validatePasswordField(forceDisplay) {
			var value = passwordField.value || '';
			var isEmpty = value.length === 0;
			if (isEmpty && !forceDisplay) {
				setFieldState(passwordField, passwordError, true, '');
				return false;
			}
			setFieldState(passwordField, passwordError, !isEmpty, isEmpty ? 'Enter your password.' : '');
			return !isEmpty;
		}

		emailField.addEventListener('input', function () {
			validateEmailField(false);
		});
		passwordField.addEventListener('input', function () {
			validatePasswordField(false);
		});

		loginForm.addEventListener('submit', function (event) {
			event.preventDefault();
			var emailValid = validateEmailField(true);
			var passwordValid = validatePasswordField(true);
			if (!emailValid || !passwordValid) {
				status.textContent = '';
				return;
			}
			clearError(loginError);
			status.textContent = 'Signing you in...';
			var data = new FormData(loginForm);
			var allowedDestinations = ['/admin', '/dashboard', '/analytics', '/recommendations'];
			var requestedDestination = new URLSearchParams(window.location.search).get('next');
			window.FinpathAPI.login({ email: data.get('email'), password: data.get('password') }, data.get('remember') === 'on')
				.then(function () { return window.FinpathAPI.me(); })
				.then(function (user) {
					var isAdmin = user && user.role === 'admin';
					var fallback = isAdmin ? '/admin' : '/dashboard';
					var destination = allowedDestinations.indexOf(requestedDestination) !== -1 ? requestedDestination : fallback;
					var recommendationDestination = requestedDestination && requestedDestination.match(/^\/recommendations\?prediction_id=(\d+)$/);
					if (recommendationDestination && Number.isSafeInteger(Number(recommendationDestination[1])) && Number(recommendationDestination[1]) > 0) {
						destination = '/recommendations?prediction_id=' + recommendationDestination[1];
					}
					else if (requestedDestination && requestedDestination.indexOf('/recommendations') === 0) {
						destination = fallback;
					}
					if (destination === '/admin' && !isAdmin) destination = fallback;
					window.location.href = destination;
				})
				.catch(function (reason) { status.textContent = ''; showError(loginError, reason.message); });
		});
	}

	var forgotPasswordLink = document.getElementById('forgot-password-link');
	var forgotPasswordView = document.getElementById('forgot-password-view');
	var forgotPasswordForm = document.getElementById('forgot-password-form');
	if (forgotPasswordLink && forgotPasswordView && forgotPasswordForm) {
		var forgotPasswordBack = document.getElementById('forgot-password-back');
		var forgotPasswordStatus = document.getElementById('forgot-password-status');
		var forgotPasswordSubmit = document.getElementById('forgot-password-submit');
		var loginHeading = document.getElementById('login-title');
		var loginDescription = document.getElementById('auth-heading-description');
		var loginSwitch = document.querySelector('#auth-form + .auth-switch');

		function showForgotPassword() {
			loginForm.hidden = true;
			loginError.hidden = true;
			status.textContent = '';
			loginSwitch.hidden = true;
			forgotPasswordView.hidden = false;
			loginHeading.textContent = 'Reset your password';
			loginDescription.textContent = 'Enter your email address and we will send reset instructions if an account matches.';
			document.getElementById('forgot-password-email').focus();
		}

		function showLogin() {
			forgotPasswordView.hidden = true;
			loginForm.hidden = false;
			loginSwitch.hidden = false;
			loginHeading.textContent = 'Welcome Back';
			loginDescription.textContent = 'Sign in to continue to your FINPATH account.';
			forgotPasswordStatus.textContent = '';
			window.history.replaceState(null, '', window.location.pathname + window.location.search);
		}

		forgotPasswordLink.addEventListener('click', function (event) {
			event.preventDefault();
			window.history.replaceState(null, '', window.location.pathname + window.location.search + '#forgot-password');
			showForgotPassword();
		});
		forgotPasswordBack.addEventListener('click', function (event) {
			event.preventDefault();
			showLogin();
		});
		forgotPasswordForm.addEventListener('submit', function (event) {
			event.preventDefault();
			if (!forgotPasswordForm.checkValidity()) {
				forgotPasswordForm.reportValidity();
				return;
			}
			forgotPasswordSubmit.disabled = true;
			forgotPasswordStatus.textContent = 'Submitting your request...';
			window.FinpathAPI.requestPasswordReset(document.getElementById('forgot-password-email').value.trim())
				.then(function () {
					forgotPasswordStatus.textContent = 'If an account exists for that email, a password reset link will be sent shortly. Check your inbox, or try again later.';
				})
				.catch(function (reason) {
					forgotPasswordStatus.textContent = reason && reason.status === 503
						? 'Password reset is temporarily unavailable. Please try again later.'
						: 'We could not submit your password reset request. Please try again later.';
				})
				.then(function () {
					forgotPasswordSubmit.disabled = false;
				});
		});

		if (window.location.hash === '#forgot-password') showForgotPassword();
	}

	var registerForm = document.getElementById('register-form');
	if (registerForm) {
		registerForm.addEventListener('submit', function (event) {
			event.preventDefault();
			var error = document.getElementById('register-error');
			var status = document.getElementById('register-status');
			var data;
			if (!registerForm.checkValidity()) { registerForm.reportValidity(); return; }
			if (document.getElementById('register-password').value !== document.getElementById('register-confirm-password').value) {
				showError(error, 'The passwords do not match.');
				return;
			}
			clearError(error);
			status.textContent = 'Creating your account...';
			data = new FormData(registerForm);
			window.FinpathAPI.register({ full_name: data.get('full_name'), email: data.get('email'), password: data.get('password') })
				.then(function () { window.location.href = '/login?registered=1'; })
				.catch(function (reason) { status.textContent = ''; showError(error, reason.message); });
		});
	}
}());
