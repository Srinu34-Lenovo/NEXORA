// ============================================================
// NEXORA FRONTEND
// ============================================================

"use strict";


// ------------------------------------------------------------
// STORAGE
// ------------------------------------------------------------

// ------------------------------------------------------------
// STATE
// ------------------------------------------------------------

let memories = [];

let tasks = [];

let messages = [];

let currentUser = JSON.parse(
    sessionStorage.getItem("nexora_user") || "null"
);

let pendingRegistrationEmail = sessionStorage.getItem(
    "nexora_pending_registration_email"
) || "";


async function apiRequest(path, options = {}) {

    const headers = new Headers(options.headers || {});
    const token = sessionStorage.getItem("nexora_token");

    if (token) {
        headers.set("Authorization", `Bearer ${token}`);
    }

    const response = await fetch(path, {
        ...options,
        headers
    });
    const payload = await response.json().catch(() => null);

    if (!response.ok) {
        throw new Error(
            payload?.detail || "The backend request failed."
        );
    }

    return payload;
}


// ------------------------------------------------------------
// DOM
// ------------------------------------------------------------

const navItems =
    document.querySelectorAll(".nav-item");

const pages =
    document.querySelectorAll(".page");

const pageTitle =
    document.getElementById("pageTitle");

const pageSubtitle =
    document.getElementById("pageSubtitle");

const chatInput =
    document.getElementById("chatInput");

const sendButton =
    document.getElementById("sendButton");

const messagesContainer =
    document.getElementById("messages");

const profileButton =
    document.getElementById("profileButton");

const loginModal =
    document.getElementById("loginModal");

const closeLogin =
    document.getElementById("closeLogin");

const loginForm =
    document.getElementById("loginForm");

const authNameField =
    document.getElementById("authNameField");

const authPhoneField =
    document.getElementById("authPhoneField");

const authEmailField =
    document.getElementById("authEmailField");

const authPasswordField =
    document.getElementById("authPasswordField");

const authOtpField =
    document.getElementById("authOtpField");

const authModeToggle =
    document.getElementById("authModeToggle");

const authModeFooter =
    document.getElementById("authModeFooter");

const resendOtpButton =
    document.getElementById("resendOtpButton");

let authMode = "login";

const profileName =
    document.getElementById("profileName");

const profileStatus =
    document.getElementById("profileStatus");


// ------------------------------------------------------------
// PAGE NAVIGATION
// ------------------------------------------------------------

const pageInfo = {

    chat: {
        title: "Chat",
        subtitle: "Your personal AI intelligence system"
    },

    memory: {
        title: "Memory",
        subtitle: "NEXORA's long-term memory"
    },

    tasks: {
        title: "Tasks",
        subtitle: "Manage your goals and tasks"
    },

    search: {
        title: "Search",
        subtitle: "Search your knowledge base"
    },

    agents: {
        title: "AI Agents",
        subtitle: "Autonomous AI workflows"
    },

    data: {
        title: "Data",
        subtitle: "NEXORA intelligence dashboard"
    }

};


function openPage(page) {

    pages.forEach(p => {

        p.classList.remove("active");

    });


    navItems.forEach(item => {

        item.classList.remove("active");

    });


    const selectedPage =
        document.getElementById(page + "Page");

    const selectedNav =
        document.querySelector(
            `.nav-item[data-page="${page}"]`
        );


    if (selectedPage) {

        selectedPage.classList.add("active");

    }


    if (selectedNav) {

        selectedNav.classList.add("active");

    }


    if (pageInfo[page]) {

        pageTitle.textContent =
            pageInfo[page].title;

        pageSubtitle.textContent =
            pageInfo[page].subtitle;

    }


    if (page === "data") {

        updateDashboard();

    }

}


navItems.forEach(item => {

    item.addEventListener("click", () => {

        openPage(item.dataset.page);

    });

});


// ------------------------------------------------------------
// CHAT
// ------------------------------------------------------------

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function formatMessageBody(value) {
    const safeValue = escapeHtml(value || "");
    return safeValue
        .replace(/\n{2,}/g, "</p><p>")
        .replace(/\n/g, "<br>");
}

function renderMessage(message) {

    const type = message.role === "user" ? "user" : "assistant";
    const wrapper = document.createElement("div");
    wrapper.className = `message ${type}`;

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.textContent = type === "user" ? "👤" : "◆";

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";

    const header = document.createElement("div");
    header.className = "message-header";

    const name = document.createElement("span");
    name.textContent = type === "user" ? "YOU" : "NEXORA";

    const stamp = document.createElement("span");
    const timestamp = message.created_at
        ? new Date(message.created_at).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit"
        })
        : new Date().toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit"
        });
    stamp.textContent = timestamp;
    stamp.className = "message-time";

    header.append(name, stamp);

    const body = document.createElement("div");
    body.className = "message-body";
    body.innerHTML = `<p>${formatMessageBody(message.content)}</p>`;

    bubble.append(header, body);
    wrapper.append(avatar, bubble);
    messagesContainer.appendChild(wrapper);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}


async function loadChatHistory() {

    try {
        messages = await apiRequest("/chat/history?limit=100");
        messagesContainer.innerHTML = "";

        if (messages.length === 0) {
            renderMessage({
                role: "assistant",
                content: "Hello! I'm NEXORA. 🧠 I can help you manage your memories and tasks."
            });
        } else {
            messages.forEach(renderMessage);
        }

        updateDashboard();
    } catch {
        messagesContainer.innerHTML = `
            <div class="empty-state">
                <h3>Conversation unavailable</h3>
                <p>Check the backend connection and try again.</p>
            </div>
        `;
    }
}


async function sendMessage() {

    const text = chatInput.value.trim();
    if (!text || sendButton.disabled) {
        return;
    }

    const userMessage = { role: "user", content: text };
    messages.push(userMessage);
    renderMessage(userMessage);
    chatInput.value = "";
    sendButton.disabled = true;

    try {
        const result = await apiRequest("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text })
        });
        const assistantMessage = {
            role: "assistant",
            content: result.response
        };
        messages.push(assistantMessage);
        renderMessage(assistantMessage);
        updateDashboard();
        loadTasks();
    } catch (error) {
        showToast(error.message || "Unable to send message.");
    } finally {
        sendButton.disabled = false;
    }
}


sendButton.addEventListener("click", sendMessage);


chatInput.addEventListener(
    "keydown",
    event => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            sendMessage();
        }
    }
);


// ------------------------------------------------------------
// SUGGESTIONS
// ------------------------------------------------------------

document
    .querySelectorAll(".suggestion")
    .forEach(button => {

        button.addEventListener(
            "click",
            () => {

                chatInput.value =
                    button.textContent.trim();

                chatInput.focus();

            }
        );

    });


// ------------------------------------------------------------
// MEMORY
// ------------------------------------------------------------

const addMemoryButton =
    document.getElementById(
        "addMemoryButton"
    );

const memoryInputBox =
    document.getElementById(
        "memoryInputBox"
    );

const memoryInput =
    document.getElementById(
        "memoryInput"
    );

const saveMemory =
    document.getElementById(
        "saveMemory"
    );

const cancelMemory =
    document.getElementById(
        "cancelMemory"
    );

const memoryList =
    document.getElementById(
        "memoryList"
    );

const memorySearchForm =
    document.getElementById(
        "memorySearchForm"
    );

const memorySearchInput =
    document.getElementById(
        "memorySearchInput"
    );

let visibleMemories = [];
let memoryRequestId = 0;


addMemoryButton.addEventListener(
    "click",
    () => {

        memoryInputBox.classList.remove(
            "hidden"
        );

        memoryInput.focus();

    }
);


cancelMemory.addEventListener(
    "click",
    () => {

        memoryInput.value = "";

        memoryInputBox.classList.add(
            "hidden"
        );

    }
);


saveMemory.addEventListener(
    "click",
    async () => {

        const text = memoryInput.value.trim();
        if (!text) {
            showToast("Enter something to remember.");
            return;
        }

        saveMemory.disabled = true;

        try {
            await apiRequest("/memory", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ content: text })
            });

            memoryInput.value = "";
            memoryInputBox.classList.add("hidden");

            const loaded = await loadMemories(
                memorySearchInput.value.trim()
            );
            showToast(
                loaded
                    ? "Memory saved successfully."
                    : "Memory saved, but the list could not refresh."
            );
        } catch {
            showToast("Unable to save memory.");
        } finally {
            saveMemory.disabled = false;
        }
    }
);


function normalizeMemory(memory) {

    return {
        id: memory.id,
        text: memory.content,
        category: memory.category,
        created: memory.created_at
    };
}


async function loadMemories(query = "") {

    const requestId = ++memoryRequestId;
    const endpoint = query
        ? `/memory/search?q=${encodeURIComponent(query)}`
        : "/memory";

    try {
        const loadedMemories = (await apiRequest(endpoint))
            .map(normalizeMemory);

        if (requestId !== memoryRequestId) {
            return false;
        }

        visibleMemories = loadedMemories;
        if (!query) {
            memories = loadedMemories;
        }

        renderMemories();
        updateDashboard();
        return true;
    } catch {
        if (requestId === memoryRequestId) {
            memoryList.innerHTML = `
                <div class="empty-state">
                    <h3>Memories unavailable</h3>
                    <p>Check the backend connection and try again.</p>
                </div>
            `;
        }

        return false;
    }
}


memorySearchForm.addEventListener(
    "submit",
    event => {
        event.preventDefault();
        loadMemories(memorySearchInput.value.trim());
    }
);


function renderMemories() {

    memoryList.innerHTML = "";

    if (visibleMemories.length === 0) {
        const searching = Boolean(memorySearchInput.value.trim());
        memoryList.innerHTML = `
            <div class="empty-state">
                <div>🧠</div>
                <h3>${searching ? "No matching memories" : "No memories yet"}</h3>
                <p>${searching ? "Try another search." : "Add information that NEXORA should remember."}</p>
            </div>
        `;
        return;
    }

    visibleMemories.forEach(memory => {
        const card = document.createElement("div");
        card.className = "memory-card";

        const text = document.createElement("p");
        text.textContent = memory.text;

        const deleteButton = document.createElement("button");
        deleteButton.className = "delete-memory";
        deleteButton.textContent = "×";
        deleteButton.setAttribute("aria-label", "Delete memory");

        deleteButton.addEventListener(
            "click",
            async () => {
                deleteButton.disabled = true;

                try {
                    await apiRequest(
                        `/memory/${memory.id}`,
                        { method: "DELETE" }
                    );

                    memories = memories.filter(
                        item => item.id !== memory.id
                    );
                    await loadMemories(
                        memorySearchInput.value.trim()
                    );
                    showToast("Memory deleted.");
                } catch {
                    deleteButton.disabled = false;
                    showToast("Unable to delete memory.");
                }
            }
        );

        card.appendChild(text);
        card.appendChild(deleteButton);
        memoryList.appendChild(card);
    });
}


// ------------------------------------------------------------
// TASKS
// ------------------------------------------------------------

const addTaskButton =
    document.getElementById(
        "addTaskButton"
    );

const taskInputBox =
    document.getElementById(
        "taskInputBox"
    );

const taskInput =
    document.getElementById(
        "taskInput"
    );

const saveTask =
    document.getElementById(
        "saveTask"
    );

const taskList =
    document.getElementById(
        "taskList"
    );


addTaskButton.addEventListener(
    "click",
    () => {

        taskInputBox.classList.remove(
            "hidden"
        );

        taskInput.focus();

    }
);


saveTask.addEventListener(
    "click",
    createTask
);


taskInput.addEventListener(
    "keydown",
    event => {

        if (event.key === "Enter") {

            createTask();

        }

    }
);


async function loadTasks() {

    try {
        tasks = (await apiRequest("/tasks")).map(task => ({
            ...task,
            text: task.title,
            completed: task.status === "completed"
        }));
        renderTasks();
        updateDashboard();
        return true;
    } catch (error) {
        taskList.innerHTML = `
            <div class="empty-state">
                <h3>Tasks unavailable</h3>
                <p>${escapeHtml(error.message)}</p>
            </div>
        `;
        return false;
    }
}


async function createTask() {

    const text = taskInput.value.trim();
    if (!text) {
        showToast("Enter a task.");
        return;
    }

    saveTask.disabled = true;
    try {
        await apiRequest("/tasks", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title: text })
        });
        taskInput.value = "";
        taskInputBox.classList.add("hidden");
        await loadTasks();
        showToast("Task created successfully.");
    } catch (error) {
        showToast(error.message || "Unable to create task.");
    } finally {
        saveTask.disabled = false;
    }
}


function renderTasks() {

    taskList.innerHTML = "";
    if (tasks.length === 0) {
        taskList.innerHTML = `
            <div class="empty-state">
                <div>✅</div>
                <h3>No tasks</h3>
                <p>Create your first task.</p>
            </div>
        `;
        return;
    }

    tasks.forEach(task => {
        const item = document.createElement("div");
        item.className = "task-item";
        if (task.completed) {
            item.classList.add("completed");
        }

        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.checked = task.completed;
        checkbox.setAttribute("aria-label", `Complete ${task.text}`);
        checkbox.addEventListener("change", async () => {
            checkbox.disabled = true;
            try {
                await apiRequest(`/tasks/${task.id}`, {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        status: checkbox.checked ? "completed" : "pending"
                    })
                });
                await loadTasks();
            } catch (error) {
                checkbox.checked = task.completed;
                checkbox.disabled = false;
                showToast(error.message || "Unable to update task.");
            }
        });

        const span = document.createElement("span");
        span.textContent = task.text;

        const deleteButton = document.createElement("button");
        deleteButton.className = "delete-task";
        deleteButton.textContent = "×";
        deleteButton.setAttribute("aria-label", `Delete ${task.text}`);
        deleteButton.addEventListener("click", async () => {
            deleteButton.disabled = true;
            try {
                await apiRequest(`/tasks/${task.id}`, {
                    method: "DELETE"
                });
                await loadTasks();
                showToast("Task deleted.");
            } catch (error) {
                deleteButton.disabled = false;
                showToast(error.message || "Unable to delete task.");
            }
        });

        item.append(checkbox, span, deleteButton);
        taskList.appendChild(item);
    });
}


// ------------------------------------------------------------
// SEARCH
// ------------------------------------------------------------

const searchInput =
    document.getElementById(
        "searchInput"
    );

const searchButton =
    document.getElementById(
        "searchButton"
    );

const searchResults =
    document.getElementById(
        "searchResults"
    );


async function performSearch() {

    const query = searchInput.value.trim();
    if (!query) {
        showToast("Enter something to search.");
        return;
    }

    searchButton.disabled = true;
    searchResults.innerHTML = "<p>Searching...</p>";

    try {
        const results = await apiRequest(
            `/search?q=${encodeURIComponent(query)}`
        );
        searchResults.innerHTML = "";

        if (!results.memories.length && !results.tasks.length) {
            const empty = document.createElement("div");
            empty.className = "empty-state";
            const heading = document.createElement("h3");
            heading.textContent = "No results";
            const message = document.createElement("p");
            message.textContent = `NEXORA couldn't find anything matching "${query}".`;
            empty.append(heading, message);
            searchResults.appendChild(empty);
            return;
        }

        results.memories.forEach(item => {
            addSearchResult("Memory", item.content);
        });
        results.tasks.forEach(item => {
            const description = item.description
                ? `${item.title} · ${item.description}`
                : item.title;
            addSearchResult("Task", description);
        });
    } catch (error) {
        searchResults.innerHTML = "";
        const message = document.createElement("p");
        message.textContent = error.message || "Search is unavailable.";
        searchResults.appendChild(message);
    } finally {
        searchButton.disabled = false;
    }
}


function addSearchResult(type, text) {

    const result =
        document.createElement("div");

    result.className =
        "search-result";


    const title =
        document.createElement("strong");

    title.textContent =
        type;


    const content =
        document.createElement("p");

    content.textContent =
        text;


    content.style.marginTop =
        "6px";

    content.style.color =
        "#91a0b5";


    result.appendChild(title);

    result.appendChild(content);

    searchResults.appendChild(result);

}


searchButton.addEventListener(
    "click",
    performSearch
);


searchInput.addEventListener(
    "keydown",
    event => {

        if (event.key === "Enter") {

            performSearch();

        }

    }
);


// ------------------------------------------------------------
// AI AGENTS
// ------------------------------------------------------------

document
    .querySelectorAll(".agent-button")
    .forEach(button => {

        button.addEventListener(
            "click",
            async () => {
                const agentName = button
                    .closest(".agent-card")
                    .querySelector("h3")
                    .textContent;

                openPage("chat");
                chatInput.value = `Act as the ${agentName}. ${button.closest(".agent-card").querySelector("p").textContent}`;
                await sendMessage();
            }
        );

    });


// ------------------------------------------------------------
// LOGIN
// ------------------------------------------------------------

profileButton.addEventListener(
    "click",
    () => {
        if (currentUser) {
            currentUser = null;
            sessionStorage.removeItem("nexora_user");
            sessionStorage.removeItem("nexora_token");
            updateProfile();
            showToast("Signed out.");
            return;
        }

        if (pendingRegistrationEmail) {
            document.getElementById("loginEmail").value = pendingRegistrationEmail;
            document.getElementById("loginEmail").readOnly = true;
            setAuthMode("verify");
        }
        loginModal.classList.remove("hidden");
    }
);


closeLogin.addEventListener(
    "click",
    () => {

        loginModal.classList.add(
            "hidden"
        );

    }
);


loginModal.addEventListener(
    "click",
    event => {

        if (
            event.target === loginModal
        ) {

            loginModal.classList.add(
                "hidden"
            );

        }

    }
);


function setAuthMode(mode) {

    authMode = mode;
    const registering = mode === "register";
    const verifying = mode === "verify";
    authNameField.classList.toggle("hidden", !registering);
    authPhoneField.classList.toggle("hidden", !registering);
    authEmailField.classList.toggle("hidden", verifying);
    authPasswordField.classList.toggle("hidden", verifying);
    authOtpField.classList.toggle("hidden", !verifying);
    document.getElementById("loginName").required = registering;
    document.getElementById("loginPhone").required = registering;
    document.getElementById("loginEmail").required = !verifying;
    document.getElementById("loginPassword").required = !verifying;
    document.getElementById("loginPassword").minLength = 8;
    document.getElementById("loginOtp").required = verifying;
    authModeToggle.classList.toggle("hidden", verifying);
    authModeFooter.classList.toggle("hidden", verifying);

    document.getElementById("authTitle").textContent = verifying
        ? "Verify your contact details"
        : registering
            ? "Create your NEXORA account"
            : "Welcome to NEXORA";
    document.getElementById("authDescription").textContent = verifying
        ? `Enter the six-digit code sent to ${pendingRegistrationEmail} and your phone.`
        : registering
            ? "We will verify your email and phone before activating your account."
            : "Sign in to your personal intelligence system.";
    document.getElementById("authSubmitLabel").textContent = verifying
        ? "Verify and create account"
        : registering
            ? "Send verification code"
            : "Sign In";
    document.getElementById("authModePrompt").textContent = registering
        ? "Already have an account?"
        : "New to NEXORA?";
    authModeToggle.textContent = registering
        ? "Sign in"
        : "Create an account";
}


authModeToggle.addEventListener("click", () => {
    setAuthMode(authMode === "login" ? "register" : "login");
});


let resendCooldownTimer;


function startResendCooldown() {

    clearInterval(resendCooldownTimer);
    let secondsRemaining = 60;
    resendOtpButton.disabled = true;
    resendOtpButton.textContent = `Resend in ${secondsRemaining}s`;

    resendCooldownTimer = setInterval(() => {
        secondsRemaining -= 1;
        if (secondsRemaining <= 0) {
            clearInterval(resendCooldownTimer);
            resendOtpButton.disabled = false;
            resendOtpButton.textContent = "Resend code";
            return;
        }
        resendOtpButton.textContent = `Resend in ${secondsRemaining}s`;
    }, 1000);
}


resendOtpButton.addEventListener("click", async () => {

    resendOtpButton.disabled = true;
    try {
        await apiRequest("/auth/register/resend", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: pendingRegistrationEmail })
        });
        startResendCooldown();
        showToast("A new verification code was sent.");
    } catch (error) {
        resendOtpButton.disabled = false;
        showToast(error.message || "Unable to resend code.");
    }
});


loginForm.addEventListener("submit", async event => {

    event.preventDefault();
    const name = document.getElementById("loginName").value.trim();
    const email = document.getElementById("loginEmail").value.trim();
    const password = document.getElementById("loginPassword").value;
    const phoneNumber = document.getElementById("loginPhone").value.trim();
    const code = document.getElementById("loginOtp").value.trim();
    const submit = loginForm.querySelector("button[type='submit']");

    submit.disabled = true;
    try {
        if (authMode === "register") {
            await apiRequest("/auth/register", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    username: name,
                    email,
                    password,
                    phone_number: phoneNumber
                })
            });

            pendingRegistrationEmail = email;
            sessionStorage.setItem(
                "nexora_pending_registration_email",
                email
            );
            document.getElementById("loginEmail").readOnly = true;
            setAuthMode("verify");
            startResendCooldown();
            showToast("Enter the code sent to your email and phone.");
            return;
        }

        const session = authMode === "verify"
            ? await apiRequest("/auth/register/verify", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    email: pendingRegistrationEmail,
                    code
                })
            })
            : await apiRequest("/auth/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password })
            });

        sessionStorage.setItem("nexora_token", session.access_token);
        currentUser = {
            name: session.user.username,
            email: session.user.email,
            loggedIn: true
        };
        sessionStorage.setItem("nexora_user", JSON.stringify(currentUser));
        updateProfile();
        loginModal.classList.add("hidden");
        loginForm.reset();
        pendingRegistrationEmail = "";
        sessionStorage.removeItem("nexora_pending_registration_email");
        document.getElementById("loginEmail").readOnly = false;
        setAuthMode("login");
        showToast(`Welcome, ${currentUser.name}.`);
    } catch (error) {
        showToast(error.message || "Authentication failed.");
    } finally {
        submit.disabled = false;
    }
});


function updateProfile() {

    if (currentUser && currentUser.loggedIn) {

        profileName.textContent =
            currentUser.name;

        profileStatus.textContent =
            "Signed in";

    } else {

        profileName.textContent =
            "Guest User";

        profileStatus.textContent =
            "Not signed in";

    }

}


// ------------------------------------------------------------
// DASHBOARD
// ------------------------------------------------------------

function updateDashboard() {

    document.getElementById(
        "memoryCount"
    ).textContent =
        memories.length;


    document.getElementById(
        "taskCount"
    ).textContent =
        tasks.length;


    document.getElementById(
        "messageCount"
    ).textContent =
        messages.length;

}


// ------------------------------------------------------------
// BACKEND STATUS
// ------------------------------------------------------------

async function checkBackend() {

    const status =
        document.getElementById(
            "backendStatus"
        );


    try {

        const response =
            await fetch("/docs");


        if (response.ok) {

            status.textContent =
                "Connected";

            status.style.color =
                "#22c55e";

        } else {

            throw new Error();

        }

    } catch {

        status.textContent =
            "Offline";

        status.style.color =
            "#f59e0b";

    }

}


// ------------------------------------------------------------
// TOAST
// ------------------------------------------------------------

let toastTimer;


function showToast(message) {

    const toast =
        document.getElementById(
            "toast"
        );

    const toastMessage =
        document.getElementById(
            "toastMessage"
        );


    toastMessage.textContent =
        message;


    toast.classList.add(
        "show"
    );


    clearTimeout(toastTimer);


    toastTimer =
        setTimeout(
            () => {

                toast.classList.remove(
                    "show"
                );

            },
            2500
        );

}


// ------------------------------------------------------------
// SECURITY
// ------------------------------------------------------------

function escapeHtml(value) {

    const div =
        document.createElement("div");

    div.textContent =
        value;

    return div.innerHTML;

}


// ------------------------------------------------------------
// MOBILE
// ------------------------------------------------------------

const mobileMenu =
    document.getElementById(
        "mobileMenu"
    );


mobileMenu.addEventListener(
    "click",
    () => {

        document
            .querySelector(".sidebar")
            .classList.toggle("open");

    }
);


// ------------------------------------------------------------
// INITIALIZATION
// ------------------------------------------------------------

async function initialize() {

    updateProfile();
    updateDashboard();
    await Promise.all([
        loadChatHistory(),       
        loadMemories(),
        loadTasks()
    ]);
    checkBackend();

}


initialize();