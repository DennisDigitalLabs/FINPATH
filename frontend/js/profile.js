(function () {
	'use strict';

	var form = document.getElementById('profile-form');
	var status = document.getElementById('profile-status');
	var preferenceStatus = document.getElementById('preference-status');

	form.addEventListener('submit', function (event) {
		event.preventDefault();
		if (!form.checkValidity()) {
			form.reportValidity();
			status.textContent = 'Please check the highlighted fields.';
			return;
		}
		status.textContent = 'Profile updated in this demo page only.';
	});

	form.querySelectorAll('input, select').forEach(function (field) {
		field.addEventListener('input', function () { status.textContent = ''; });
	});
	document.querySelectorAll('.preference-group input').forEach(function (field) {
		field.addEventListener('change', function () { preferenceStatus.textContent = 'Preference updated in this demo page only.'; });
	});
}());
