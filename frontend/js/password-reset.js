(function () {
	'use strict';

	function show(element, message) { element.textContent = message; element.hidden = false; }
	function hide(element) { element.textContent = ''; element.hidden = true; }
	function validPassword(value) { return value.length >= 8 && value.length <= 128 && value === value.trim() && /[A-Za-z]/.test(value) && /\d/.test(value); }

	var forgotForm = document.getElementById('forgot-password-form');
	if (forgotForm) {
		var forgotSubmitting = false;
		forgotForm.addEventListener('submit', function (event) {
			event.preventDefault();
			var email = document.getElementById('forgot-email').value.trim();
			var error = document.getElementById('forgot-error');
			var emailError = document.getElementById('forgot-email-error');
			var success = document.getElementById('forgot-success');
			var button = forgotForm.querySelector('button[type="submit"]');
			if (forgotSubmitting) return;
			hide(error); hide(success); hide(emailError);
			if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { show(emailError, 'Enter a valid email address.'); return; }
			forgotSubmitting = true; button.disabled = true; document.getElementById('forgot-status').textContent = 'Sending your reset link...';
			window.FinpathAPI.requestPasswordReset(email).then(function (result) { show(success, result.message); forgotForm.reset(); }).catch(function (reason) { show(error, reason.message); }).finally(function () { forgotSubmitting = false; button.disabled = false; document.getElementById('forgot-status').textContent = ''; });
		});
	}

	var resetForm = document.getElementById('reset-password-form');
	if (resetForm) {
		var tokenMatch = window.location.hash.match(/^#token=([^&]+)$/);
		var token = tokenMatch ? decodeURIComponent(tokenMatch[1]) : '';
		var error = document.getElementById('reset-error');
		if (!token) { show(error, 'This reset link is missing or invalid. Request a new one.'); return; }
		window.FinpathAPI.validatePasswordResetToken(token).then(function () { resetForm.hidden = false; }).catch(function (reason) { show(error, reason.message); });
		resetForm.addEventListener('submit', function (event) {
			event.preventDefault();
			var password = document.getElementById('reset-password').value;
			var confirmation = document.getElementById('reset-confirm-password').value;
			var button = resetForm.querySelector('button[type="submit"]');
			if (resetForm.dataset.submitting === 'true') return;
			hide(error);
			if (!validPassword(password)) { show(error, 'Use 8 to 128 characters, including a letter and a number, without leading or trailing spaces.'); return; }
			if (password !== confirmation) { show(error, 'The passwords do not match.'); return; }
			resetForm.dataset.submitting = 'true'; button.disabled = true; document.getElementById('reset-status').textContent = 'Updating your password...';
			window.FinpathAPI.resetPassword(token, password).then(function (result) { resetForm.hidden = true; show(document.getElementById('reset-success'), result.message + ' You can now sign in.'); window.location.hash = ''; }).catch(function (reason) { show(error, reason.message); }).finally(function () { resetForm.dataset.submitting = 'false'; button.disabled = false; document.getElementById('reset-status').textContent = ''; });
		});
	}
}());