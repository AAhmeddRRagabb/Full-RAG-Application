
const APP_MAIN_ROUTE = "http://localhost:8000/api/v1"

// Sending a Query to FastAPI
const sendBtn = document.querySelector('.query-form .send');
const queryInput = document.getElementById('queryArea');
const messagesArea = document.getElementById('messages');

sendBtn.addEventListener('click', async (e) => {
    e.preventDefault();
    
    const query = queryInput.value;
    const limit = 5;
    

    generateUserMessage(query);
    
    const response = await fetch(
        `${APP_MAIN_ROUTE}/nlp/answer_user_query/mohammed`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                'query': query,
                'limit': limit
            })
        }
    );

    if (!response.ok) {
        console.log("error");
    } else {
        const data = await response.json();

        const answer = data['answer'];
        const full_prompt = data['full_prompt'];
        const chat_history = data['chat_history'];
        
        generateAIMessage(answer);

        console.log(full_prompt);
        console.log(`\n\n${chat_history}`);

    }


})



function generateUserMessage(message) {
    const report = document.createElement("article");
    report.className = "message user-message";

    // content
    const content = document.createElement("div");
    content.classList.add("message-content");
    
    content.innerHTML = `
        ${getReport(message)}
    `;
    
    report.appendChild(content);
    

    // avatar
    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = "A";

    report.appendChild(avatar);
    
    
    messagesArea.appendChild(report);
}



function generateAIMessage(message) {
    const report = document.createElement("article");
    report.className = "message assistant-message";

    // avatar
    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = "AI";

    report.appendChild(avatar);

    // content
    const content = document.createElement("div");
    content.classList.add("message-content");
    
    content.innerHTML = `
        ${getReport(message)}
    `;

    report.appendChild(content);
    messagesArea.appendChild(report);
}

function getReport(aiResponse) {
    return reportHtml = DOMPurify.sanitize(
        marked.parse(aiResponse)
    );
}