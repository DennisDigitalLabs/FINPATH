(function () {
	'use strict';

	var content = document.querySelector('.admin-content');
	var adminCreateSection = document.getElementById('admin-create-section');
	var adminCreateForm = document.getElementById('admin-create-form');
	var adminCreateStatus = document.getElementById('admin-create-status');
	var adminCreateSubmit = document.getElementById('admin-create-submit');
	var errorState = document.createElement('div');
	errorState.className = 'admin-notice live-admin-state';
	errorState.setAttribute('role', 'status');
	errorState.textContent = 'Loading live administration data...';
	content.insertBefore(errorState, content.firstChild);
	content.querySelector('.admin-notice:not(.live-admin-state)').hidden = true;
	content.querySelectorAll('.admin-section').forEach(function (section) { section.hidden = true; });

	function showError(message) {
		errorState.setAttribute('role', 'alert');
		errorState.textContent = message;
		errorState.hidden = false;
		content.querySelector('.admin-intro').hidden = true;
		content.querySelector('.admin-notice:not(.live-admin-state)').hidden = true;
		content.querySelectorAll('.admin-section:not(#admin-create-section), .admin-notice:not([role="alert"])').forEach(function (section) { section.hidden = true; });
		document.querySelectorAll('.stat-card').forEach(function (card) { card.hidden = true; });
	}

	function adminCreateError(reason) {
		if (reason && reason.status === 401) return 'Your session has expired. Please log in again.';
		if (reason && reason.status === 403) return 'Administrator access is required.';
		if (reason && reason.status === 409) return 'An active administrator with this email already exists or the maximum number of active administrators has been reached.';
		if (reason && reason.status === 422) return 'Please check the account details and try again.';
		return reason && reason.message ? reason.message : 'We could not create the administrator account. Please try again.';
	}

	adminCreateForm.addEventListener('submit', function (event) {
		event.preventDefault();
		if (!adminCreateForm.checkValidity()) {
			adminCreateForm.reportValidity();
			return;
		}

		var fullName = document.getElementById('admin-create-name').value.trim();
		var email = document.getElementById('admin-create-email').value.trim();
		var password = document.getElementById('admin-create-password').value;
		var confirmation = document.getElementById('admin-create-confirm-password').value;
		if (!fullName) {
			adminCreateStatus.textContent = 'Enter the administrator\'s full name.';
			return;
		}
		if (password.length < 8 || password.length > 128 || password !== password.trim() || !/[A-Za-z]/.test(password) || !/[0-9]/.test(password)) {
			adminCreateStatus.textContent = 'Use a password of 8 to 128 characters, with a letter and a number and no surrounding spaces.';
			return;
		}
		if (password !== confirmation) {
			adminCreateStatus.textContent = 'The passwords do not match.';
			return;
		}

		adminCreateStatus.textContent = 'Creating administrator account...';
		adminCreateSubmit.disabled = true;
		window.FinpathAPI.postAuthenticated('/api/v1/auth/admins', {
			full_name: fullName,
			email: email,
			password: password
		}).then(function () {
			adminCreateForm.reset();
			adminCreateStatus.textContent = 'Administrator account created successfully.';
		}).catch(function (reason) {
			adminCreateStatus.textContent = adminCreateError(reason);
		}).then(function () {
			adminCreateSubmit.disabled = false;
		});
	});

	function renderDistribution(targetId, values) {
		var list = document.getElementById(targetId);
		list.textContent = '';
		Object.keys(values || {}).forEach(function (key) {
			var row = document.createElement('div');
			var label = document.createElement('span');
			var count = document.createElement('b');
			label.textContent = key;
			count.textContent = String(values[key]);
			row.appendChild(label);
			row.appendChild(count);
			list.appendChild(row);
		});
		if (!Object.keys(values || {}).length) {
			var empty = document.createElement('p');
			empty.textContent = 'No data is available yet.';
			list.appendChild(empty);
		}
	}

	function isCount(value) {
		return Number.isInteger(value) && value >= 0;
	}

	function isCountDistribution(value) {
		return value && typeof value === 'object' && !Array.isArray(value) &&
			Object.keys(value).every(function (key) { return isCount(value[key]); });
	}

	function render(data) {
		var countFields = [
			'user_count', 'active_user_count', 'total_assessments',
			'completed_assessments', 'prediction_count', 'recommendation_count'
		];
		if (!data || !countFields.every(function (field) { return isCount(data[field]); }) ||
			!isCountDistribution(data.assessment_status_distribution) ||
			!isCountDistribution(data.risk_level_distribution) ||
			typeof data.generated_at !== 'string' || !data.generated_at || isNaN(Date.parse(data.generated_at))) {
			throw new Error('The admin analytics response was incomplete or invalid.');
		}
		errorState.hidden = true;
		document.querySelectorAll('[data-stat]').forEach(function (element) {
			element.textContent = String(data[element.getAttribute('data-stat')]);
		});
		document.querySelector('.admin-pill').textContent = 'Live admin data';
		document.querySelector('.admin-notice:not(.live-admin-state)').hidden = true;
		document.querySelector('.admin-intro p:not(.eyebrow)').textContent = 'Review live system totals and distributions from the protected administration service.';
		document.getElementById('generated-at').textContent = 'Generated ' + new Date(data.generated_at).toLocaleString();
		document.querySelector('.sidebar-note strong').textContent = 'Live administration';
		document.querySelector('.sidebar-note small').textContent = 'System data from the protected analytics service.';
		document.getElementById('overview-section').hidden = false;
		document.getElementById('admin-create-section').hidden = false;
		content.querySelectorAll('.admin-empty-state').forEach(function (section) { section.hidden = false; });
		renderDistribution('assessment-distribution', data.assessment_status_distribution);
		renderDistribution('risk-distribution', data.risk_level_distribution);
	}

	function load() {
		if (!window.FinpathAPI.getToken()) { window.location.href = '/login?next=/admin'; return; }
		window.FinpathAPI.me().then(function (user) {
			if (user.role !== 'admin') {
				var forbidden = new Error('Administrator access is required to view this page.');
				forbidden.status = 403;
				throw forbidden;
			}
			adminCreateSection.hidden = false;
			return window.FinpathAPI.getSystemAnalytics();
		}).then(render).catch(function (reason) {
			if (reason && reason.status === 401) { window.location.href = '/login?next=/admin'; return; }
			showError(reason && reason.status === 403 ? 'Administrator access is required to view this page.' : (reason && reason.message ? reason.message : 'We could not load the admin dashboard. Please try again.'));
		});
	}

	load();
}());
