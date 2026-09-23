(function () {
	'use strict';

	var list = document.getElementById('recommendation-list');
	var filter = document.getElementById('category-filter');
	var emptyState = document.getElementById('empty-state');
	var recommendations = [];
	var state = {};
	var errorState = document.getElementById('recommendation-error');

	function showError(message) {
		list.hidden = true;
		emptyState.hidden = true;
		errorState.textContent = message;
		errorState.hidden = false;
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
		var completed = recommendations.filter(function (item) { return state[item.id].completed; }).length;
		var highPriority = recommendations.filter(function (item) { return item.priority === 1; }).length;
		var percent = recommendations.length ? Math.round((completed / recommendations.length) * 100) : 0;
		document.getElementById('total-count').textContent = recommendations.length;
		document.getElementById('priority-count').textContent = highPriority;
		document.getElementById('completed-count').textContent = completed;
		document.getElementById('progress-value').textContent = percent + '%';
		document.getElementById('summary-bar').style.width = percent + '%';
		document.querySelector('.summary-track').setAttribute('aria-valuenow', String(percent));
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
		var completeButton = document.createElement('button');
		var saveButton = document.createElement('button');
		var detailsButton = document.createElement('button');
		card.className = 'recommendation-card' + (itemState.completed ? ' is-complete' : '');
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
		completeButton.className = 'btn btn-primary btn-sm complete-button';
		completeButton.type = 'button';
		completeButton.setAttribute('aria-pressed', String(itemState.completed));
		completeButton.textContent = itemState.completed ? 'Completed' : 'Mark complete';
		saveButton.className = 'icon-button save-button' + (itemState.saved ? ' is-saved' : '');
		saveButton.type = 'button';
		saveButton.setAttribute('aria-pressed', String(itemState.saved));
		saveButton.setAttribute('aria-label', itemState.saved ? 'Remove saved recommendation' : 'Save recommendation');
		saveButton.textContent = itemState.saved ? '★' : '☆';
		detailsButton.className = 'details-button';
		detailsButton.type = 'button';
		detailsButton.setAttribute('aria-expanded', String(itemState.details));
		detailsButton.textContent = itemState.details ? 'Hide details ↑' : 'View details ↓';
		actions.appendChild(completeButton);
		actions.appendChild(saveButton);
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
		emptyState.textContent = recommendations.length ? 'No recommendations match this category yet.' : 'No recommendations are available yet. Complete an assessment to receive personalized next steps.';
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
		if (event.target.closest('.complete-button')) itemState.completed = !itemState.completed;
		if (event.target.closest('.save-button')) itemState.saved = !itemState.saved;
		if (event.target.closest('.details-button')) itemState.details = !itemState.details;
		render();
	});
	filter.addEventListener('change', render);

	if (!window.FinpathAPI.getToken()) {
		window.location.href = 'login.html?next=recommendations.html';
		return;
	}
	window.FinpathAPI.me().then(function () {
		return window.FinpathAPI.listRecommendations();
	}).then(function (result) {
		recommendations = Array.isArray(result) ? result : [];
		state = recommendations.reduce(function (result, item) { result[item.id] = { completed: false, saved: false, details: false }; return result; }, {});
		setFilterOptions();
		document.querySelector('.demo-pill').textContent = 'Live recommendations';
		document.querySelector('.demo-notice').hidden = true;
		document.getElementById('demo-insight').hidden = true;
		document.querySelector('.summary-note').textContent = 'From your latest predictions';
		document.getElementById('list-heading').textContent = 'Your recommendations';
		render();
	}).catch(function (reason) {
		if (reason && reason.status === 401) { window.location.href = 'login.html?next=recommendations.html'; return; }
		showError(reason && reason.message ? reason.message : 'We could not load your recommendations. Please try again.');
	});
}());
