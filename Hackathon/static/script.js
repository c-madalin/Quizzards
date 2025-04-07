let confirmCallback = null;
        let confirmContext = null;
        
        // Show a popup with custom message, title and type
        function showPopup(message, title = "Notification", type = "info", showCancel = false) {
            const popupContainer = document.getElementById('popup-container');
            const popupTitle = document.getElementById('popup-title');
            const popupContent = document.getElementById('popup-content');
            const popupConfirmBtn = document.getElementById('popup-confirm-btn');
            const popupCancelBtn = document.getElementById('popup-cancel-btn');
            
            // Set title and message
            popupTitle.textContent = title;
            popupContent.textContent = message;
            
            // Set popup type
            const popup = document.querySelector('.popup');
            popup.className = 'popup'; // Reset class
            popup.classList.add('popup-' + type);
            
            // Show/hide cancel button
            popupCancelBtn.style.display = showCancel ? 'block' : 'none';
            
            // Show the popup
            popupContainer.style.display = 'flex';
            
            // Return a promise to handle async confirmation
            return new Promise((resolve) => {
                confirmCallback = (result) => {
                    resolve(result);
                };
            });
        }
        
        // Confirm action
        function confirmPopup() {
            if (confirmCallback) {
                confirmCallback(true);
            }
            closePopup();
        }
        
        // Close popup
        function closePopup() {
            const popupContainer = document.getElementById('popup-container');
            popupContainer.style.display = 'none';
            
            if (confirmCallback) {
                confirmCallback(false);
            }
        }
        
        // Show a confirmation dialog
        async function showConfirmation(message, title = "Confirmation") {
            return await showPopup(message, title, "warning", true);
        }
        
        // Show success message
        function showSuccess(message, title = "Success") {
            return showPopup(message, title, "success");
        }
        
        // Show error message
        function showError(message, title = "Error") {
            return showPopup(message, title, "error");
        }

        // Updated uploadFile function
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
                            showSuccess(`Fișier încărcat cu succes: ${data.filename}`, 'Încărcare reușită');
                            location.reload(); // Reload to update the file list
                        } else {
                            showError(`Eroare: ${data.error}`, 'Eroare de încărcare');
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        showError('A apărut o eroare la încărcarea fișierului.', 'Eroare de rețea');
                    });
                }
            };
            input.click();
        }

        // Updated deleteFile function
        async function deleteFile(filename) {
            const confirmed = await showConfirmation(`Sigur doriți să ștergeți fișierul "${filename}"?`, 'Confirmare ștergere');
            
            if (confirmed) {
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
                        showSuccess('Fișier șters cu succes', 'Ștergere reușită');
                        location.reload(); // Reload to update the file list
                    } else {
                        showError(`Eroare: ${data.error}`, 'Eroare la ștergere');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showError('A apărut o eroare la ștergerea fișierului.', 'Eroare de rețea');
                });
            }
        }

        // Updated sendMessage function
        function sendMessage() {
            const chatInput = document.getElementById('chatInput');
            const message = chatInput.value.trim();
            if (!message) {
                return;
            }

            const chatMessages = document.getElementById('chat-messages');
            
            // Add user message
            const userMessageRow = document.createElement('div');
            userMessageRow.className = 'message-row user-message-row';
            
            const userMessageDiv = document.createElement('div');
            userMessageDiv.className = 'message user-message';
            
            const userMessageContent = document.createElement('div');
            userMessageContent.className = 'message-content';
            userMessageContent.textContent = message;
            
            const userMessageTime = document.createElement('div');
            userMessageTime.className = 'message-time';
            userMessageTime.textContent = getCurrentTime();
            
            userMessageDiv.appendChild(userMessageContent);
            userMessageDiv.appendChild(userMessageTime);
            userMessageRow.appendChild(userMessageDiv);
            
            chatMessages.appendChild(userMessageRow);
            
            // Show typing indicator
            const typingRow = document.createElement('div');
            typingRow.className = 'message-row ai-message-row';
            typingRow.innerHTML = `
                <div class="ai-avatar">AI</div>
                <div class="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            `;
            chatMessages.appendChild(typingRow);
            
            // Clear input field and scroll to bottom
            chatInput.value = '';
            chatMessages.scrollTop = chatMessages.scrollHeight;

            // Send the message to the server
            fetch('/submit_chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            })
            .then(response => response.json())
            .then(data => {
                // Remove typing indicator
                chatMessages.removeChild(typingRow);
                
                if (data.success) {
                    // Add AI message
                    const aiMessageRow = document.createElement('div');
                    aiMessageRow.className = 'message-row ai-message-row';
                    
                    const aiAvatar = document.createElement('div');
                    aiAvatar.className = 'ai-avatar';
                    aiAvatar.textContent = 'AI';
                    
                    const aiMessageDiv = document.createElement('div');
                    aiMessageDiv.className = 'message ai-message';
                    
                    const aiMessageContent = document.createElement('div');
                    aiMessageContent.className = 'message-content';
                    aiMessageContent.textContent = data.ai_response;
                    
                    const aiMessageTime = document.createElement('div');
                    aiMessageTime.className = 'message-time';
                    aiMessageTime.textContent = getCurrentTime();
                    
                    aiMessageDiv.appendChild(aiMessageContent);
                    aiMessageDiv.appendChild(aiMessageTime);
                    
                    aiMessageRow.appendChild(aiAvatar);
                    aiMessageRow.appendChild(aiMessageDiv);
                    
                    chatMessages.appendChild(aiMessageRow);
                    
                    // Scroll to bottom
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                } else {
                    // Handle error
                    const errorMessageRow = document.createElement('div');
                    errorMessageRow.className = 'message-row ai-message-row';
                    
                    const errorMessage = document.createElement('div');
                    errorMessage.className = 'message ai-message error-message';
                    errorMessage.textContent = 'Eroare: ' + data.error;
                    
                    errorMessageRow.appendChild(errorMessage);
                    chatMessages.appendChild(errorMessageRow);
                    
                    // Show popup error
                    showError(`Eroare: ${data.error}`, 'Eroare de comunicare');
                }
            })
            .catch(error => {
                // Remove typing indicator
                chatMessages.removeChild(typingRow);
                
                // Show error message in chat
                const errorMessageRow = document.createElement('div');
                errorMessageRow.className = 'message-row ai-message-row';
                
                const errorMessage = document.createElement('div');
                errorMessage.className = 'message ai-message error-message';
                errorMessage.textContent = 'Eroare de conexiune. Încercați din nou.';
                
                errorMessageRow.appendChild(errorMessage);
                chatMessages.appendChild(errorMessageRow);
                
                // Show popup error
                showError('Eroare de conexiune. Încercați din nou.', 'Eroare de rețea');
                
                console.error('Error:', error);
            });
        }
        
        // Function to get current time in HH:MM format
        function getCurrentTime() {
            const now = new Date();
            const hours = now.getHours().toString().padStart(2, '0');
            const minutes = now.getMinutes().toString().padStart(2, '0');
            return `${hours}:${minutes}`;
        }
        
        // Allow pressing Enter to send a message
        document.getElementById('chatInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });

function toggleMenu() {
    const menu = document.getElementById('menu');
    menu.classList.toggle('open');
}

