(function (window) {
	'use strict';

	var tokenStorageKey = 'finpath_access_token';
	var apiBaseStorageKey = 'finpath_api_base_url';

	function configuredBaseUrl() {
		var configured = window.FINPATH_CONFIG && window.FINPATH_CONFIG.API_BASE_URL;
		var stored = window.localStorage.getItem(apiBaseStorageKey);
		return String(stored || configured || '').replace(/\/$/, '');
	}

	function getToken() {
		return window.localStorage.getItem(tokenStorageKey) || window.sessionStorage.getItem(tokenStorageKey);
	}

	function storeToken(token, remember) {
		window.localStorage.removeItem(tokenStorageKey);
		window.sessionStorage.removeItem(tokenStorageKey);
		(remember ? window.localStorage : window.sessionStorage).setItem(tokenStorageKey, token);
	}

	function clearToken() {
		window.localStorage.removeItem(tokenStorageKey);
		window.sessionStorage.removeItem(tokenStorageKey);
	}

	function errorMessage(status, payload) {
		if (status === 401) return 'Your session has expired. Please sign in again.';
		if (status === 403) return 'You are not authorized to perform this action.';
		if (status === 422) {
			if (Array.isArray(payload && payload.detail)) {
				return payload.detail.map(function (item) { return item.msg || 'Please check the submitted values.'; }).join(' ');
			}
			return (payload && payload.detail) || 'Please check the submitted values.';
		}
		if (status === 503) return 'The prediction service is temporarily unavailable. Please try again later.';
		if (status >= 500) return 'We could not complete that request. Please try again later.';
		return (payload && payload.detail) || 'The request could not be completed.';
	}

	function request(path, options) {
		options = options || {};
		var headers = options.headers || {};
		var token = getToken();
		var requestOptions = {
			method: options.method || 'GET',
			headers: headers
		};
		if (token) headers.Authorization = 'Bearer ' + token;
		if (options.body !== undefined) {
			headers['Content-Type'] = 'application/json';
			requestOptions.body = JSON.stringify(options.body);
		}
		return window.fetch(configuredBaseUrl() + path, requestOptions).then(function (response) {
			return response.text().then(function (text) {
				var payload = null;
				try { payload = text ? JSON.parse(text) : null; } catch (error) { payload = null; }
				if (!response.ok) {
					if (response.status === 401) clearToken();
					var apiError = new Error(errorMessage(response.status, payload));
					apiError.name = 'FinpathApiError';
					apiError.status = response.status;
					apiError.detail = payload && payload.detail;
					throw apiError;
				}
				return payload;
			});
		}).catch(function (error) {
			if (error && error.name === 'FinpathApiError') throw error;
			var networkError = new Error('We could not reach the service. Check your connection and try again.');
			networkError.name = 'FinpathNetworkError';
			throw networkError;
		});
	}

	function get(path) { return request(path); }
	function post(path, body) { return request(path, { method: 'POST', body: body }); }
	function put(path, body) { return request(path, { method: 'PUT', body: body }); }
	function remove(path) { return request(path, { method: 'DELETE' }); }

	var api = {
		getBaseUrl: configuredBaseUrl,
		setBaseUrl: function (url) {
			if (url) window.localStorage.setItem(apiBaseStorageKey, String(url).replace(/\/$/, ''));
			else window.localStorage.removeItem(apiBaseStorageKey);
		},
		getToken: getToken,
		clearToken: clearToken,
		login: function (credentials, remember) {
			return post('/api/v1/auth/login', credentials).then(function (result) {
				storeToken(result.access_token, remember);
				return result;
			});
		},
		register: function (user) { return post('/api/v1/auth/register', user); },
		me: function () { return get('/api/v1/auth/me'); },
		getAuthenticated: get,
		postAuthenticated: post,
		putAuthenticated: put,
		deleteAuthenticated: remove,
		createAssessment: function (data) { return post('/api/v1/assessments', data); },
		listAssessments: function () { return get('/api/v1/assessments'); },
		getAssessment: function (id) { return get('/api/v1/assessments/' + encodeURIComponent(id)); },
		updateAssessment: function (id, data) { return put('/api/v1/assessments/' + encodeURIComponent(id), data); },
		deleteAssessment: function (id) { return remove('/api/v1/assessments/' + encodeURIComponent(id)); },
		createPrediction: function (assessmentId) { return post('/api/v1/predictions', { assessment_id: assessmentId }); },
		getPrediction: function (id) { return get('/api/v1/predictions/' + encodeURIComponent(id)); },
		listPredictions: function (assessmentId) { return get('/api/v1/assessments/' + encodeURIComponent(assessmentId) + '/predictions'); },
		listRecommendations: function () { return get('/api/v1/recommendations'); },
		getRecommendation: function (id) { return get('/api/v1/recommendations/' + encodeURIComponent(id)); },
		getDashboard: function () { return get('/api/v1/dashboard'); },
		getAnalytics: function () { return get('/api/v1/analytics'); },
		getSystemAnalytics: function () { return get('/api/v1/analytics/system'); }
	};

	window.FinpathAPI = api;
}(window));
