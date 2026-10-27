'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const assessmentScript = fs.readFileSync(
	path.join(__dirname, '..', 'frontend', 'js', 'assessment.js'),
	'utf8'
);
const apiScript = fs.readFileSync(
	path.join(__dirname, '..', 'frontend', 'js', 'api.js'),
	'utf8'
);

function createElement(values = {}) {
	return {
		children: [],
		textContent: '',
		classList: { toggle() {} },
		style: {},
		listeners: {},
		addEventListener(name, callback) { this.listeners[name] = callback; },
		appendChild(child) { this.children.push(child); },
		setAttribute() {},
		focus() {},
		...values
	};
}

async function submitAssessment(entries, predictionBehavior, assessmentBehavior) {
	const elements = new Map();
	const listeners = {};
	const form = {
		addEventListener(name, callback) { listeners[name] = callback; },
		querySelectorAll() { return []; }
	};
	const assessmentPayloads = [];
	const assessmentKeys = [];
	const predictionCalls = [];
	const predictionRecords = [];
	let predictionAttempts = 0;
	let predictionLookups = 0;
	let assessmentAttempts = 0;
	const sessionValues = new Map();

	elements.set('assessment-form', form);
	for (const id of [
		'step-counter',
		'progress-bar',
		'progress-percent',
		'progress-detail',
		'previous-button',
		'next-button',
		'complete-button',
		'validation-summary',
		'review-list',
		'completion-state',
		'completion-title',
		'completion-message',
		'prediction-link'
	]) {
		elements.set(id, id === 'completion-state' ? createElement({ hidden: true }) : createElement());
	}

	const window = {
		FinpathAPI: {
			getToken: () => 'test-token',
			me: () => new Promise(() => {}),
			createAssessment(payload, idempotencyKey) {
				assessmentPayloads.push(payload);
				assessmentKeys.push(idempotencyKey);
				assessmentAttempts += 1;
				if (assessmentBehavior) return assessmentBehavior({
					payload,
					idempotencyKey,
					attempt: assessmentAttempts
				});
				return Promise.resolve({ id: 12 });
			},
			createPrediction(assessmentId) {
				predictionCalls.push(assessmentId);
				predictionAttempts += 1;
				if (predictionBehavior) return predictionBehavior({
					assessmentId,
					attempt: predictionAttempts,
					predictionRecords
				});
				return Promise.reject(new Error('Stop after capturing assessment payload'));
			},
			listPredictions(assessmentId) {
				predictionLookups += 1;
				return Promise.resolve(predictionRecords.filter((prediction) => prediction.assessment_id === assessmentId));
			}
		},
		sessionStorage: {
			getItem(key) { return sessionValues.get(key) || null; },
			setItem(key, value) { sessionValues.set(key, value); },
			removeItem(key) { sessionValues.delete(key); }
		},
		crypto: { randomUUID: () => 'test-idempotency-key' },
		scrollTo() {},
		setTimeout() {}
	};
	const document = {
		getElementById(id) {
			if (!elements.has(id)) elements.set(id, createElement());
			return elements.get(id);
		},
		querySelectorAll(selector) {
			return selector === '.assessment-step' ? [createElement()] : [];
		},
		querySelector: createElement
	};
	class FormDataMock {
		constructor(submittedForm) {
			assert.equal(submittedForm, form);
		}
		entries() {
			return entries[Symbol.iterator]();
		}
	}

	vm.runInNewContext(assessmentScript, { window, document, FormData: FormDataMock });
	async function submit() {
		listeners.submit({ preventDefault() {} });
		await new Promise((resolve) => setImmediate(resolve));
	}
	await submit();

	return {
		submitted: JSON.parse(JSON.stringify(assessmentPayloads[0])),
		assessmentPayloads,
		assessmentKeys,
		predictionCalls,
		get predictionLookups() { return predictionLookups; },
		predictionRecords,
		elements,
		submit
	};
}

test('assessment submission preserves valid FormData fields and omits empty and hidden fields', async () => {
	const { submitted } = await submitAssessment([
		['age_range', '25-34'],
		['sex', 'Female'],
		['employment_status', 'Employed'],
		['monthly_income', '45000'],
		['optional_answer', ''],
		['_hidden_loan_formal', 'No']
	]);

	assert.deepEqual(submitted, {
		assessment_data: {
			age_range: '25-34',
			sex: 'Female',
			employment_status: 'Employed',
			monthly_income: '45000'
		},
		assessment_status: 'completed'
	});
});

test('assessment previous and next preserve entered values and stop at step boundaries', async () => {
	const ids = [
		'step-counter', 'progress-bar', 'progress-percent', 'progress-detail',
		'previous-button', 'next-button', 'complete-button', 'validation-summary',
		'review-list', 'completion-state', 'completion-title', 'completion-message',
		'prediction-link'
	];
	const elements = new Map(ids.map((id) => [id, createElement()]));
	const firstField = createElement({
		value: '25-34',
		checkValidity: () => true,
		closest: () => ({ hidden: false })
	});
	const secondField = createElement({
		value: 'Female',
		checkValidity: () => true,
		closest: () => ({ hidden: false })
	});
	const steps = [
		createElement({
			querySelector: () => createElement({ textContent: 'About you' }),
			querySelectorAll: () => [firstField]
		}),
		createElement({
			querySelector: () => createElement({ textContent: 'Income' }),
			querySelectorAll: () => [secondField]
		}),
		createElement({
			querySelector: () => createElement({ textContent: 'Review' }),
			querySelectorAll: () => []
		})
	];
	const stepItems = steps.map((_, index) =>
		createElement({ querySelector: () => createElement({ textContent: String(index + 1) }) })
	);
	const formListeners = {};
	const form = createElement({
		addEventListener(name, callback) { formListeners[name] = callback; },
		querySelectorAll: () => [firstField, secondField]
	});
	elements.set('assessment-form', form);
	const window = {
		FinpathAPI: {
			getToken: () => 'test-token',
			me: () => Promise.resolve({ id: 1 })
		},
		scrollTo() {}
	};
	const document = {
		getElementById(id) {
			if (!elements.has(id)) elements.set(id, createElement());
			return elements.get(id);
		},
		querySelectorAll(selector) {
			if (selector === '.assessment-step') return steps;
			if (selector === '.step-item') return stepItems;
			return [];
		},
		querySelector(selector) {
			if (selector === '.progress-track') return createElement({ setAttribute() {} });
			if (selector === '.assessment-sidebar') return createElement();
			return createElement();
		},
		createElement
	};
	vm.runInNewContext(assessmentScript, { window, document, FormData });
	await new Promise((resolve) => setImmediate(resolve));

	assert.equal(steps[0].hidden, false);
	elements.get('next-button').listeners.click();
	assert.equal(steps[1].hidden, false);
	assert.equal(firstField.value, '25-34');
	elements.get('previous-button').listeners.click();
	assert.equal(steps[0].hidden, false);
	assert.equal(firstField.value, '25-34');
	elements.get('previous-button').listeners.click();
	assert.equal(steps[0].hidden, false);
	elements.get('next-button').listeners.click();
	elements.get('next-button').listeners.click();
	assert.equal(steps[2].hidden, false);
	assert.equal(firstField.value, '25-34');
	assert.equal(secondField.value, 'Female');
	elements.get('next-button').listeners.click();
	assert.equal(steps[2].hidden, false);
});

test('prediction retry reuses the saved assessment and checks for an existing prediction', async () => {
	const submission = await submitAssessment(
		[['age_range', '25-34']],
		({ assessmentId, attempt, predictionRecords }) => {
			if (attempt === 1) {
				predictionRecords.push({ id: 27, assessment_id: assessmentId });
				return Promise.reject(new Error('The prediction response was interrupted.'));
			}
			return Promise.resolve({ id: 27, assessment_id: assessmentId });
		}
	);

	assert.equal(submission.assessmentPayloads.length, 1);
	assert.deepEqual(submission.predictionCalls, [12]);
	await submission.submit();

	assert.equal(submission.assessmentPayloads.length, 1);
	assert.deepEqual(submission.predictionCalls, [12]);
	assert.equal(submission.predictionLookups, 2);
	assert.equal(submission.elements.get('completion-state').hidden, false);
	assert.equal(submission.elements.get('complete-button').textContent, 'Retry prediction');
});

test('assessment retry reuses its idempotency key after a lost create response', async () => {
	const persistedAssessments = new Map();
	const submission = await submitAssessment(
		[['age_range', '25-34']],
		({ assessmentId, predictionRecords }) => {
			predictionRecords.push({ id: 31, assessment_id: assessmentId });
			return Promise.resolve({ id: 31, assessment_id: assessmentId });
		},
		({ payload, idempotencyKey, attempt }) => {
			if (!persistedAssessments.has(idempotencyKey)) {
				persistedAssessments.set(idempotencyKey, { id: 12, payload });
			}
			if (attempt === 1) return Promise.reject(new Error('The assessment response was interrupted.'));
			return Promise.resolve(persistedAssessments.get(idempotencyKey));
		}
	);

	assert.equal(submission.assessmentPayloads.length, 1);
	await submission.submit();

	assert.equal(submission.assessmentPayloads.length, 2);
	assert.equal(submission.assessmentKeys[0], submission.assessmentKeys[1]);
	assert.equal(persistedAssessments.size, 1);
	assert.deepEqual(submission.predictionCalls, [12]);
	assert.equal(submission.predictionLookups, 1);
	assert.equal(submission.elements.get('completion-state').hidden, false);
});

test('API client sends the assessment idempotency key as a request header', async () => {
	let requestOptions;
	const storage = { getItem: () => null, setItem() {}, removeItem() {} };
	const window = {
		FINPATH_CONFIG: { API_BASE_URL: 'https://api.example.test' },
		localStorage: storage,
		sessionStorage: storage,
		fetch: async (_url, options) => {
			requestOptions = options;
			return { ok: true, text: async () => '{"id":12}' };
		}
	};
	vm.runInNewContext(apiScript, { window });

	await window.FinpathAPI.createAssessment({ assessment_data: {} }, 'test-idempotency-key');

	assert.equal(requestOptions.headers['Idempotency-Key'], 'test-idempotency-key');
	assert.equal(requestOptions.headers['Content-Type'], 'application/json');
});

test('prediction retry creates a prediction for the saved assessment when none exists', async () => {
	const submission = await submitAssessment(
		[['age_range', '25-34']],
		({ assessmentId, attempt }) => attempt === 1
			? Promise.reject(new Error('The prediction service is unavailable.'))
			: Promise.resolve({ id: 28, assessment_id: assessmentId })
	);

	assert.equal(submission.assessmentPayloads.length, 1);
	await submission.submit();

	assert.equal(submission.assessmentPayloads.length, 1);
	assert.deepEqual(submission.predictionCalls, [12, 12]);
	assert.equal(submission.predictionLookups, 2);
	assert.equal(submission.elements.get('completion-state').hidden, false);
});
