(function () {
	'use strict';

	var content = document.querySelector('.profile-content');
	var errorState = document.getElementById('profile-error');
	var nameValue = document.querySelector('[data-profile-name]');
	var emailValue = document.querySelector('[data-profile-email]');

	function showError(message) {
		errorState.textContent = message;
		errorState.hidden = false;
		document.querySelector('.profile-grid').hidden = true;
		document.querySelector('.security-panel').hidden = true;
		content.setAttribute('aria-busy', 'false');
	}

	function renderDashboard(data) {
		if (!data || !Number.isSafeInteger(data.assessment_count) || data.assessment_count < 0) {
			throw new Error('The account activity response was incomplete or invalid.');
		}
		var assessment = data.latest_assessment;
		var prediction = data.latest_prediction;
		document.getElementById('profile-assessment-count').textContent = String(data.assessment_count);
		document.getElementById('profile-assessment-status').textContent = assessment
			? String(assessment.assessment_status)
			: 'No assessments yet';
		document.getElementById('profile-risk-result').textContent = prediction
			? String(prediction.risk_category) + ' (' + String(prediction.risk_level) + ')'
			: 'No prediction yet';

		var predictionLink = document.getElementById('profile-prediction-link');
		var recommendationsLink = document.getElementById('profile-recommendations-link');
		if (prediction) {
			var predictionId = encodeURIComponent(prediction.id);
			predictionLink.href = '/prediction?prediction_id=' + predictionId;
			recommendationsLink.href = '/recommendations?prediction_id=' + predictionId;
		} else {
			predictionLink.href = '/assessment';
			predictionLink.textContent = 'Start an assessment';
			recommendationsLink.hidden = true;
		}
	}

	function load() {
		if (!window.FinpathAPI || !window.FinpathAPI.getToken()) {
			window.location.href = '/login?next=/profile';
			return;
		}
		window.FinpathAPI.me().then(function (user) {
			nameValue.textContent = String(user.full_name || '');
			emailValue.textContent = String(user.email || '');
			return window.FinpathAPI.getDashboard();
		}).then(renderDashboard).catch(function (reason) {
			if (reason && reason.status === 401) {
				window.location.href = '/login?next=/profile';
				return;
			}
			showError(reason && reason.message ? reason.message : 'We could not load your account information. Please try again.');
		}).then(function () {
			content.setAttribute('aria-busy', 'false');
		});
	}

	load();
}());
