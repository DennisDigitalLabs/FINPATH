(function () {
	'use strict';

	var form = document.getElementById('profile-form');
	var status = document.getElementById('profile-status');
	var preferenceStatus = document.getElementById('preference-status');
	var nameValue = document.querySelector('[data-profile-name]');
	var emailValue = document.querySelector('[data-profile-email]');
	var displayName = document.getElementById('display-name');
	var emailField = document.getElementById('email');
	var profileNotice = document.querySelector('.demo-notice p');
	document.querySelectorAll('.preference-group').forEach(function (group) { group.remove(); });
	if (profileNotice) profileNotice.innerHTML = '<strong>Profile details</strong><br>These details are loaded from your authenticated account.';

	function showAccount(user) {
		var fullName = String(user.full_name || 'Account holder');
		var email = String(user.email || '');
		if (nameValue) nameValue.textContent = fullName;
		if (emailValue) emailValue.textContent = email;
		if (displayName) displayName.value = fullName;
		if (emailField) emailField.value = email;
	}

	if (!window.FinpathAPI || !window.FinpathAPI.getToken()) {
		window.location.href = '/login?next=/profile';
		return;
	}
	if (window.FinpathAPI && window.FinpathAPI.getToken()) {
		window.FinpathAPI.me().then(showAccount).catch(function () {
			if (status) status.textContent = 'We could not load your account details.';
		});
	}

	if (form) {
		form.addEventListener('submit', function (event) {
			event.preventDefault();
			status.textContent = 'Profile details are managed from your account.';
		});
	}
	if (preferenceStatus) preferenceStatus.textContent = 'Preferences are currently read-only.';
}());
