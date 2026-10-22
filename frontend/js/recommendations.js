(function () {
	'use strict';

	var list = document.getElementById('recommendation-list');
	var filter = document.getElementById('category-filter');
	var emptyState = document.getElementById('empty-state');
	var recommendations = [];
	var state = {};
	var errorState = document.getElementById('recommendation-error');
	var params = new URLSearchParams(window.location.search);
	var rawPredictionId = params.get('prediction_id');
	var predictionId = rawPredictionId && /^\d+$/.test(rawPredictionId) ? Number(rawPredictionId) : NaN;

	function showError(message, backHref) {
		document.querySelector('.demo-pill').textContent = 'Recommendations unavailable';
		list.hidden = true;
		emptyState.hidden = true;
		document.querySelector('.summary-section').hidden = true;
		document.querySelector('.insight-panel').hidden = true;
		errorState.innerHTML = '';
		errorState.textContent = message;
		var backLink = document.createElement('a');
		backLink.className = 'btn btn-outline';
		backLink.href = backHref || '/dashboard';
		backLink.textContent = backHref ? 'Return to prediction' : 'Return to dashboard';
		errorState.appendChild(backLink);
		errorState.hidden = false;
	}

	function loginHref() {
		var returnPath = rawPredictionId
			? '/recommendations?prediction_id=' + encodeURIComponent(rawPredictionId)
			: '/recommendations';
		return '/login?next=' + encodeURIComponent(returnPath);
	}

	function formatCategory(category) {
		return String(category || 'Recommendation').replace(/_/g, ' ').replace(/\b\w/g, function (character) { return character.toUpperCase(); });
	}

	function formatDate(value) {
		if (!value) return '';
		var date = new Date(value);
		return isNaN(date.getTime()) ? '' : date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
	}

	function updateSummary() {
		var highPriority = recommendations.filter(function (item) { return item.priority === 1; }).length;
		document.getElementById('total-count').textContent = recommendations.length;
		document.getElementById('priority-count').textContent = highPriority;
	}

	function appendText(parent, tagName, className, text) {
		var element = document.createElement(tagName);
		if (className) element.className = className;
		element.textContent = text;
		parent.appendChild(element);
		return element;
	}

	function buildCard(item) {
		var itemState = state[item.id];
		var card = document.createElement('article');
		var header = document.createElement('div');
		var actions = document.createElement('div');
		var detail = document.createElement('div');
		var detailsButton = document.createElement('button');
		card.className = 'recommendation-card';
		card.dataset.id = String(item.id);
		header.className = 'card-header';
		appendText(header, 'span', 'category-label', formatCategory(item.category));
		appendText(header, 'span', 'priority-label priority-' + (item.priority <= 2 ? 'high' : item.priority === 3 ? 'medium' : 'low'), 'Priority ' + String(item.priority));
		card.appendChild(header);
		appendText(card, 'h3', '', item.recommendation_text);
		appendText(card, 'p', 'card-explanation', 'Generated from your prediction.');
		detail.className = 'recommendation-detail';
		detail.hidden = !itemState.details;
		appendText(detail, 'div', '', 'Prediction reference: ' + String(item.prediction_id));
		if (formatDate(item.created_at)) appendText(detail, 'div', '', 'Generated ' + formatDate(item.created_at));
		card.appendChild(detail);
		actions.className = 'card-actions';
		detailsButton.className = 'details-button';
		detailsButton.type = 'button';
		detailsButton.setAttribute('aria-expanded', String(itemState.details));
		detailsButton.textContent = itemState.details ? 'Hide details ↑' : 'View details ↓';
		actions.appendChild(detailsButton);
		card.appendChild(actions);
		return card;
	}

	function render() {
		var selected = filter.value;
		var visible = recommendations.filter(function (item) { return selected === 'all' || item.category === selected; });
		list.innerHTML = '';
		visible.forEach(function (item) { list.appendChild(buildCard(item)); });
		list.hidden = false;
		emptyState.textContent = recommendations.length ? 'No recommendations match this category yet.' : 'No recommendations are available for this prediction yet.';
		emptyState.hidden = visible.length > 0;
		updateSummary();
	}

	function setFilterOptions() {
		var categories = recommendations.reduce(function (result, item) {
			if (result.indexOf(item.category) === -1) result.push(item.category);
			return result;
		}, []);
		filter.innerHTML = '';
		var all = document.createElement('option');
		all.value = 'all';
		all.textContent = 'All recommendations';
		filter.appendChild(all);
		categories.forEach(function (category) {
			var option = document.createElement('option');
			option.value = category;
			option.textContent = formatCategory(category);
			filter.appendChild(option);
		});
	}

	list.addEventListener('click', function (event) {
		var card = event.target.closest('.recommendation-card');
		if (!card) return;
		var itemState = state[card.dataset.id];
		if (event.target.closest('.details-button')) itemState.details = !itemState.details;
		render();
	});
	filter.addEventListener('change', render);

	if (rawPredictionId && (!Number.isSafeInteger(predictionId) || predictionId <= 0)) {
		showError('A valid prediction was not selected. Return to your dashboard and open a prediction first.');
		return;
	}

	if (!window.FinpathAPI.getToken()) {
		window.location.href = loginHref();
		return;
	}
	window.FinpathAPI.me().then(function () {
		if (!rawPredictionId) {
			return window.FinpathAPI.getDashboard().then(function (dashboard) {
				if (!dashboard.latest_prediction) {
					throw new Error('No recommendations are available until you complete an assessment.');
				}
				predictionId = dashboard.latest_prediction.id;
				var returnPath = '/recommendations?prediction_id=' + encodeURIComponent(predictionId);
				window.history.replaceState(null, '', returnPath);
				return predictionId;
			});
		}
		return predictionId;
	}).then(function () {
		return window.FinpathAPI.listRecommendationsForPrediction(predictionId);
	}).then(function (result) {
		if (!Array.isArray(result)) throw new Error('The recommendations response was invalid. Please try again.');
		recommendations = Array.isArray(result) ? result : [];
		state = recommendations.reduce(function (result, item) { result[item.id] = { details: false }; return result; }, {});
		setFilterOptions();
		document.querySelector('.demo-pill').textContent = 'Live recommendations';
		document.querySelector('.demo-notice').hidden = true;
		document.getElementById('demo-insight').hidden = true;
		document.querySelector('.summary-note').textContent = 'For this prediction';
		document.getElementById('list-heading').textContent = 'Your recommendations';
		render();
	}).catch(function (reason) {
		if (reason && reason.status === 401) { window.location.href = loginHref(); return; }
		showError(
			reason && reason.message ? reason.message : 'We could not load your recommendations. Please try again.',
			'prediction.html?prediction_id=' + encodeURIComponent(predictionId)
		);
	});
}());
