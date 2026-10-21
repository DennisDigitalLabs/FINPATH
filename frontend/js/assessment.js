(function () {
	'use strict';

	var form = document.getElementById('assessment-form');
	var steps = Array.prototype.slice.call(document.querySelectorAll('.assessment-step'));
	var stepItems = Array.prototype.slice.call(document.querySelectorAll('.step-item'));
	var counter = document.getElementById('step-counter');
	var progressBar = document.getElementById('progress-bar');
	var progressPercent = document.getElementById('progress-percent');
	var progressTrack = document.querySelector('.progress-track');
	var progressDetail = document.getElementById('progress-detail');
	var previousButton = document.getElementById('previous-button');
	var nextButton = document.getElementById('next-button');
	var completeButton = document.getElementById('complete-button');
	var validationSummary = document.getElementById('validation-summary');
	var reviewList = document.getElementById('review-list');
	var completionState = document.getElementById('completion-state');
	var completionTitle = document.getElementById('completion-title');
	var completionMessage = document.getElementById('completion-message');
	var predictionLink = document.getElementById('prediction-link');
	var currentStep = 0;
	var totalQuestions = steps.length - 1;
	var isSubmitting = false;
	var submittedAssessment = null;
	var assessmentIdempotencyStorageKey = 'finpath_assessment_idempotency_key';

	// Conditional logic: Show/hide loan-related fields based on loan_usage
	var loanUsageField = document.getElementById('loan-usage');
	var formalLoanGroup = document.getElementById('formal-loan-group');
	var informalLoanGroup = document.getElementById('informal-loan-group');
	var digitalCreditGroup = document.getElementById('digital-credit-group');
	var loanAppGroup = document.getElementById('loan-app-group');
	var fulizaGroup = document.getElementById('fuliza-group');
	var loanDefaultGroup = document.getElementById('loan-default-group');

	// Conditional logic: Show/hide mobile money frequency based on mobile_money_use
	var mobileMoneyUseField = document.getElementById('mobile-money-usage');
	var mobileMoneyFrequencyGroup = document.getElementById('mobile-money-frequency-group');

	function updateConditionals() {
		// Handle loan conditional logic
		if (loanUsageField && loanUsageField.value === 'Yes') {
			formalLoanGroup.hidden = false;
			informalLoanGroup.hidden = false;
			digitalCreditGroup.hidden = false;
			loanAppGroup.hidden = false;
			fulizaGroup.hidden = false;
			loanDefaultGroup.hidden = false;
		} else {
			formalLoanGroup.hidden = true;
			informalLoanGroup.hidden = true;
			digitalCreditGroup.hidden = true;
			loanAppGroup.hidden = true;
			fulizaGroup.hidden = true;
			loanDefaultGroup.hidden = true;
			// Clear hidden field values
			[document.getElementById('loan-formal'), document.getElementById('loan-informal'), document.getElementById('digital-credit-usage'), document.getElementById('loan-app-usage'), document.getElementById('fuliza-usage'), document.getElementById('loan-default')].forEach(function(field) {
				if (field) field.value = '';
			});
		}

		// Handle mobile money frequency conditional logic
		if (mobileMoneyUseField && mobileMoneyUseField.value !== 'No') {
			mobileMoneyFrequencyGroup.hidden = false;
		} else {
			mobileMoneyFrequencyGroup.hidden = true;
			// Clear hidden field value
			var freqField = document.getElementById('mobile-money-frequency');
			if (freqField) freqField.value = '';
		}
	}

	function labelFor(field) {
		var label = document.querySelector('label[for="' + field.id + '"]');
		return label ? label.textContent.replace('*', '').trim() : field.name;
	}

	function showStep(index) {
		currentStep = index;
		steps.forEach(function (step, stepIndex) { step.hidden = stepIndex !== index; step.classList.toggle('active', stepIndex === index); });
		stepItems.forEach(function (item, itemIndex) { item.classList.toggle('active', itemIndex === index); item.classList.toggle('done', itemIndex < index); });
		var isReview = index === totalQuestions;
		var percent = Math.round((index / totalQuestions) * 100);
		counter.innerHTML = isReview ? 'Step 8 of 8 <span>Review your answers</span>' : 'Step ' + (index + 1) + ' of ' + totalQuestions + ' <span>' + stepItems[index].querySelector('strong').textContent + '</span>';
		progressBar.style.width = percent + '%';
		progressPercent.textContent = percent + '% complete';
		progressTrack.setAttribute('aria-valuenow', String(percent));
		progressDetail.textContent = isReview ? 'Ready to complete' : (index === 0 ? 'Getting started' : 'Section ' + (index + 1) + ' of ' + totalQuestions);
		previousButton.hidden = index === 0;
		nextButton.hidden = isReview;
		completeButton.hidden = !isReview;
		validationSummary.hidden = true;
		if (isReview) { buildReview(); }
		var heading = steps[index].querySelector('legend, h2');
		if (heading) { heading.focus ? heading.focus() : null; }
		window.scrollTo({ top: 0, behavior: 'smooth' });
	}

	function validateCurrentStep() {
		if (currentStep === totalQuestions) return true;
		var fields = steps[currentStep].querySelectorAll('input, select, textarea');
		var firstInvalid = null;
		Array.prototype.forEach.call(fields, function (field) {
			// Skip hidden fields in validation
			if (field.closest('.form-group').hidden) return;
			var valid = field.checkValidity();
			field.setAttribute('aria-invalid', String(!valid));
			if (!valid && !firstInvalid) firstInvalid = field;
		});
		if (firstInvalid) {
			validationSummary.hidden = false;
			firstInvalid.focus();
			return false;
		}
		return true;
	}

	function showMessage(message, isError) {
		validationSummary.textContent = message;
		validationSummary.classList.toggle('alert-danger', isError);
		validationSummary.classList.toggle('alert-success', !isError);
		validationSummary.hidden = false;
	}

	function redirectToLogin() {
		showMessage('Please sign in before starting an assessment. Redirecting you to login.', true);
		window.setTimeout(function () { window.location.href = 'login.html?next=assessment.html'; }, 900);
	}

	function formDataObject() {
		var data = {};
		for (const entry of new FormData(form).entries()) {
			// Skip empty values and hidden field group values
			if (entry[1] !== '' && !entry[0].startsWith('_hidden_')) {
				data[entry[0]] = entry[1];
			}
		}
		return data;
	}

	function getAssessmentIdempotencyKey() {
		var existingKey = window.sessionStorage.getItem(assessmentIdempotencyStorageKey);
		if (existingKey) return existingKey;
		if (!window.crypto || typeof window.crypto.randomUUID !== 'function') {
			throw new Error('Secure assessment submission is unavailable in this browser. Please update your browser and try again.');
		}
		var key = window.crypto.randomUUID();
		window.sessionStorage.setItem(assessmentIdempotencyStorageKey, key);
		return key;
	}

	function findOrCreatePrediction(assessment) {
		return window.FinpathAPI.listPredictions(assessment.id).then(function (predictions) {
			if (!Array.isArray(predictions)) throw new Error('The prediction history response was invalid.');
			if (predictions.length) return { assessment: assessment, prediction: predictions[0] };
			return window.FinpathAPI.createPrediction(assessment.id).then(function (prediction) {
				return { assessment: assessment, prediction: prediction };
			});
		});
	}

	function handleSubmit() {
		var assessment;
		var predictionRequest;
		if (isSubmitting) return;
		if (!window.FinpathAPI.getToken()) { redirectToLogin(); return; }
		var idempotencyKey;
		if (!submittedAssessment) {
			try {
				idempotencyKey = getAssessmentIdempotencyKey();
			} catch (error) {
				showMessage(error.message, true);
				return;
			}
		}
		isSubmitting = true;
		completeButton.disabled = true;
		nextButton.disabled = true;
		previousButton.disabled = true;
		if (submittedAssessment) {
			showMessage('Checking for an existing prediction...', false);
			predictionRequest = findOrCreatePrediction(submittedAssessment);
		} else {
			showMessage('Submitting your assessment...', false);
			assessment = { assessment_data: formDataObject(), assessment_status: 'completed' };
			predictionRequest = window.FinpathAPI.createAssessment(assessment, idempotencyKey)
				.then(function (created) {
					submittedAssessment = created;
					Array.prototype.forEach.call(form.querySelectorAll('input, select, textarea'), function (field) {
						field.disabled = true;
					});
					completeButton.textContent = 'Retry prediction';
					showMessage('Assessment submitted. Generating your explainable prediction...', false);
					return findOrCreatePrediction(created);
				});
		}
		predictionRequest
			.then(function (result) {
				window.sessionStorage.removeItem(assessmentIdempotencyStorageKey);
				form.hidden = true;
				document.querySelector('.assessment-sidebar').hidden = true;
				validationSummary.hidden = true;
				completionTitle.focus();
				completionMessage.textContent = 'Your assessment and explainable FINPATH prediction are ready.';
				predictionLink.href = 'prediction.html?assessment_id=' + encodeURIComponent(result.assessment.id) + '&prediction_id=' + encodeURIComponent(result.prediction.id);
				completionState.hidden = false;
				completionState.focus();
				window.scrollTo({ top: 0, behavior: 'smooth' });
			})
			.catch(function (reason) {
				isSubmitting = false;
				completeButton.disabled = false;
				nextButton.disabled = false;
				previousButton.disabled = false;
				if (reason && reason.status === 401) { redirectToLogin(); return; }
				showMessage(submittedAssessment
					? 'Your assessment was saved, but prediction generation failed. Select Retry prediction to continue without creating another assessment.'
					: (reason && reason.message ? reason.message : 'We could not complete your assessment. Please try again.'), true);
			});
	}

	function buildReview() {
		reviewList.innerHTML = '';
		var fields = form.querySelectorAll('input, select, textarea');
		Array.prototype.forEach.call(fields, function (field) {
			// Skip empty values and hidden fields
			if (!field.value || field.closest('.form-group').hidden) return;
			var item = document.createElement('div');
			item.className = 'review-item';
			var title = document.createElement('strong');
			var answer = document.createElement('span');
			title.textContent = labelFor(field);
			answer.textContent = field.options ? field.options[field.selectedIndex].text : field.value;
			item.appendChild(title); item.appendChild(answer); reviewList.appendChild(item);
		});
	}

	// Event listeners
	nextButton.addEventListener('click', function () { if (validateCurrentStep()) showStep(currentStep + 1); });
	previousButton.addEventListener('click', function () { showStep(currentStep - 1); });
	form.addEventListener('submit', function (event) {
		event.preventDefault();
		if (!validateCurrentStep()) return;
		handleSubmit();
	});
	form.addEventListener('input', function (event) { 
		if (event.target.matches('[aria-invalid="true"]') && event.target.checkValidity()) event.target.setAttribute('aria-invalid', 'false');
		// Update conditionals on field change
		if (event.target === loanUsageField || event.target === mobileMoneyUseField) {
			updateConditionals();
		}
	});

	// Initialize
	if (!window.FinpathAPI.getToken()) {
		redirectToLogin();
	} else {
		window.FinpathAPI.me().then(function () { showStep(0); }).catch(function (reason) {
			if (reason && reason.status === 401) redirectToLogin();
			else showMessage(reason && reason.message ? reason.message : 'We could not verify your session. Please try again.', true);
		});
	}
}());