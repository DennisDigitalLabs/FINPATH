(function () {
	'use strict';

	var content = document.querySelector('.admin-content');
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
		content.querySelectorAll('.admin-section, .admin-notice:not([role="alert"])').forEach(function (section) { section.hidden = true; });
		document.querySelectorAll('.stat-card').forEach(function (card) { card.hidden = true; });
	}

	function setStat(index, label, value, detail) {
		var card = document.querySelectorAll('.stat-card')[index];
		card.querySelector('span').textContent = label;
		card.querySelector('strong').textContent = String(value);
		card.querySelector('small').textContent = detail;
	}

	function renderDistribution(title, values) {
		var section = document.createElement('section');
		section.className = 'admin-section live-distribution';
		var heading = document.createElement('div');
		heading.className = 'section-heading';
		var headingText = document.createElement('div');
		var eyebrow = document.createElement('p');
		var h2 = document.createElement('h2');
		eyebrow.className = 'eyebrow';
		eyebrow.textContent = 'Live system data';
		h2.textContent = title;
		headingText.appendChild(eyebrow);
		headingText.appendChild(h2);
		heading.appendChild(headingText);
		section.appendChild(heading);
		Object.keys(values || {}).forEach(function (key) {
			var row = document.createElement('div');
			row.className = 'category-list';
			var label = document.createElement('span');
			var count = document.createElement('b');
			label.textContent = key;
			count.textContent = String(values[key]);
			row.appendChild(label);
			row.appendChild(count);
			section.appendChild(row);
		});
		if (!Object.keys(values || {}).length) {
			var empty = document.createElement('p');
			empty.textContent = 'No data is available yet.';
			section.appendChild(empty);
		}
		content.appendChild(section);
	}

	function render(data) {
		errorState.hidden = true;
		setStat(0, 'Total users', data.user_count, 'Live registered accounts');
		setStat(1, 'Active users', data.active_user_count, 'Currently active accounts');
		setStat(2, 'Total assessments', data.total_assessments, 'Live assessment records');
		setStat(3, 'Completed assessments', data.completed_assessments, 'Live completed records');
		setStat(4, 'Predictions generated', data.prediction_count, 'Live prediction records');
		var extra = document.createElement('article');
		extra.className = 'stat-card';
		extra.innerHTML = '<span>Recommendations generated</span><strong></strong><small>Live recommendation records</small>';
		extra.querySelector('strong').textContent = String(data.recommendation_count);
		document.querySelector('.stat-grid').appendChild(extra);
		document.querySelector('.admin-pill').textContent = 'Live admin data';
		document.querySelector('.admin-notice:not(.live-admin-state)').hidden = true;
		document.querySelector('.admin-intro p:not(.eyebrow)').textContent = 'Review live system totals and distributions from the protected administration service.';
		document.querySelector('.summary-note').textContent = 'Generated ' + new Date(data.generated_at).toLocaleString();
		document.querySelector('.sidebar-note strong').textContent = 'Live administration';
		document.querySelector('.sidebar-note small').textContent = 'System data from the protected analytics service.';
		document.querySelector('.admin-content > .admin-section').hidden = false;
		content.querySelectorAll('.admin-empty-state').forEach(function (section) { section.hidden = false; });
		renderDistribution('Assessment status distribution', data.assessment_status_distribution);
		renderDistribution('Risk-level distribution', data.risk_level_distribution);
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
