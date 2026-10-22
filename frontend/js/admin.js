(function () {
	'use strict';

	var pageSize = 10;
	var currentPage = 1;
	var currentSearch = '';
	var denied = false;
	var usersRequestNumber = 0;
	var adminState = document.getElementById('admin-state');
	var userListState = document.getElementById('user-list-state');
	var healthState = document.getElementById('health-state');
	var usersBody = document.getElementById('admin-users-body');
	var usersTable = document.getElementById('admin-users-table');

	function setMessage(element, message, isError) {
		element.textContent = message;
		element.classList.toggle('admin-error-state', Boolean(isError));
	}

	function showDenied(message) {
		if (denied) return;
		denied = true;
		var layout = document.querySelector('.admin-layout');
		var errorState = document.createElement('div');
		var homeLink = document.createElement('a');
		errorState.className = 'admin-notice admin-error-state';
		errorState.setAttribute('role', 'alert');
		errorState.textContent = message;
		homeLink.className = 'btn btn-outline';
		homeLink.href = '/';
		homeLink.textContent = 'Return home';
		layout.className = 'container admin-denied';
		layout.replaceChildren(errorState, homeLink);
		document.querySelector('.admin-header').remove();
	}

	function handleFailure(reason, element, fallback) {
		if (reason && reason.status === 401) {
			window.FinpathAPI.clearToken();
			window.location.href = '/login?next=/admin';
			return true;
		}
		if (reason && reason.status === 403) {
			showDenied('Administrator access is required to view this page.');
			return true;
		}
		setMessage(element, reason && reason.message ? reason.message : fallback, true);
		return false;
	}

	function renderDistribution(targetId, values) {
		var list = document.getElementById(targetId);
		list.replaceChildren();
		Object.keys(values).forEach(function (key) {
			var row = document.createElement('div');
			var label = document.createElement('span');
			var count = document.createElement('b');
			label.textContent = key;
			count.textContent = String(values[key]);
			row.appendChild(label);
			row.appendChild(count);
			list.appendChild(row);
		});
		if (!Object.keys(values).length) {
			var empty = document.createElement('p');
			empty.textContent = 'No records available yet.';
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

	function renderAnalytics(data) {
		var countFields = [
			'user_count', 'active_user_count', 'total_assessments',
			'completed_assessments', 'prediction_count', 'recommendation_count'
		];
		if (!data || !countFields.every(function (field) { return isCount(data[field]); }) ||
			!isCountDistribution(data.assessment_status_distribution) ||
			!isCountDistribution(data.risk_level_distribution) ||
			typeof data.generated_at !== 'string' || !data.generated_at || isNaN(Date.parse(data.generated_at))) {
			throw new Error('The system overview response was incomplete or invalid.');
		}
		document.querySelectorAll('[data-stat]').forEach(function (element) {
			element.textContent = String(data[element.getAttribute('data-stat')]);
		});
		document.getElementById('generated-at').textContent = 'Updated ' + new Date(data.generated_at).toLocaleString();
		renderDistribution('assessment-distribution', data.assessment_status_distribution);
		renderDistribution('risk-distribution', data.risk_level_distribution);
	}

	function isUser(value) {
		return value && Number.isSafeInteger(value.id) && value.id > 0 &&
			typeof value.full_name === 'string' && typeof value.email === 'string' &&
			typeof value.role === 'string' && typeof value.is_active === 'boolean' &&
			typeof value.created_at === 'string' && !isNaN(Date.parse(value.created_at));
	}

	function renderUsers(data) {
		if (!data || !Array.isArray(data.items) || !isCount(data.total) ||
			data.page !== currentPage || data.page_size !== pageSize ||
			!data.items.every(isUser)) {
			throw new Error('The user list response was incomplete or invalid.');
		}
		var lastPage = Math.max(1, Math.ceil(data.total / pageSize));
		if (currentPage > lastPage) {
			currentPage = lastPage;
			loadUsers();
			return;
		}

		usersBody.replaceChildren();
		usersTable.hidden = data.items.length === 0;
		if (!data.items.length) {
			setMessage(userListState, currentSearch ? 'No matching accounts were found.' : 'No user accounts are available yet.', false);
		} else {
			userListState.textContent = '';
			userListState.hidden = true;
			data.items.forEach(function (user) {
				var row = document.createElement('tr');
				var account = document.createElement('td');
				var name = document.createElement('strong');
				var email = document.createElement('small');
				var role = document.createElement('td');
				var statusCell = document.createElement('td');
				var statusLabel = document.createElement('span');
				var created = document.createElement('td');
				var actionCell = document.createElement('td');
				name.textContent = user.full_name;
				email.textContent = user.email;
				account.appendChild(name);
				account.appendChild(email);
				role.textContent = user.role;
				statusLabel.className = 'admin-account-status ' + (user.is_active ? 'is-active' : 'is-inactive');
				statusLabel.textContent = user.is_active ? 'Active' : 'Inactive';
				statusCell.appendChild(statusLabel);
				created.textContent = new Date(user.created_at).toLocaleDateString();
				if (user.role === 'user') {
					var action = document.createElement('button');
					action.className = 'user-status-action';
					action.type = 'button';
					action.dataset.userId = String(user.id);
					action.dataset.active = String(!user.is_active);
					action.textContent = user.is_active ? 'Deactivate' : 'Reactivate';
					action.setAttribute('aria-label', (user.is_active ? 'Deactivate ' : 'Reactivate ') + user.full_name);
					actionCell.appendChild(action);
				} else {
					actionCell.textContent = 'Protected';
				}
				[account, role, statusCell, created, actionCell].forEach(function (cell) { row.appendChild(cell); });
				usersBody.appendChild(row);
			});
		}
		document.getElementById('users-summary').textContent = data.total + ' account' + (data.total === 1 ? '' : 's');
		document.getElementById('user-page-summary').textContent = data.total ?
			'Showing ' + ((currentPage - 1) * pageSize + 1) + '–' + Math.min(currentPage * pageSize, data.total) + ' of ' + data.total :
			'No accounts';
		document.getElementById('users-previous').disabled = currentPage <= 1;
		document.getElementById('users-next').disabled = currentPage >= lastPage;
	}

	function loadAnalytics() {
		document.getElementById('generated-at').textContent = 'Loading live totals…';
		window.FinpathAPI.getSystemAnalytics().then(renderAnalytics).catch(function (reason) {
			if (handleFailure(reason, adminState, 'System overview is unavailable.')) return;
			document.querySelectorAll('[data-stat]').forEach(function (element) { element.textContent = 'Unavailable'; });
			var message = reason && reason.message ? reason.message : 'System totals unavailable';
			document.getElementById('generated-at').textContent = message;
			setMessage(document.getElementById('assessment-distribution'), message, true);
			setMessage(document.getElementById('risk-distribution'), message, true);
		});
	}

	function loadHealth() {
		setMessage(healthState, 'Checking backend and database…', false);
		window.FinpathAPI.getAdminHealth().then(function (result) {
			if (!result || result.status !== 'healthy' || result.database !== 'available' ||
				typeof result.checked_at !== 'string' || isNaN(Date.parse(result.checked_at))) {
				throw new Error('The system health response was incomplete or invalid.');
			}
			healthState.replaceChildren();
			var status = document.createElement('div');
			var label = document.createElement('strong');
			var checked = document.createElement('small');
			status.className = 'admin-health-status';
			label.textContent = 'Healthy';
			checked.textContent = 'Database available · checked ' + new Date(result.checked_at).toLocaleString();
			status.appendChild(label);
			status.appendChild(checked);
			healthState.appendChild(status);
		}).catch(function (reason) {
			if (handleFailure(reason, healthState, 'System health is unavailable.')) return;
			setMessage(healthState, reason && reason.message ? reason.message : 'System health is unavailable.', true);
		});
	}

	function loadUsers() {
		var requestNumber = ++usersRequestNumber;
		userListState.hidden = false;
		usersTable.hidden = true;
		setMessage(userListState, 'Loading accounts…', false);
		document.getElementById('users-summary').textContent = 'Loading accounts…';
		window.FinpathAPI.listAdminUsers(currentSearch, currentPage, pageSize).then(function (data) {
			if (requestNumber === usersRequestNumber) renderUsers(data);
		}).catch(function (reason) {
			if (requestNumber !== usersRequestNumber) return;
			if (handleFailure(reason, userListState, 'Accounts could not be loaded.')) return;
			setMessage(userListState, reason && reason.message ? reason.message : 'Accounts could not be loaded.', true);
			document.getElementById('users-summary').textContent = 'Unavailable';
		});
	}

	function refresh() {
		setMessage(adminState, 'Refreshing live administration data…', false);
		loadAnalytics();
		loadHealth();
		loadUsers();
	}

	document.getElementById('refresh-admin').addEventListener('click', refresh);
	document.getElementById('admin-logout').addEventListener('click', function () {
		window.FinpathAPI.clearToken();
		window.location.href = '/login';
	});
	document.getElementById('user-search-form').addEventListener('submit', function (event) {
		event.preventDefault();
		currentSearch = document.getElementById('user-search').value.trim();
		currentPage = 1;
		loadUsers();
	});
	document.getElementById('clear-user-search').addEventListener('click', function () {
		document.getElementById('user-search').value = '';
		currentSearch = '';
		currentPage = 1;
		loadUsers();
	});
	document.getElementById('users-previous').addEventListener('click', function () {
		if (currentPage > 1) { currentPage -= 1; loadUsers(); }
	});
	document.getElementById('users-next').addEventListener('click', function () {
		currentPage += 1;
		loadUsers();
	});
	usersBody.addEventListener('click', function (event) {
		var button = event.target.closest('button[data-user-id]');
		if (!button) return;
		var userId = Number(button.dataset.userId);
		var active = button.dataset.active === 'true';
		var action = active ? 'Reactivate' : 'Deactivate';
		if (!Number.isSafeInteger(userId) || userId <= 0 ||
			!window.confirm(action + ' this user account?')) return;
		button.disabled = true;
		window.FinpathAPI.setAdminUserActive(userId, active).then(function () {
			loadUsers();
			loadAnalytics();
		}).catch(function (reason) {
			button.disabled = false;
			handleFailure(reason, userListState, 'The account status could not be updated.');
			if (!denied && (!reason || reason.status !== 401)) {
				setMessage(userListState, reason && reason.message ? reason.message : 'The account status could not be updated.', true);
			}
		});
	});

	function load() {
		if (!window.FinpathAPI.getToken()) {
			window.location.href = '/login?next=/admin';
			return;
		}
		window.FinpathAPI.me().then(function (user) {
			if (!user || user.role !== 'admin') {
				var forbidden = new Error('Administrator access is required to view this page.');
				forbidden.status = 403;
				throw forbidden;
			}
			setMessage(adminState, 'Administrator access verified. Live data is shown below.', false);
			loadAnalytics();
			loadHealth();
			loadUsers();
		}).catch(function (reason) {
			handleFailure(reason, adminState, 'We could not verify administrator access.');
		});
	}

	load();
}());
