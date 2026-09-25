(function () {
	'use strict';

	var processingState = document.getElementById('processing-state');
	var resultState = document.getElementById('result-state');
	var errorState = document.getElementById('prediction-error');
	var processingStatus = document.getElementById('processing-status');
	var params = new URLSearchParams(window.location.search);
	var resultLede = document.querySelector('.result-header .panel-lede');
	var riskBadge = document.querySelector('.risk-badge');
	var probabilityValue = document.querySelector('.score-ring span');
	var scoreMeter = document.querySelector('.meter-track');
	var confidenceValue = document.querySelector('.confidence-value');
	var confidenceDescription = document.querySelector('.confidence-card p');
	var confidenceTrack = document.querySelector('.confidence-track');
	var modelBadge = document.querySelector('.demo-badge');
	var factorList = document.querySelector('.factor-list');
	var recommendationsLink = document.querySelector('.result-actions a[href^="recommendations"]');
	resultState.querySelector('.result-header .panel-lede').textContent = '';
	factorList.innerHTML = '';
	if (!errorState) {
		errorState = document.createElement('div');
		errorState.className = 'prediction-panel';
		errorState.setAttribute('role', 'alert');
		errorState.hidden = true;
		processingState.parentNode.insertBefore(errorState, resultState);
	}

	function showError(message) {
		processingState.hidden = true;
		resultState.hidden = true;
		errorState.textContent = message;
		errorState.hidden = false;
	}

	function percentage(value) { return Math.round(Number(value) * 100); }

	function factorEntries(factors) {
		if (Array.isArray(factors)) return factors;
		if (factors && Array.isArray(factors.top_factors)) return factors.top_factors;
		if (factors && typeof factors === 'object') return Object.keys(factors).map(function (key) { return { feature: key, value: factors[key] }; });
		return [];
	}

	function renderFactors(factors) {
		var list = factorList;
		var entries = factorEntries(factors);
		list.innerHTML = '';
		if (!entries.length) {
			var empty = document.createElement('p');
			empty.textContent = 'The model did not provide contributing factors for this prediction.';
			list.appendChild(empty);
			return;
		}
		entries.forEach(function (item) {
			var card = document.createElement('article');
			var content = document.createElement('div');
			var title = document.createElement('strong');
			var detail = document.createElement('p');
			card.className = 'factor-card';
			title.textContent = String(item.feature || item.name || item.factor || 'Contributing factor');
			detail.textContent = item.description ? String(item.description) : (item.value === undefined ? 'Supplied by the FINPATH explainability output.' : 'Model contribution: ' + String(item.value));
			content.appendChild(title);
			content.appendChild(detail);
			card.appendChild(content);
			list.appendChild(card);
		});
	}

	function renderPrediction(prediction) {
		var probability = percentage(prediction.probability);
		var confidence = prediction.confidence === null || prediction.confidence === undefined ? null : percentage(prediction.confidence);
		var riskLevel = String(prediction.risk_level || '');
		resultLede.textContent = String(prediction.explanation);
		document.getElementById('result-heading').textContent = 'Your FINPATH prediction.';
		riskBadge.textContent = riskLevel.charAt(0).toUpperCase() + riskLevel.slice(1) + ' risk';
		probabilityValue.textContent = String(probability);
		scoreMeter.setAttribute('aria-label', 'Model probability ' + probability + ' percent');
		scoreMeter.querySelector('span').style.width = probability + '%';
		document.querySelector('.score-label').childNodes[0].textContent = 'Model probability ';
		document.querySelector('.tooltip-mark').setAttribute('title', 'Probability returned by the FINPATH model.');
		document.querySelector('.tooltip-mark').setAttribute('aria-label', 'Probability returned by the FINPATH model.');
		document.querySelector('.score-visual p').textContent = 'Probability returned by the FINPATH model.';
		confidenceValue.textContent = confidence === null ? 'Not available' : String(confidence) + '%';
		confidenceDescription.textContent = confidence === null ? 'Confidence was not supplied by the model.' : 'Confidence supplied by the FINPATH model.';
		if (confidence !== null) {
			confidenceTrack.setAttribute('aria-valuenow', String(confidence));
			confidenceTrack.querySelector('span').style.width = confidence + '%';
		}
		else {
			confidenceTrack.setAttribute('aria-valuenow', '0');
			confidenceTrack.setAttribute('aria-label', 'Model confidence not available');
			confidenceTrack.querySelector('span').style.width = '0%';
		}
		modelBadge.textContent = 'Model version ' + String(prediction.model_version);
		document.querySelector('.factors-section .section-heading > p').textContent = 'These factors were supplied by the FINPATH model.';
		renderFactors(prediction.contributing_factors);
		if (recommendationsLink) recommendationsLink.href = '/recommendations?prediction_id=' + encodeURIComponent(prediction.id);
		processingState.hidden = true;
		resultState.hidden = false;
		document.getElementById('result-heading').focus();
	}

	function loadPrediction() {
		var predictionId = params.get('prediction_id');
		var assessmentId = params.get('assessment_id');
		if (!predictionId && !assessmentId) { showError('No prediction was selected. Complete an assessment first.'); return; }
		window.FinpathAPI.me().then(function () {
			processingStatus.textContent = 'Loading your model result...';
			if (predictionId) return window.FinpathAPI.getPrediction(predictionId);
			return window.FinpathAPI.listPredictions(assessmentId).then(function (predictions) {
				if (!predictions || !predictions.length) { throw new Error('No prediction was found for that assessment.'); }
				return predictions[0];
			});
		}).then(renderPrediction).catch(function (reason) {
			if (reason && reason.status === 401) { window.location.href = '/login?next=/prediction'; return; }
			showError(reason && reason.message ? reason.message : 'We could not load your prediction. Please try again.');
		});
	}

	loadPrediction();
}());
