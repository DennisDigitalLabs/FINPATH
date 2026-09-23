(function () {
	'use strict';

	var content = document.querySelector('.analytics-content');
	var errorState = document.createElement('div');
	errorState.className = 'demo-notice';
	errorState.setAttribute('role', 'alert');
	errorState.hidden = true;
	content.insertBefore(errorState, content.firstChild);

	function showError(message) {
		errorState.textContent = message;
		errorState.hidden = false;
	}

	function setMetric(card, label, value) {
		card.querySelector('.metric-label').textContent = label;
		card.querySelector('strong').textContent = String(value);
		var status = card.querySelector('.metric-status');
		if (status) status.textContent = 'Live backend data';
	}

	function renderDistributionTable(data) {
		var panel = document.querySelector('.history-panel');
		var body = panel.querySelector('tbody');
		var caption = panel.querySelector('caption');
		var rows = Object.keys(data.assessment_status_distribution || {}).map(function (key) { return ['Assessment status', key, data.assessment_status_distribution[key]]; });
		rows = rows.concat(Object.keys(data.risk_level_distribution || {}).map(function (key) { return ['Risk level', key, data.risk_level_distribution[key]]; }));
		panel.querySelector('h2').textContent = 'Live distributions';
		panel.querySelector('.section-heading .summary-note').textContent = 'From your account';
		caption.textContent = 'Live analytics distributions';
		body.innerHTML = '';
		rows.forEach(function (row) {
			var tr = document.createElement('tr');
			var type = document.createElement('td');
			var label = document.createElement('td');
			var value = document.createElement('td');
			type.textContent = row[0];
			label.textContent = row[1];
			value.textContent = String(row[2]);
			tr.appendChild(type);
			tr.appendChild(label);
			tr.appendChild(value);
			tr.appendChild(document.createElement('td'));
			body.appendChild(tr);
		});
		if (!rows.length) {
			var empty = document.createElement('tr');
			var cell = document.createElement('td');
			cell.colSpan = 4;
			cell.textContent = 'No analytics data is available yet.';
			empty.appendChild(cell);
			body.appendChild(empty);
		}
	}

	function render(data) {
		var cards = document.querySelectorAll('.metric-card');
		setMetric(cards[0], 'Total assessments', data.total_assessments);
		setMetric(cards[1], 'Completed assessments', data.completed_assessments);
		setMetric(cards[2], 'Predictions generated', data.prediction_count);
		setMetric(cards[3], 'Recommendations generated', data.recommendation_count);
		cards[4].hidden = true;
		document.querySelector('.demo-pill').textContent = 'Live analytics';
		document.querySelector('.demo-notice:not([role="alert"])').hidden = true;
		document.querySelector('.summary-note').textContent = 'From your account';
		document.querySelector('.trend-panel').hidden = true;
		document.querySelector('.interpretation-panel').hidden = true;
		document.querySelector('.indicators-panel').hidden = true;
		renderDistributionTable(data);
	}

	function load() {
		if (!window.FinpathAPI.getToken()) { window.location.href = 'login.html?next=analytics.html'; return; }
		window.FinpathAPI.me().then(function () { return window.FinpathAPI.getAnalytics(); }).then(render).catch(function (reason) {
			if (reason && reason.status === 401) { window.location.href = 'login.html?next=analytics.html'; return; }
			showError(reason && reason.message ? reason.message : 'We could not load your analytics. Please try again.');
		});
	}

	load();
}());
