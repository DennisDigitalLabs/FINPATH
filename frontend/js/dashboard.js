(function () {
	'use strict';

	var content = document.querySelector('.dashboard-content');
	var errorState = document.createElement('div');
	errorState.className = 'dashboard-notice';
	errorState.setAttribute('role', 'alert');
	errorState.hidden = true;
	content.insertBefore(errorState, content.firstChild);

	function dateText(value) {
		if (!value) return 'Not available';
		var date = new Date(value);
		return isNaN(date.getTime()) ? 'Not available' : date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
	}

	function setText(selector, value) {
		var element = document.querySelector(selector);
		if (element) element.textContent = value;
	}

	function showError(message) {
		errorState.textContent = message;
		errorState.hidden = false;
		content.querySelector('.welcome-band').hidden = true;
		content.querySelectorAll('.dashboard-notice:not([role="alert"]), .overview-grid, .quick-actions, .lower-grid').forEach(function (section) { section.hidden = true; });
	}

	function renderRecommendations(items) {
		var preview = document.querySelector('.recommendation-preview');
		preview.innerHTML = '';
		(items || []).slice(0, 3).forEach(function (item, index) {
			var row = document.createElement('div');
			var body = document.createElement('div');
			row.className = 'recommendation-item';
			var number = document.createElement('span');
			number.textContent = String(index + 1).padStart(2, '0');
			row.appendChild(number);
			var title = document.createElement('strong');
			title.textContent = item.recommendation_text;
			body.appendChild(title);
			var detail = document.createElement('p');
			detail.textContent = 'Priority ' + String(item.priority);
			body.appendChild(detail);
			row.appendChild(body);
			preview.appendChild(row);
		});
		if (!(items || []).length) {
			var empty = document.createElement('p');
			empty.textContent = 'No recommendations are available yet.';
			preview.appendChild(empty);
		}
	}

	function renderActivity(items) {
		var list = document.querySelector('.activity-list');
		list.innerHTML = '';
		(items || []).forEach(function (item) {
			var row = document.createElement('li');
			var marker = document.createElement('span');
			var body = document.createElement('div');
			marker.className = 'activity-dot ' + (item.has_prediction ? 'profile' : 'complete');
			marker.setAttribute('aria-hidden', 'true');
			marker.textContent = item.has_prediction ? '◈' : '✓';
			row.appendChild(marker);
			var title = document.createElement('strong');
			title.textContent = 'Assessment ' + String(item.assessment_id) + ' ' + String(item.assessment_status);
			body.appendChild(title);
			var detail = document.createElement('small');
			detail.textContent = item.has_prediction ? 'Prediction generated' : 'No prediction generated';
			body.appendChild(detail);
			row.appendChild(body);
			var time = document.createElement('time');
			time.dateTime = item.assessment_date || '';
			time.textContent = dateText(item.assessment_date);
			row.appendChild(time);
			list.appendChild(row);
		});
		if (!(items || []).length) {
			var empty = document.createElement('li');
			empty.textContent = 'No recent assessment activity.';
			list.appendChild(empty);
		}
	}

	function render(data) {
		var assessment = data.latest_assessment;
		var prediction = data.latest_prediction;
		var probability = prediction ? Math.round(Number(prediction.probability) * 100) : null;
		var confidence = prediction && prediction.confidence !== null && prediction.confidence !== undefined ? Math.round(Number(prediction.confidence) * 100) : null;
		setText('#dashboard-title', 'Welcome back, ' + String(data.user.full_name));
		setText('.welcome-band .eyebrow', 'Your workspace');
		setText('.demo-pill', 'Live dashboard');
		setText('.updated-label', assessment ? 'Updated ' + dateText(assessment.updated_at) : 'No assessments yet');
		document.querySelectorAll('.dashboard-notice').forEach(function (notice) { if (notice !== errorState) notice.hidden = true; });
		setText('.risk-card .status-tag', prediction ? String(prediction.risk_level) : 'Unavailable');
		setText('.risk-number', probability === null ? '—' : String(probability));
		setText('.risk-main strong', prediction ? String(prediction.risk_category) : 'No prediction available');
		setText('.risk-main p', prediction ? String(prediction.explanation) : 'Complete an assessment to generate a prediction.');
		document.querySelector('.risk-meter').setAttribute('aria-label', probability === null ? 'No model probability available' : 'Model probability ' + probability + ' percent');
		document.querySelector('.risk-meter span').style.width = (probability === null ? 0 : probability) + '%';
		setText('.confidence-card .status-tag', confidence === null ? 'Unavailable' : 'Model output');
		setText('.confidence-number', confidence === null ? '—' : confidence + '%');
		setText('.confidence-card p', confidence === null ? 'Confidence was not supplied by the model.' : 'Confidence supplied by the model.');
		document.querySelector('.confidence-meter').setAttribute('aria-label', confidence === null ? 'Model confidence not available' : 'Model confidence ' + confidence + ' percent');
		document.querySelector('.confidence-meter').setAttribute('aria-valuenow', String(confidence === null ? 0 : confidence));
		document.querySelector('.confidence-meter span').style.width = (confidence === null ? 0 : confidence) + '%';
		setText('.status-progress strong', data.assessment_count + ' assessments');
		setText('.status-progress > span', assessment ? String(assessment.assessment_status) : 'None');
		setText('.assessment-status-card p', assessment ? 'Last reviewed ' + dateText(assessment.updated_at) : 'No assessment has been completed.');
		document.querySelector('.status-meter').setAttribute('aria-valuenow', assessment ? '100' : '0');
		document.querySelector('.status-meter').setAttribute('aria-label', assessment ? 'Assessment status ' + assessment.assessment_status : 'No assessment data available');
		document.querySelector('.status-meter span').style.width = assessment ? '100%' : '0%';
		if (prediction) document.querySelector('.action-card[href="/prediction"]').href = '/prediction?prediction_id=' + encodeURIComponent(prediction.id);
		renderRecommendations(data.latest_recommendations);
		renderActivity(data.recent_activity);
		document.querySelector('.indicators-section').hidden = true;
		var recommendationFootnote = document.querySelector('.recommendations-section .section-footnote');
		if (recommendationFootnote) recommendationFootnote.hidden = true;
		var previewLabel = document.querySelector('.recommendations-section .preview-label');
		if (previewLabel) previewLabel.hidden = true;
		document.querySelector('.activity-section .updated-label').textContent = 'Live activity';
	}

	function load() {
		if (!window.FinpathAPI.getToken()) { window.location.href = '/login?next=/dashboard'; return; }
		window.FinpathAPI.me().then(function () { return window.FinpathAPI.getDashboard(); }).then(render).catch(function (reason) {
			if (reason && reason.status === 401) { window.location.href = '/login?next=/dashboard'; return; }
			showError(reason && reason.message ? reason.message : 'We could not load your dashboard. Please try again.');
		});
	}

	document.getElementById('logout-button').addEventListener('click', function () { window.FinpathAPI.clearToken(); window.location.href = '/login'; });
	load();
}());
