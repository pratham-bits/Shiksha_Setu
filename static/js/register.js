// static/js/register.js
document.addEventListener('DOMContentLoaded', function() {
    const registerForm = document.getElementById('registerForm');
    const submitBtn = document.getElementById('submitBtn');
    const statusMessage = document.getElementById('statusMessage');

    registerForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const username = document.getElementById('username').value.trim();
        const email = document.getElementById('email').value.trim();
        
        if (!username || !email) {
            showStatus('Please fill in all fields', 'error');
            return;
        }

        if (username.length < 3) {
            showStatus('Username must be at least 3 characters long', 'error');
            return;
        }

        if (!isValidEmail(email)) {
            showStatus('Please enter a valid email address', 'error');
            return;
        }

        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Sending Verification Code...';
        showStatus('Sending verification code to your email...', 'info');
        
        setTimeout(() => {
            registerForm.submit();
        }, 1000);
    });

    function showStatus(message, type) {
        statusMessage.textContent = message;
        statusMessage.className = `alert alert-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'}`;
        statusMessage.classList.remove('d-none');
        
        if (type !== 'error') {
            setTimeout(() => {
                statusMessage.classList.add('d-none');
            }, 5000);
        }
    }

    function isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }
});