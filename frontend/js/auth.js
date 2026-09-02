(function () {
	'use strict';

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
			window.FinpathAPI.login({ email: data.get('email'), password: data.get('password') }, data.get('remember') === 'on')
				.then(function () { window.location.href = 'dashboard.html'; })
				.catch(function (reason) { status.textContent = ''; showError(loginError, reason.message); });
		});
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
				.then(function () { window.location.href = 'login.html?registered=1'; })
				.catch(function (reason) { status.textContent = ''; showError(error, reason.message); });
		});
	}
}());
