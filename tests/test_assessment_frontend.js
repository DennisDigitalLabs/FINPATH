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

function createElement() {
	return {
		classList: { toggle() {} },
		style: {},
		addEventListener() {},
		setAttribute() {}
	};
}

async function submitAssessment(entries) {
	const elements = new Map();
	const listeners = {};
	const form = {
		addEventListener(name, callback) { listeners[name] = callback; }
	};
	const assessmentPayloads = [];

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
		elements.set(id, createElement());
	}

	const window = {
		FinpathAPI: {
			getToken: () => 'test-token',
			me: () => new Promise(() => {}),
			createAssessment(payload) {
				assessmentPayloads.push(payload);
				return Promise.resolve({ id: 12 });
			},
			createPrediction: () => Promise.reject(new Error('Stop after capturing assessment payload'))
		},
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
	listeners.submit({ preventDefault() {} });
	await new Promise((resolve) => setImmediate(resolve));

	return JSON.parse(JSON.stringify(assessmentPayloads[0]));
}

test('assessment submission preserves valid FormData fields and omits empty and hidden fields', async () => {
	const submitted = await submitAssessment([
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
