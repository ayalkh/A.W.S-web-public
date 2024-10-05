document.addEventListener('DOMContentLoaded', function() {
    const formInputs = document.querySelectorAll('.login-form input[type="text"], .login-form input[type="password"], .profile-container form input[type="text"], .profile-container form input[type="tel"], .profile-container form select');
    
    formInputs.forEach(input => {
        input.addEventListener('focus', function() {
            this.style.borderColor = '#007bff';
        });

        input.addEventListener('blur', function() {
            this.style.borderColor = '#ddd';
        });
    });

    const submitButtons = document.querySelectorAll('.login-form input[type="submit"], .profile-container form button[type="submit"]');
    
    submitButtons.forEach(button => {
        button.addEventListener('mousedown', function() {
            this.style.backgroundColor = '#004080';
        });

        button.addEventListener('mouseup', function() {
            this.style.backgroundColor = '#007bff';
        });
    });
});

function editUserInfo() {
    var elements = document.querySelectorAll('.user-info input, .user-info select');
    for (var i = 0; i < elements.length; i++) {
        elements[i].disabled = false;
    }
    document.getElementById('save-button').style.display = 'inline';
    document.getElementById('edit-button').style.display = 'none';
}

function saveUserInfo() {
    document.getElementById('user-info-form').submit();
}

function deleteChild(url) {
    if (confirm("Are you sure you want to delete this child?")) {
        window.location.href = url;
    }
}
//Export Session Data Button
function exportSessions() {
    fetch('/export_sessions/{{ child.id }}')
        .then(response => response.blob())
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = 'sessions_export.csv';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
        })
        .catch(error => console.error('Error:', error));
}