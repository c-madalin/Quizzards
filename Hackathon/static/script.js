function uploadFile() {
    const input = document.createElement('input');
    input.type = 'file';
    input.onchange = function(event) {
        const file = event.target.files[0];
        if (file) {
            const formData = new FormData();
            formData.append('file', file);
            
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('File uploaded successfully: ' + data.filename);
                    location.reload(); // Reload to update the file list
                } else {
                    alert('Error: ' + data.error);
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });
        }
    };
    input.click();
}

function deleteFile(filename) {
    if (confirm(`Are you sure you want to delete "${filename}"?`)) {
        fetch('/delete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ filename: filename })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('File deleted successfully');
                location.reload(); // Reload to update the file list
            } else {
                alert('Error: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
    }
}

function sendMessage() {
    const chatInput = document.getElementById('chatInput');
    const message = chatInput.value.trim();
    if (!message) {
        alert('Please enter a message');
        return;
    }

    fetch('/submit_chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: message })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const chatMessages = document.getElementById('chat-messages');
            const userMessage = document.createElement('div');
            userMessage.textContent = 'You: ' + message;
            chatMessages.appendChild(userMessage);

            const aiMessage = document.createElement('div');
            aiMessage.textContent = 'AI: ' + data.ai_response;
            chatMessages.appendChild(aiMessage);

            chatInput.value = ''; // Clear input field
        } else {
            alert('Error: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

function toggleMenu() {
    const menu = document.getElementById('menu');
    menu.classList.toggle('open');
}