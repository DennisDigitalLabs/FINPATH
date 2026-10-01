(function () {
	'use strict';

	var status = document.getElementById('reset-link-status');
	var linkError = document.getElementById('reset-link-error');
	var form = document.getElementById('reset-password-form');
	var formError = document.getElementById('reset-password-error');
	var formStatus = document.getElementById('reset-password-status');
	var submit = document.getElementById('reset-password-submit');
	var success = document.getElementById('reset-password-success');
	var passwordField = document.getElementById('new-password');
	var confirmationField = document.getElementById('confirm-new-password');
	var resetToken = new URLSearchParams(window.location.hash.replace(/^#/, '')).get('token');

	function clearTokenFromAddressBar() {
		window.history.replaceState(null, '', window.location.pathname);
	}

	function clearResetToken() {
		resetToken = '';
		clearTokenFromAddressBar();
	}

	function showLinkError(message) {
		status.hidden = true;
		linkError.textContent = message;
		linkError.hidden = false;
		form.hidden = true;
	}

	function passwordProblem(password) {
		var length = Array.from(password).length;
		if (length < 8 || length > 128) return 'Use a password between 8 and 128 characters.';
		if (password !== password.trim()) return 'The password cannot start or end with whitespace.';
		if (!/\p{L}/u.test(password)) return 'Include at least one letter.';
		if (!/\p{N}/u.test(password)) return 'Include at least one number.';
		return '';
	}

	function validateLink() {
		if (!resetToken) {
			showLinkError('This reset link is missing or invalid. Request a new reset link to continue.');
			return;
		}
		window.FinpathAPI.validatePasswordResetToken(resetToken).then(function (result) {
			if (!result || result.valid !== true) {
				clearResetToken();
				showLinkError('This reset link is invalid or has expired. Request a new reset link to continue.');
				return;
			}
			status.hidden = true;
			form.hidden = false;
			passwordField.focus();
		}).catch(function (reason) {
			if (reason && reason.status === 400) clearResetToken();
			showLinkError(reason && reason.status === 400
				? 'This reset link is invalid or has expired. Request a new reset link to continue.'
				: 'We could not verify this reset link. Reopen the email link or request a new one.');
		});
	}

	form.addEventListener('submit', function (event) {
		event.preventDefault();
		formError.hidden = true;
		formError.textContent = '';
		if (!form.checkValidity()) {
			form.reportValidity();
			return;
		}

		var password = passwordField.value;
		var problem = passwordProblem(password);
		if (problem) {
			formError.textContent = problem;
			formError.hidden = false;
			passwordField.focus();
			return;
		}
		if (password !== confirmationField.value) {
			formError.textContent = 'The passwords do not match.';
			formError.hidden = false;
			confirmationField.focus();
			return;
		}
		if (!resetToken) {
			showLinkError('This reset link is invalid or has expired. Request a new reset link to continue.');
			return;
		}

		submit.disabled = true;
		formStatus.textContent = 'Updating your password...';
		window.FinpathAPI.resetPassword(resetToken, password).then(function () {
			clearResetToken();
			passwordField.value = '';
			confirmationField.value = '';
			form.hidden = true;
			formStatus.textContent = '';
			document.getElementById('reset-description').textContent = 'Your account is ready to use with your new password.';
			success.hidden = false;
		}).catch(function (reason) {
			if (reason && reason.status === 400) {
				clearResetToken();
				showLinkError('This reset link is invalid or has expired. Request a new reset link to continue.');
			} else if (reason && reason.status === 422) {
				formError.textContent = 'The password was not accepted. Check the password requirements and try again.';
				formError.hidden = false;
			} else {
				formError.textContent = 'We could not update your password. Please try again.';
				formError.hidden = false;
			}
		}).then(function () {
			submit.disabled = false;
		});
	});

	validateLink();
}());
