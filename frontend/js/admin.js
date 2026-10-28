(function () {
	'use strict';

	var pageSize = 10;
	var currentPage = 1;
	var currentSearch = '';
	var denied = false;
	var usersRequestNumber = 0;
	var usersTotal = 0;
	var recordsRequestNumber = 0;
	var recordsPage = 1;
	var recordsSearch = '';
	var recordsFilter = '';
	var recordsType = '';
	var recordsTotal = 0;
	var operationalPage = 1;
	var operationalTotal = 0;
	var operationalRequestNumber = 0;
	var auditPage = 1;
	var auditTotal = 0;
	var auditRequestNumber = 0;
	var auditActionLabels = {
		'admin.login_succeeded': 'Administrator login succeeded',
		'admin.account_created': 'Administrator account created',
		'admin.account_creation_rejected': 'Administrator account creation rejected',
		'admin.bootstrap_completed': 'Administrator setup completed',
		'user.created_by_admin': 'User account created by administrator',
		'user.creation_rejected': 'User account creation rejected',
		'user.activated': 'User account activated',
		'user.deactivated': 'User account deactivated',
		'user.status_change_rejected': 'User account status change rejected',
		'operational_event.acknowledged': 'Operational event acknowledged'
	};
	var adminState = document.getElementById('admin-state');
	var userListState = document.getElementById('user-list-state');
	var healthState = document.getElementById('health-state');
	var modelMonitoringState = document.getElementById('model-monitoring-state');
	var modelMonitoringDetails = document.getElementById('model-monitoring-details');
	var operationalEventsState = document.getElementById('operational-events-state');
	var operationalEventsTable = document.getElementById('operational-events-table');
	var operationalEventsBody = document.getElementById('operational-events-body');
	var auditLogsState = document.getElementById('audit-logs-state');
	var auditLogsTable = document.getElementById('audit-logs-table');
	var auditLogsBody = document.getElementById('audit-logs-body');
	var usersBody = document.getElementById('admin-users-body');
	var usersTable = document.getElementById('admin-users-table');
	var createUserForm = document.getElementById('create-user-form');
	var createUserState = document.getElementById('create-user-state');
	var createUserButton = document.getElementById('create-user-submit');
	var createAdminForm = document.getElementById('create-admin-form');
	var createAdminState = document.getElementById('create-admin-state');
	var createAdminButton = document.getElementById('create-admin-submit');
	var adminDashboard = document.getElementById('admin-dashboard');
	var firstAdminSetup = document.getElementById('first-admin-setup');
	var firstAdminForm = document.getElementById('first-admin-form');
	var firstAdminState = document.getElementById('first-admin-state');
	var firstAdminButton = document.getElementById('first-admin-submit');
	var bootstrapUnavailable = document.getElementById('admin-bootstrap-unavailable');
	var recordsSection = document.getElementById('admin-records-section');
	var recordsState = document.getElementById('record-list-state');
	var recordsTable = document.getElementById('admin-records-table');
	var recordsHead = document.getElementById('admin-records-head');
	var recordsBody = document.getElementById('admin-records-body');
	var adminSidebar = document.getElementById('admin-sidebar');
	var adminMenuToggle = document.getElementById('admin-menu-toggle');
	var adminMenuBackdrop = document.getElementById('admin-menu-backdrop');

	function setAdminMenuOpen(isOpen) {
		adminSidebar.classList.toggle('is-open', isOpen);
		adminMenuBackdrop.hidden = !isOpen;
		adminMenuToggle.setAttribute('aria-expanded', String(isOpen));
		adminMenuToggle.setAttribute(
			'aria-label',
			isOpen ? 'Close admin navigation' : 'Open admin navigation'
		);
	}

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

	function showBootstrapUnavailable(message) {
		firstAdminSetup.hidden = false;
		firstAdminForm.hidden = true;
		bootstrapUnavailable.textContent = message;
		bootstrapUnavailable.hidden = false;
	}

	function handleFailure(reason, element, fallback) {
		if (reason && reason.status === 401) {
			window.FinpathAPI.clearToken();
			window.location.href = '/admin/login?next=%2Fadmin';
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
			!isCountDistribution(data.risk_category_distribution) ||
			!(data.assessment_completion_rate === null ||
				(typeof data.assessment_completion_rate === 'number' &&
					Number.isFinite(data.assessment_completion_rate) &&
					data.assessment_completion_rate >= 0 && data.assessment_completion_rate <= 1)) ||
			typeof data.generated_at !== 'string' || !data.generated_at || isNaN(Date.parse(data.generated_at))) {
			throw new Error('The system overview response was incomplete or invalid.');
		}
		document.querySelectorAll('[data-stat]').forEach(function (element) {
			element.textContent = String(data[element.getAttribute('data-stat')]);
		});
		document.getElementById('generated-at').textContent = 'Updated ' + new Date(data.generated_at).toLocaleString();
		renderDistribution('assessment-distribution', data.assessment_status_distribution);
		renderDistribution('risk-distribution', data.risk_level_distribution);
		renderDistribution('risk-category-distribution', data.risk_category_distribution);
		document.getElementById('assessment-completion-rate').textContent =
			data.assessment_completion_rate === null
				? 'Not available until assessments are recorded.'
				: Math.round(data.assessment_completion_rate * 100) + '% of recorded assessments completed';
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
		usersTotal = data.total;
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

	function recordColumns(type) {
		if (type === 'assessments') return [
			['id', 'Assessment ID'], ['owner', 'Account'], ['status', 'Status'], ['created_at', 'Created']
		];
		if (type === 'predictions') return [
			['id', 'Prediction ID'], ['owner', 'Account'], ['assessment_id', 'Assessment ID'],
			['risk_level', 'Risk'], ['risk_category', 'Category'], ['probability', 'Probability'],
			['model_version', 'Model'], ['created_at', 'Created']
		];
		return [
			['id', 'Recommendation ID'], ['owner', 'Account'], ['prediction_id', 'Prediction ID'],
			['category', 'Category'], ['priority', 'Priority'], ['recommendation_text', 'Recommendation'],
			['created_at', 'Created']
		];
	}

	function formatRecordValue(item, field) {
		if (field === 'owner') return String(item.full_name) + ' (' + String(item.email) + ')';
		if (field === 'probability') {
			return typeof item.probability === 'number' ? (item.probability * 100).toFixed(1) + '%' : 'Unavailable';
		}
		if (field === 'created_at') {
			var date = new Date(item.created_at);
			return isNaN(date.getTime()) ? 'Unavailable' : date.toLocaleString();
		}
		return item[field] === null || item[field] === undefined ? '—' : String(item[field]);
	}

	function renderRecords(data) {
		if (!data || data.record_type !== recordsType || !Array.isArray(data.items) ||
			!isCount(data.total) || data.page !== recordsPage || data.page_size !== pageSize) {
			throw new Error('The records response was incomplete or invalid.');
		}
		recordsTotal = data.total;
		var lastPage = Math.max(1, Math.ceil(data.total / pageSize));
		if (recordsPage > lastPage) {
			recordsPage = lastPage;
			loadRecords();
			return;
		}

		recordsHead.replaceChildren();
		var headingRow = document.createElement('tr');
		var columns = recordColumns(recordsType);
		columns.forEach(function (column) {
			var heading = document.createElement('th');
			heading.scope = 'col';
			heading.textContent = column[1];
			headingRow.appendChild(heading);
		});
		recordsHead.appendChild(headingRow);
		recordsBody.replaceChildren();
		data.items.forEach(function (item) {
			var row = document.createElement('tr');
			columns.forEach(function (column) {
				var cell = document.createElement('td');
				cell.textContent = formatRecordValue(item, column[0]);
				row.appendChild(cell);
			});
			recordsBody.appendChild(row);
		});
		recordsTable.hidden = data.items.length === 0;
		recordsState.hidden = data.items.length > 0;
		recordsState.textContent = data.items.length ? '' :
			(recordsSearch || recordsFilter ? 'No records match these filters.' : 'No records are available yet.');
		document.getElementById('records-summary').textContent =
			data.total + ' ' + recordsType + (data.total === 1 ? '' : ' records');
		document.getElementById('record-page-summary').textContent = data.total
			? 'Showing ' + ((recordsPage - 1) * pageSize + 1) + '–' + Math.min(recordsPage * pageSize, data.total) + ' of ' + data.total
			: 'No records';
		document.getElementById('records-previous').disabled = recordsPage <= 1;
		document.getElementById('records-next').disabled = recordsPage >= lastPage;
	}

	function loadRecords() {
		if (!recordsType) return;
		var requestNumber = ++recordsRequestNumber;
		recordsSection.hidden = false;
		recordsTable.hidden = true;
		recordsState.hidden = false;
		setMessage(recordsState, 'Loading ' + recordsType + '…', false);
		document.getElementById('records-summary').textContent = 'Loading records…';
		window.FinpathAPI.listAdminRecords(
			recordsType, recordsSearch, recordsFilter, recordsPage, pageSize
		).then(function (data) {
			if (requestNumber === recordsRequestNumber) renderRecords(data);
		}).catch(function (reason) {
			if (requestNumber !== recordsRequestNumber) return;
			if (handleFailure(reason, recordsState, 'Records could not be loaded.')) return;
			setMessage(recordsState, reason && reason.message ? reason.message : 'Records could not be loaded.', true);
			document.getElementById('records-summary').textContent = 'Unavailable';
		});
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
			setMessage(document.getElementById('risk-category-distribution'), message, true);
			setMessage(document.getElementById('assessment-completion-rate'), 'Unavailable: ' + message, true);
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

	function loadModelMonitoring() {
		modelMonitoringDetails.hidden = true;
		setMessage(modelMonitoringState, 'Checking loaded model and recorded predictions…', false);
		window.FinpathAPI.getAdminModelMonitoring().then(function (result) {
			if (!result || typeof result.model_available !== 'boolean' ||
				!(result.model_version === null || typeof result.model_version === 'string') ||
				!isCount(result.recorded_prediction_count) ||
				!isCount(result.explanation_available_count) ||
				!isCount(result.contributing_factors_available_count) ||
				!isCountDistribution(result.recorded_model_versions) ||
				typeof result.generated_at !== 'string' || isNaN(Date.parse(result.generated_at))) {
				throw new Error('The model monitoring response was incomplete or invalid.');
			}
			modelMonitoringState.textContent = 'Updated ' + new Date(result.generated_at).toLocaleString();
			modelMonitoringState.classList.toggle('admin-error-state', false);
			document.getElementById('model-runtime-status').textContent =
				result.model_available ? 'Loaded and available' : 'Unavailable';
			document.getElementById('model-runtime-version').textContent =
				'Loaded version: ' + (result.model_version || 'Not reported');
			document.getElementById('model-prediction-count').textContent =
				result.recorded_prediction_count + ' predictions stored';
			document.getElementById('model-explanation-count').textContent =
				'Explanation available for ' + result.explanation_available_count + ' of ' +
				result.recorded_prediction_count + ' recorded predictions.';
			document.getElementById('model-factor-count').textContent =
				'Contributing factors available for ' +
				result.contributing_factors_available_count + ' recorded predictions.';
			renderDistribution('model-version-distribution', result.recorded_model_versions);
			modelMonitoringDetails.hidden = false;
		}).catch(function (reason) {
			if (handleFailure(reason, modelMonitoringState, 'Model monitoring is unavailable.')) return;
			setMessage(
				modelMonitoringState,
				reason && reason.message ? reason.message : 'Model monitoring is unavailable.',
				true
			);
		});
	}

	function renderOperationalEvents(data) {
		if (!data || !Array.isArray(data.items) || !isCount(data.total) ||
			data.page !== operationalPage || data.page_size !== pageSize ||
			data.items.some(function (item) {
				return !item || !Number.isSafeInteger(item.id) || item.id <= 0 ||
					typeof item.event_type !== 'string' || typeof item.source !== 'string' ||
					typeof item.severity !== 'string' || typeof item.summary !== 'string' ||
					(item.status !== 'open' && item.status !== 'acknowledged') ||
					typeof item.occurred_at !== 'string' || isNaN(Date.parse(item.occurred_at));
			})) {
			throw new Error('The operational-events response was incomplete or invalid.');
		}
		operationalTotal = data.total;
		var lastPage = Math.max(1, Math.ceil(data.total / pageSize));
		if (operationalPage > lastPage) {
			operationalPage = lastPage;
			loadOperationalEvents();
			return;
		}
		operationalEventsBody.replaceChildren();
		data.items.forEach(function (item) {
			var row = document.createElement('tr');
			var isAlert = item.severity === 'warning' || item.severity === 'error' ||
				item.severity === 'critical';
			var classification = item.severity === 'info'
				? 'Informational event'
				: (isAlert
					? (item.status === 'acknowledged' ? 'Acknowledged alert · ' : 'Open alert · ') + item.severity
					: 'Recorded event · ' + item.severity);
			[classification, item.event_type, item.source, item.summary, item.status,
				new Date(item.occurred_at).toLocaleString()].forEach(function (value) {
				var cell = document.createElement('td');
				cell.textContent = value;
				row.appendChild(cell);
			});
			row.children[4].className = 'admin-table-badge is-' + item.status;
			var actionCell = document.createElement('td');
			if (item.status === 'open' &&
				(item.severity === 'warning' || item.severity === 'error' || item.severity === 'critical')) {
				var button = document.createElement('button');
				button.type = 'button';
				button.className = 'btn btn-outline';
				button.dataset.eventId = String(item.id);
				button.textContent = 'Acknowledge';
				actionCell.appendChild(button);
			} else {
				actionCell.textContent = item.acknowledged_at
					? 'Acknowledged' +
						(item.acknowledged_by_user_id
							? ' by admin #' + item.acknowledged_by_user_id
							: '') +
						' · ' + new Date(item.acknowledged_at).toLocaleString()
					: '—';
			}
			row.appendChild(actionCell);
			operationalEventsBody.appendChild(row);
		});
		operationalEventsTable.hidden = data.items.length === 0;
		operationalEventsState.hidden = data.items.length !== 0;
		setMessage(
			operationalEventsState,
			data.items.length ? '' : 'No operational events have been recorded.',
			false
		);
		var pages = lastPage;
		document.getElementById('operational-events-page-summary').textContent =
			'Page ' + operationalPage + ' of ' + pages + ' · ' + operationalTotal + ' events';
		document.getElementById('operational-events-previous').disabled = operationalPage <= 1;
		document.getElementById('operational-events-next').disabled = operationalPage >= pages;
	}

	function loadOperationalEvents() {
		var requestNumber = ++operationalRequestNumber;
		operationalEventsTable.hidden = true;
		operationalEventsState.hidden = false;
		setMessage(operationalEventsState, 'Loading recorded operational events…', false);
		var statusFilter = document.getElementById('operational-status-filter').value;
		var severityFilter = document.getElementById('operational-severity-filter').value;
		window.FinpathAPI.listAdminOperationalEvents(
			operationalPage,
			pageSize,
			statusFilter || null,
			severityFilter || null
		)
			.then(function (data) {
				if (requestNumber === operationalRequestNumber) renderOperationalEvents(data);
			})
			.catch(function (reason) {
				if (requestNumber !== operationalRequestNumber) return;
				if (handleFailure(reason, operationalEventsState, 'Operational events are unavailable.')) return;
				setMessage(
					operationalEventsState,
					reason && reason.message ? reason.message : 'Operational events are unavailable.',
					true
				);
			});
	}

	function loadOperationalSummary() {
		window.FinpathAPI.getAdminOperationalSummary().then(function (result) {
			if (!result || !isCount(result.recorded_error_count) ||
				!isCount(result.open_alert_count) ||
				typeof result.generated_at !== 'string' || isNaN(Date.parse(result.generated_at))) {
				throw new Error('The operational summary response was incomplete or invalid.');
			}
			document.getElementById('operational-summary').textContent =
				result.recorded_error_count + ' recorded errors · ' +
				result.open_alert_count + ' open alerts';
		}).catch(function (reason) {
			if (handleFailure(reason, operationalEventsState, 'Operational summary is unavailable.')) return;
			document.getElementById('operational-summary').textContent = 'Summary unavailable';
		});
	}

	function renderAuditLogs(data) {
		if (!data || !Array.isArray(data.items) || !isCount(data.total) ||
			data.page !== auditPage || data.page_size !== pageSize ||
			data.items.some(function (item) {
				return !item || !Number.isSafeInteger(item.id) || item.id <= 0 ||
					typeof item.action !== 'string' ||
					!(item.actor_user_id === null || Number.isSafeInteger(item.actor_user_id)) ||
					!(item.target_type === null || typeof item.target_type === 'string') ||
					!(item.target_id === null || typeof item.target_id === 'string') ||
					(item.outcome !== 'success' && item.outcome !== 'failure' && item.outcome !== 'unknown') ||
					typeof item.created_at !== 'string' || isNaN(Date.parse(item.created_at));
			})) {
			throw new Error('The audit-log response was incomplete or invalid.');
		}
		auditTotal = data.total;
		var lastPage = Math.max(1, Math.ceil(data.total / pageSize));
		if (auditPage > lastPage) {
			auditPage = lastPage;
			loadAuditLogs();
			return;
		}
		auditLogsBody.replaceChildren();
		data.items.forEach(function (item) {
			var row = document.createElement('tr');
			var actionLabel = auditActionLabels[item.action] || item.action
				.replace(/[._]+/g, ' ')
				.replace(/\b\w/g, function (character) { return character.toUpperCase(); });
			[
				actionLabel,
				item.actor_user_id === null ? 'System/bootstrap' : String(item.actor_user_id),
				item.outcome === 'unknown' ? 'Not recorded (legacy/uninstrumented)' :
					item.outcome.charAt(0).toUpperCase() + item.outcome.slice(1),
				item.target_type ? item.target_type + (item.target_id ? ' #' + item.target_id : '') : '—',
				new Date(item.created_at).toLocaleString()
			].forEach(function (value, index) {
				var cell = document.createElement('td');
				cell.textContent = value;
				if (index === 2) {
					cell.className = 'admin-table-badge is-' + item.outcome;
				}
				row.appendChild(cell);
			});
			auditLogsBody.appendChild(row);
		});
		auditLogsTable.hidden = data.items.length === 0;
		auditLogsState.hidden = data.items.length !== 0;
		var hasAuditFilters = Boolean(
			document.getElementById('audit-action-filter').value.trim() ||
			document.getElementById('audit-actor-filter').value ||
			document.getElementById('audit-outcome-filter').value ||
			document.getElementById('audit-date-from').value ||
			document.getElementById('audit-date-to').value
		);
		setMessage(
			auditLogsState,
			data.items.length ? '' : (hasAuditFilters
				? 'No audit records match these filters.'
				: 'No audit records have been recorded.'),
			false
		);
		var pages = lastPage;
		document.getElementById('audit-logs-page-summary').textContent =
			'Page ' + auditPage + ' of ' + pages + ' · ' + auditTotal + ' records';
		document.getElementById('audit-logs-previous').disabled = auditPage <= 1;
		document.getElementById('audit-logs-next').disabled = auditPage >= pages;
	}

	function loadAuditLogs() {
		var requestNumber = ++auditRequestNumber;
		auditLogsTable.hidden = true;
		auditLogsState.hidden = false;
		setMessage(auditLogsState, 'Loading audit records…', false);
		var dateFrom = document.getElementById('audit-date-from').value;
		var dateTo = document.getElementById('audit-date-to').value;
		var filters = {
			action: document.getElementById('audit-action-filter').value.trim(),
			actorUserId: document.getElementById('audit-actor-filter').value,
			outcome: document.getElementById('audit-outcome-filter').value,
			createdAfter: dateFrom ? new Date(dateFrom + 'T00:00:00.000Z').toISOString() : '',
			createdBefore: dateTo ? new Date(dateTo + 'T23:59:59.999Z').toISOString() : ''
		};
		window.FinpathAPI.listAdminAuditLogs(auditPage, pageSize, filters)
			.then(function (data) {
				if (requestNumber === auditRequestNumber) renderAuditLogs(data);
			})
			.catch(function (reason) {
				if (requestNumber !== auditRequestNumber) return;
				if (handleFailure(reason, auditLogsState, 'Audit records are unavailable.')) return;
				setMessage(
					auditLogsState,
					reason && reason.message ? reason.message : 'Audit records are unavailable.',
					true
				);
			});
	}

	function loadUsers() {
		var requestNumber = ++usersRequestNumber;
		userListState.hidden = false;
		usersTable.hidden = true;
		setMessage(userListState, 'Loading accounts…', false);
		document.getElementById('users-summary').textContent = 'Loading accounts…';
		var activeFilter = document.getElementById('user-active-filter').value;
		var isActive = activeFilter === '' ? null : activeFilter === 'true';
		window.FinpathAPI.listAdminUsers(currentSearch, currentPage, pageSize, isActive).then(function (data) {
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
		loadModelMonitoring();
		loadOperationalSummary();
		loadOperationalEvents();
		loadAuditLogs();
		loadUsers();
	}

	document.getElementById('refresh-admin').addEventListener('click', refresh);
	document.getElementById('operational-events-previous').addEventListener('click', function () {
		if (operationalPage > 1) { operationalPage -= 1; loadOperationalEvents(); }
	});
	document.getElementById('operational-status-filter').addEventListener('change', function () {
		operationalPage = 1;
		loadOperationalEvents();
	});
	document.getElementById('operational-severity-filter').addEventListener('change', function () {
		operationalPage = 1;
		loadOperationalEvents();
	});
	document.getElementById('operational-events-next').addEventListener('click', function () {
		var pages = Math.max(1, Math.ceil(operationalTotal / pageSize));
		if (operationalPage < pages) { operationalPage += 1; loadOperationalEvents(); }
	});
	operationalEventsBody.addEventListener('click', function (event) {
		var button = event.target.closest('button[data-event-id]');
		if (!button) return;
		var eventId = Number(button.dataset.eventId);
		if (!Number.isSafeInteger(eventId) || eventId <= 0) return;
		button.disabled = true;
		window.FinpathAPI.acknowledgeAdminAlert(eventId).then(function () {
			loadOperationalEvents();
			loadOperationalSummary();
			loadAuditLogs();
		}).catch(function (reason) {
			button.disabled = false;
			operationalEventsState.hidden = false;
			if (!handleFailure(reason, operationalEventsState, 'The alert could not be acknowledged.')) {
				loadAuditLogs();
			}
		});
	});
	document.getElementById('audit-logs-previous').addEventListener('click', function () {
		if (auditPage > 1) { auditPage -= 1; loadAuditLogs(); }
	});
	document.getElementById('audit-logs-next').addEventListener('click', function () {
		var pages = Math.max(1, Math.ceil(auditTotal / pageSize));
		if (auditPage < pages) { auditPage += 1; loadAuditLogs(); }
	});
	document.getElementById('audit-filter-form').addEventListener('submit', function (event) {
		event.preventDefault();
		auditPage = 1;
		loadAuditLogs();
	});
	document.getElementById('clear-audit-filters').addEventListener('click', function () {
		document.getElementById('audit-filter-form').reset();
		auditPage = 1;
		loadAuditLogs();
	});
	firstAdminForm.addEventListener('submit', function (event) {
		event.preventDefault();
		var admin = {
			full_name: firstAdminForm.elements.full_name.value.trim(),
			email: firstAdminForm.elements.email.value.trim(),
			password: firstAdminForm.elements.password.value,
			bootstrap_token: firstAdminForm.elements.bootstrap_token.value,
			confirm_existing_owner: firstAdminForm.elements.confirm_existing_owner.checked
		};
		firstAdminButton.disabled = true;
		setMessage(firstAdminState, 'Creating the first administrator account…', false);
		window.FinpathAPI.createFirstAdmin(admin).then(function () {
			firstAdminForm.reset();
			setMessage(firstAdminState, 'Administrator account created. Redirecting to sign in…', false);
			window.location.href = '/admin/login?next=%2Fadmin';
		}).catch(function (reason) {
			setMessage(
				firstAdminState,
				reason && reason.message ? reason.message : 'The first administrator account could not be created.',
				true
			);
		}).finally(function () {
			firstAdminButton.disabled = false;
		});
	});
	createUserForm.addEventListener('submit', function (event) {
		event.preventDefault();
		var user = {
			full_name: createUserForm.elements.full_name.value.trim(),
			email: createUserForm.elements.email.value.trim(),
			password: createUserForm.elements.password.value
		};
		createUserButton.disabled = true;
		setMessage(createUserState, 'Creating account…', false);
		window.FinpathAPI.createAdminUser(user).then(function () {
			createUserForm.reset();
			currentPage = 1;
			currentSearch = '';
			document.getElementById('user-search').value = '';
			setMessage(createUserState, 'Account created. The user can now sign in.', false);
			loadUsers();
			loadAnalytics();
		}).catch(function (reason) {
			if (!handleFailure(reason, createUserState, 'The account could not be created.')) {
				setMessage(
					createUserState,
					reason && reason.message ? reason.message : 'The account could not be created.',
					true
				);
			}
		}).finally(function () {
			createUserButton.disabled = false;
		});
	});
	createAdminForm.addEventListener('submit', function (event) {
		event.preventDefault();
		var admin = {
			full_name: createAdminForm.elements.full_name.value.trim(),
			email: createAdminForm.elements.email.value.trim(),
			password: createAdminForm.elements.password.value
		};
		createAdminButton.disabled = true;
		setMessage(createAdminState, 'Creating administrator account…', false);
		window.FinpathAPI.createAdminAccount(admin).then(function () {
			createAdminForm.reset();
			setMessage(createAdminState, 'Administrator account created. The new administrator can sign in.', false);
			loadUsers();
			loadAnalytics();
		}).catch(function (reason) {
			if (!handleFailure(reason, createAdminState, 'The administrator account could not be created.')) {
				setMessage(
					createAdminState,
					reason && reason.message ? reason.message : 'The administrator account could not be created.',
					true
				);
			}
		}).finally(function () {
			createAdminButton.disabled = false;
		});
	});
	document.getElementById('admin-logout').addEventListener('click', function () {
		window.FinpathAPI.clearToken();
		window.location.href = '/login';
	});
	adminMenuToggle.addEventListener('click', function () {
		setAdminMenuOpen(adminMenuToggle.getAttribute('aria-expanded') !== 'true');
	});
	adminMenuBackdrop.addEventListener('click', function () {
		setAdminMenuOpen(false);
		adminMenuToggle.focus();
	});
	document.addEventListener('keydown', function (event) {
		if (event.key === 'Escape' && adminMenuToggle.getAttribute('aria-expanded') === 'true') {
			setAdminMenuOpen(false);
			adminMenuToggle.focus();
		}
	});
	document.addEventListener('click', function (event) {
		if (adminMenuToggle.getAttribute('aria-expanded') !== 'true') return;
		if (!event.target.closest('#admin-sidebar, #admin-menu-toggle')) {
			setAdminMenuOpen(false);
		}
	});
	document.getElementById('user-search-form').addEventListener('submit', function (event) {
		event.preventDefault();
		currentSearch = document.getElementById('user-search').value.trim();
		currentPage = 1;
		loadUsers();
	});
	document.getElementById('clear-user-search').addEventListener('click', function () {
		document.getElementById('user-search').value = '';
		document.getElementById('user-active-filter').value = '';
		currentSearch = '';
		currentPage = 1;
		loadUsers();
	});
	document.getElementById('users-previous').addEventListener('click', function () {
		if (currentPage > 1) { currentPage -= 1; loadUsers(); }
	});
	document.getElementById('users-next').addEventListener('click', function () {
		var totalPages = Math.max(1, Math.ceil(usersTotal / pageSize));
		if (currentPage < totalPages) { currentPage += 1; loadUsers(); }
	});
	document.getElementById('record-search-form').addEventListener('submit', function (event) {
		event.preventDefault();
		recordsSearch = document.getElementById('record-search').value.trim();
		recordsFilter = document.getElementById('record-filter').value.trim();
		recordsPage = 1;
		loadRecords();
	});
	document.getElementById('clear-record-search').addEventListener('click', function () {
		document.getElementById('record-search').value = '';
		document.getElementById('record-filter').value = '';
		recordsSearch = '';
		recordsFilter = '';
		recordsPage = 1;
		loadRecords();
	});
	document.getElementById('records-previous').addEventListener('click', function () {
		if (recordsPage > 1) { recordsPage -= 1; loadRecords(); }
	});
	document.getElementById('records-next').addEventListener('click', function () {
		var lastPage = Math.max(1, Math.ceil(recordsTotal / pageSize));
		if (recordsPage < lastPage) { recordsPage += 1; loadRecords(); }
	});
	document.querySelectorAll('.side-link[href="#admin-records-section"]').forEach(function (link) {
		link.addEventListener('click', function () {
			if (recordsType) return;
			recordsType = 'assessments';
			document.getElementById('admin-records-heading').textContent = 'Assessments';
			loadRecords();
		});
	});
	document.querySelectorAll('.admin-sidebar .side-link').forEach(function (link) {
		link.addEventListener('click', function () {
			setAdminMenuOpen(false);
			document.querySelectorAll('.admin-sidebar .side-link').forEach(function (item) {
				item.classList.toggle('active', item === link);
				if (item === link) item.setAttribute('aria-current', 'page');
				else item.removeAttribute('aria-current');
			});
		});
	});
	document.querySelectorAll('.admin-stat-link').forEach(function (card) {
		card.addEventListener('click', function () {
			if (card.dataset.recordType) {
				recordsType = card.dataset.recordType;
				recordsPage = 1;
				recordsSearch = '';
				recordsFilter = card.dataset.recordFilter || '';
				document.getElementById('record-search').value = '';
				document.getElementById('record-filter').value = recordsFilter;
				document.getElementById('admin-records-heading').textContent =
					recordsType.charAt(0).toUpperCase() + recordsType.slice(1);
				loadRecords();
			} else if (card.dataset.userActive) {
				document.getElementById('user-search').value = '';
				document.getElementById('user-active-filter').value =
					card.dataset.userActive === 'all' ? '' : card.dataset.userActive;
				currentSearch = '';
				currentPage = 1;
				loadUsers();
			}
		});
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
			window.location.href = '/admin/login?next=%2Fadmin';
			return;
		}
		window.FinpathAPI.me().then(function (user) {
			if (!user || user.role !== 'admin') {
				var forbidden = new Error('Administrator access is required to view this page.');
				forbidden.status = 403;
				throw forbidden;
			}
			adminDashboard.hidden = false;
			document.querySelector('.admin-header').hidden = false;
			setMessage(adminState, 'Administrator access verified. Live data is shown below.', false);
			loadAnalytics();
			loadHealth();
			loadModelMonitoring();
			loadOperationalSummary();
			loadOperationalEvents();
			loadAuditLogs();
			loadUsers();
		}).catch(function (reason) {
			handleFailure(reason, adminState, 'We could not verify administrator access.');
		});
	}

	window.FinpathAPI.getAdminBootstrapStatus().then(function (bootstrapStatus) {
		if (!bootstrapStatus || typeof bootstrapStatus.setup_available !== 'boolean' ||
			typeof bootstrapStatus.administrator_exists !== 'boolean' ||
			typeof bootstrapStatus.setup_configured !== 'boolean') {
			throw new Error('The administrator setup status response was invalid.');
		}
		if (bootstrapStatus.setup_available) {
			firstAdminSetup.hidden = false;
			return;
		}
		if (bootstrapStatus.administrator_exists) {
			load();
			return;
		}
		showBootstrapUnavailable(
			bootstrapStatus.setup_configured
				? 'First administrator setup is unavailable because the configured owner account needs trusted operator review.'
				: 'First administrator setup is not configured. Please contact the system administrator.'
		);
	}).catch(function (reason) {
		showBootstrapUnavailable(
			reason && reason.message
				? reason.message
				: 'Administrator setup status could not be checked. Please try again later.'
		);
	});
}());
