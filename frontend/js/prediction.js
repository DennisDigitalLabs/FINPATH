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
	var modelBadge = document.querySelector('.model-badge');
	var factorList = document.querySelector('.factor-list');
	var recommendationsLink = document.querySelector('.result-actions a[href^="/recommendations"]');
	if (!errorState) {
		errorState = document.createElement('div');
		errorState.className = 'prediction-panel';
		errorState.setAttribute('role', 'alert');
		errorState.hidden = true;
		processingState.parentNode.insertBefore(errorState, resultState);
	}

	function showError(message) {
		processingState.hidden = true;
		processingState.setAttribute('aria-busy', 'false');
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

	function formatFeatureName(feature) {
		var rawName = String(feature || 'Model feature');
		var isCategorical = rawName.indexOf('cat__') === 0;
		var name = rawName.replace(/^(?:cat|num)__/, '');
		var encodedCategory = isCategorical ? name.match(/^(.*)_(-?\d+(?:\.\d+)?)$/) : null;
		if (encodedCategory) {
			name = encodedCategory[1].replace(/_/g, ' ') + ' (encoded category ' + encodedCategory[2] + ')';
		} else {
			name = name.replace(/_/g, ' ');
		}
		return name.charAt(0).toUpperCase() + name.slice(1);
	}

	function renderFactors(factors) {
		var list = factorList;
		var entries = factorEntries(factors);
		list.innerHTML = '';
		if (!entries.length) {
			var empty = document.createElement('p');
			empty.textContent = 'The model did not return contributing factors for this prediction.';
			list.appendChild(empty);
			return;
		}
		entries.forEach(function (item) {
			var card = document.createElement('article');
			var content = document.createElement('div');
			var title = document.createElement('strong');
			var detail = document.createElement('p');
			card.className = 'factor-card';
			detail.className = 'factor-impact';
			title.textContent = formatFeatureName(item.feature || item.name || item.factor);
			if (typeof item.impact === 'number' && Number.isFinite(item.impact)) {
				detail.textContent = 'SHAP impact for the predicted class: ' + (item.impact > 0 ? '+' : '') + item.impact.toFixed(4);
			} else if (item.description) {
				detail.textContent = String(item.description);
			} else if (item.value !== undefined) {
				detail.textContent = 'Model value: ' + String(item.value);
			} else {
				detail.textContent = 'The model identified this feature as relevant to the prediction.';
			}
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
		var confidenceCard = document.querySelector('.confidence-card');
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
		if (confidence !== null) {
			confidenceCard.hidden = false;
			confidenceDescription.textContent = 'Confidence supplied by the FINPATH model.';
			confidenceTrack.setAttribute('aria-valuenow', String(confidence));
			confidenceTrack.querySelector('span').style.width = confidence + '%';
		}
		else {
			confidenceCard.hidden = true;
		}
		modelBadge.textContent = 'Model version ' + String(prediction.model_version);
		document.querySelector('.factors-section .section-heading > p').textContent = 'These factors were supplied by the FINPATH model.';
		renderFactors(prediction.contributing_factors);
		if (recommendationsLink) recommendationsLink.href = '/recommendations?prediction_id=' + encodeURIComponent(prediction.id);
		processingState.hidden = true;
		processingState.setAttribute('aria-busy', 'false');
		resultState.hidden = false;
		document.getElementById('result-heading').focus();
	}

	function loadPrediction() {
		processingState.hidden = false;
		processingState.setAttribute('aria-busy', 'true');
		var predictionId = params.get('prediction_id');
		var assessmentId = params.get('assessment_id');
		window.FinpathAPI.me().then(function () {
			processingStatus.textContent = 'Loading your model result...';
			if (predictionId) return window.FinpathAPI.getPrediction(predictionId);
			if (assessmentId) {
				return window.FinpathAPI.listPredictions(assessmentId).then(function (predictions) {
					if (!predictions || !predictions.length) { throw new Error('No prediction was found for that assessment.'); }
					return predictions[0];
				});
			}
			return window.FinpathAPI.getDashboard().then(function (dashboard) {
				if (!dashboard.latest_prediction) throw new Error('No prediction is available yet. Complete an assessment first.');
				return dashboard.latest_prediction;
			});
		}).then(renderPrediction).catch(function (reason) {
			if (reason && reason.status === 401) { window.location.href = '/login?next=/prediction'; return; }
			showError(reason && reason.message ? reason.message : 'We could not load your prediction. Please try again.');
		});
	}

	loadPrediction();
}());
