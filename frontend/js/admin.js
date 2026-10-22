(function () {
	'use strict';

	var content = document.querySelector('.admin-content');
	var layout = document.querySelector('.admin-layout');
	var errorState = document.createElement('div');
	errorState.className = 'admin-notice live-admin-state';
	errorState.setAttribute('role', 'status');
	errorState.textContent = 'Loading live administration data...';
	content.insertBefore(errorState, content.firstChild);
	content.querySelector('.admin-notice:not(.live-admin-state)').hidden = true;
	content.querySelectorAll('.admin-section').forEach(function (section) { section.hidden = true; });

	function showError(message) {
		var dashboardLink = document.createElement('a');
		errorState.setAttribute('role', 'alert');
		errorState.textContent = message;
		errorState.hidden = false;
		dashboardLink.className = 'btn btn-outline';
		dashboardLink.href = '/dashboard';
		dashboardLink.textContent = 'Return to dashboard';
		layout.className = 'container admin-denied';
		layout.replaceChildren(errorState, dashboardLink);
		document.querySelector('.admin-header').remove();
	}

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
			return window.FinpathAPI.getSystemAnalytics();
		}).then(render).catch(function (reason) {
			if (reason && reason.status === 401) { window.location.href = '/login?next=/admin'; return; }
			showError(reason && reason.status === 403 ? 'Administrator access is required to view this page.' : (reason && reason.message ? reason.message : 'We could not load the admin dashboard. Please try again.'));
		});
	}

	load();
}());
