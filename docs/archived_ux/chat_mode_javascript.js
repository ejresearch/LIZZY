        async function sendMessage() {
            const input = document.getElementById('chat-input');
            const sendBtn = document.getElementById('send-btn');
            const message = input.value.trim();

            if (!message) return;

            // Disable input
            input.disabled = true;
            sendBtn.disabled = true;

            // Add user message to history
            chatHistory.push({
                role: 'user',
                content: message
            });

            // Clear input
            input.value = '';

            // Render immediately
            renderChatMessages();

            try {
                // Send to backend
                const response = await fetch('/api/brainstorm/chat/query', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        project: currentProject,
                        query: message,
                        focused_scene: focusedScene
                    })
                });

                const data = await response.json();

                if (data.success) {
                    // Add assistant response
                    chatHistory.push({
                        role: 'assistant',
                        id: data.message_id,
                        experts: data.experts
                    });

                    renderChatMessages();
                } else {
                    showMessage(data.error || 'Failed to get response', 'error');
                }
            } catch (error) {
                console.error('Error sending message:', error);
                showMessage('Error: ' + error.message, 'error');
            } finally {
                input.disabled = false;
                sendBtn.disabled = false;
                input.focus();
            }
        }

