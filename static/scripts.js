let sessionEnded = false;
let timerStarted = false;

async function sendMessage() {
    if (sessionEnded) {
        alert("Session has ended. No more messages can be sent.");
        return;
    }

    let userInput = document.getElementById('user-input');
    let chatHistory = document.getElementById('chat-history');
    let thinkingIndicator = document.getElementById('thinking');

    const userMessage = userInput.value.trim();

    if (!userMessage) return;

    if (!timerStarted) {
        timerStarted = true;
        const sessionDuration = 2 * 60 * 1000; 
        const warningTime = 1 * 60 * 1000; 

        setTimeout(() => {
            alert("⚠️ One minute remaining.");
        }, warningTime);

        setTimeout(async () => {
            sessionEnded = true;
            alert("Session has ended. You will now be redirected.");

            const sessionNumber = parseInt(document.body.dataset.sessionNumber);

            const response = await fetch('/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({message: "[SESSION TIMEOUT]"})
            });

            const data = await response.json();

            if (data.redirect) {
                window.location.href = data.redirect;
            } else {
                window.location.href = `/chatbot_questionnaire/${sessionNumber}`;
            }

        }, sessionDuration);
    }

    const userMessageDiv = document.createElement('div');
    userMessageDiv.classList.add('message', 'user-message');
    userMessageDiv.innerText = userMessage;
    chatHistory.appendChild(userMessageDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;

    userInput.value = "";

    thinkingIndicator.style.display = 'flex';

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({message: userMessage})
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        thinkingIndicator.style.display = 'none';

        if (data.redirect) {
            alert(data.reply);
            window.location.href = data.redirect;
            return; 
        }

        const botMessageDiv = document.createElement('div');
        botMessageDiv.classList.add('message', 'bot-message');

        if (data.session_end) {
            sessionEnded = true;
            botMessageDiv.innerText = data.reply;
            chatHistory.appendChild(botMessageDiv);
            chatHistory.scrollTop = chatHistory.scrollHeight;
            alert(data.reply);
            window.location.href = data.redirect;
        } else if (data.reply) {
            botMessageDiv.innerText = data.reply;
            chatHistory.appendChild(botMessageDiv);
            chatHistory.scrollTop = chatHistory.scrollHeight;
        } else {
            botMessageDiv.innerText = "[No reply from server]";
            chatHistory.appendChild(botMessageDiv);
            chatHistory.scrollTop = chatHistory.scrollHeight;
        }

    } catch (error) {
        thinkingIndicator.style.display = 'none';
        const errorDiv = document.createElement('div');
        errorDiv.classList.add('message', 'bot-message');
        errorDiv.innerText = `[Error: ${error.message}]`;
        chatHistory.appendChild(errorDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;
        console.error("Error fetching response:", error);
    }
}


document.getElementById('user-input').addEventListener('keyup', function(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
});
