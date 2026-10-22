(function () {
	'use strict';

	var content = document.querySelector('.analytics-content');
	var dataSection = document.querySelector('.analytics-data');
	var errorState = document.getElementById('analytics-error');

	function showError(message) {
		errorState.textContent = message;
		errorState.hidden = false;
		dataSection.hidden = true;
		content.setAttribute('aria-busy', 'false');
	}

	function isCount(value) {
		return Number.isSafeInteger(value) && value >= 0;
	}

	function isDistribution(value) {
		return value && typeof value === 'object' && !Array.isArray(value) &&
			Object.keys(value).every(function (key) { return isCount(value[key]); });
	}

	function renderDistribution(targetId, values) {
		var list = document.getElementById(targetId);
		var keys = Object.keys(values);
		list.textContent = '';
		if (!keys.length) {
			var empty = document.createElement('li');
			empty.textContent = 'No records yet.';
			list.appendChild(empty);
			return;
		}
		keys.forEach(function (key) {
			var row = document.createElement('li');
			var label = document.createElement('span');
			var count = document.createElement('strong');
			label.textContent = key.replace(/_/g, ' ');
			count.textContent = String(values[key]);
			row.appendChild(label);
			row.appendChild(count);
			list.appendChild(row);
		});
	}

	function render(data) {
		var metrics = ['total_assessments', 'completed_assessments', 'prediction_count', 'recommendation_count'];
		if (!data || !metrics.every(function (field) { return isCount(data[field]); }) ||
			!isDistribution(data.assessment_status_distribution) ||
			!isDistribution(data.risk_level_distribution)) {
			throw new Error('The analytics response was incomplete or invalid.');
		}
		metrics.forEach(function (field) {
			document.querySelector('[data-metric="' + field + '"]').textContent = String(data[field]);
		});
		renderDistribution('assessment-status-distribution', data.assessment_status_distribution);
		renderDistribution('risk-level-distribution', data.risk_level_distribution);
		document.getElementById('analytics-updated').textContent = 'Current account totals';
		dataSection.hidden = false;
		content.setAttribute('aria-busy', 'false');
	}

	function load() {
		if (!window.FinpathAPI.getToken()) {
			window.location.href = '/login?next=/analytics';
			return;
		}
		window.FinpathAPI.me()
			.then(function () { return window.FinpathAPI.getAnalytics(); })
			.then(render)
			.catch(function (reason) {
				if (reason && reason.status === 401) {
					window.location.href = '/login?next=/analytics';
					return;
				}
				showError(reason && reason.message ? reason.message : 'We could not load your analytics. Please try again.');
			});
	}

	load();
}());
