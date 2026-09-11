(function () {
	'use strict';

	var content = document.querySelector('.profile-content');
	var status = document.getElementById('profile-status');
	content.querySelector('.profile-intro').hidden = true;
	content.querySelector('.demo-notice').hidden = true;
	content.querySelector('.profile-grid').hidden = true;
	var editPanel = content.querySelector('.edit-panel');
	if (editPanel) editPanel.remove();

	function showError(message) {
		status.textContent = message;
		status.className = 'form-status alert-danger';
	}

	function render(user) {
		var initials = String(user.full_name || '').split(/\s+/).map(function (part) { return part.charAt(0); }).join('').slice(0, 2).toUpperCase();
		document.querySelector('.demo-pill').textContent = 'Connected profile';
		document.querySelector('.avatar').textContent = initials || 'FP';
		document.getElementById('profile-name').textContent = user.full_name;
		document.getElementById('profile-email').textContent = user.email;
		document.getElementById('profile-role').textContent = user.role;
		document.getElementById('profile-created').textContent = new Date(user.created_at).toLocaleDateString();
		content.querySelector('.profile-intro').hidden = false;
		content.querySelector('.profile-grid').hidden = false;
	}

	if (!window.FinpathAPI.getToken()) {
		window.location.href = 'login.html?next=profile.html';
	} else {
		window.FinpathAPI.me().then(render).catch(function (reason) {
			if (reason && reason.status === 401) { window.location.href = 'login.html?next=profile.html'; return; }
			showError(reason && reason.message ? reason.message : 'We could not load your profile. Please try again.');
		});
	}
}());
