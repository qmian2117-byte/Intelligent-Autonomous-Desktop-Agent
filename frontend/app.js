// DesktopPilot AI Dashboard Controller

const API_BASE = "http://127.0.0.1:8000/api/v1";
const WS_URL = "ws://127.0.0.1:8000/ws/telemetry";

let activeToken = null;
let socket = null;
let voiceOutputEnabled = true;
let continuousVoiceEnabled = false;
let isListening = false;
let recognition = null;

let isAgentSpeaking = false;
let micErrorBackoff = false;

function initSpeechRecognition() {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
        console.warn("Web Speech API not supported in this browser.");
        return null;
    }

    const rec = new SpeechRec();
    rec.continuous = false;
    rec.interimResults = true;
    rec.lang = "en-US";

    rec.onstart = () => {
        isListening = true;
        const micBtn = document.getElementById("mic-btn");
        const micLabel = document.getElementById("mic-label");
        if (micBtn) micBtn.classList.add("listening");
        if (micLabel) micLabel.innerText = "Listening...";
        addLog("[VOICE MIC] 🎤 Listening for your voice command...", "system");
    };

    rec.onresult = (event) => {
        let transcript = "";
        let isFinal = false;
        for (let i = event.resultIndex; i < event.results.length; i++) {
            transcript += event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                isFinal = true;
            }
        }
        const input = document.getElementById("goal-input");
        if (input) input.value = transcript;

        if (isFinal && transcript.trim().length > 0) {
            const finalCmd = transcript.trim().replace(/[.?!,]+$/, "");
            addLog(`[VOICE RECOGNIZED] 🗣️ "${finalCmd}"`, "success");
            sendGoalToBackend(finalCmd);
            if (input) input.value = "";
        }
    };

    rec.onerror = (event) => {
        if (event.error !== "no-speech") {
            addLog(`[VOICE WARNING] Mic error: ${event.error}`, "warning");
        }
        if (event.error === "not-allowed" || event.error === "service-not-allowed") {
            micErrorBackoff = true;
            continuousVoiceEnabled = false;
            const btn = document.getElementById("continuous-mic-btn");
            if (btn) {
                btn.classList.remove("active");
                btn.innerText = "🎙️ Hands-Free Mode: OFF";
            }
        }
        stopMicUI();
    };

    rec.onend = () => {
        stopMicUI();
        // Feedback loop prevention: NEVER restart mic if assistant is currently speaking audio
        if (continuousVoiceEnabled && !isAgentSpeaking && !micErrorBackoff) {
            setTimeout(() => {
                if (continuousVoiceEnabled && !isAgentSpeaking && !micErrorBackoff) {
                    try {
                        rec.start();
                    } catch (e) {}
                }
            }, 600);
        }
    };

    return rec;
}

function stopMicUI() {
    isListening = false;
    const micBtn = document.getElementById("mic-btn");
    const micLabel = document.getElementById("mic-label");
    if (micBtn) micBtn.classList.remove("listening");
    if (micLabel) micLabel.innerText = "Speak";
}

function toggleMicListening() {
    if (!recognition) {
        recognition = initSpeechRecognition();
    }
    if (!recognition) {
        addLog("[VOICE ERROR] Browser Speech Recognition not available. Use Chrome or Edge.", "error");
        return;
    }

    if (isListening) {
        continuousVoiceEnabled = false;
        recognition.stop();
        stopMicUI();
    } else {
        try {
            recognition.start();
        } catch (e) {
            console.warn(e);
        }
    }
}

function toggleContinuousVoice() {
    continuousVoiceEnabled = !continuousVoiceEnabled;
    const btn = document.getElementById("continuous-mic-btn");
    if (btn) {
        btn.classList.toggle("active", continuousVoiceEnabled);
        btn.innerText = continuousVoiceEnabled ? "🎙️ Hands-Free Mode: ON" : "🎙️ Hands-Free Mode: OFF";
    }
    if (continuousVoiceEnabled) {
        addLog("[VOICE MODE] Hands-Free Continuous Listening activated!", "success");
        if (!isListening) toggleMicListening();
    } else {
        addLog("[VOICE MODE] Hands-Free Continuous Listening turned off.", "system");
        if (recognition && isListening) recognition.stop();
    }
}

function toggleVoiceOutput() {
    voiceOutputEnabled = !voiceOutputEnabled;
    const btn = document.getElementById("tts-toggle-btn");
    if (btn) {
        btn.classList.toggle("active", voiceOutputEnabled);
        btn.innerText = voiceOutputEnabled ? "🔊 Voice Reply: ON" : "🔇 Voice Reply: OFF";
    }
    if (!voiceOutputEnabled && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
    }
}

function speakAgentResponse(text) {
    if (!voiceOutputEnabled || !("speechSynthesis" in window)) return;
    try {
        window.speechSynthesis.cancel();
        // Immediately pause / stop microphone while speaking response
        if (recognition && isListening) {
            try { recognition.stop(); } catch(e) {}
            stopMicUI();
        }
        isAgentSpeaking = true;

        // Clean symbols/emojis and long paths for natural speech
        const cleanSpeech = text
            .replace(/[•📁🚀🔍📋🌐🖥️⚙️✍️⬇️🤖✅🧪]/g, "")
            .split("\n")[0]
            .slice(0, 220);
        const utterance = new SpeechSynthesisUtterance(cleanSpeech);
        utterance.rate = 1.05;
        utterance.pitch = 1.0;

        const onFinishedSpeaking = () => {
            isAgentSpeaking = false;
            // Safely resume continuous listening after TTS output has ceased
            if (continuousVoiceEnabled && recognition && !micErrorBackoff) {
                setTimeout(() => {
                    if (continuousVoiceEnabled && !isAgentSpeaking && !micErrorBackoff) {
                        try { recognition.start(); } catch (e) {}
                    }
                }, 400);
            }
        };

        utterance.onend = onFinishedSpeaking;
        utterance.onerror = onFinishedSpeaking;

        window.speechSynthesis.speak(utterance);
    } catch (e) {
        isAgentSpeaking = false;
        console.warn("TTS error:", e);
    }
}

function setGoal(text) {
    const input = document.getElementById("goal-input");
    if (input) {
        input.value = text;
        const form = document.getElementById("task-form");
        if (form) form.dispatchEvent(new Event('submit'));
    }
}

function scrollToSection(id) {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: "smooth" });
}

document.addEventListener("DOMContentLoaded", () => {
    initWebSocket();
    testHealth();

    const form = document.getElementById("task-form");
    if (form) {
        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            const input = document.getElementById("goal-input");
            const goal = input.value.trim();
            if (!goal) return;

            await sendGoalToBackend(goal);
            input.value = "";
        });
    }
});

async function sendGoalToBackend(goal) {
    addLog(`[USER] Submitted goal: "${goal}"`, "system");
    setRunningState(true);
    document.getElementById("planner-output").innerText = `Analyzing: "${goal}"`;

    try {
        const res = await fetch(`${API_BASE}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: goal })
        });

        const data = await res.json();
        handleAgentResponse(data);
        return data;
    } catch (err) {
        addLog(`[ERROR] Backend connection failed: ${err.message}`, "error");
        setRunningState(false);
        return null;
    }
}

async function runFullDiagnosticSuite() {
    const testCases = [
        { name: "Task 7 (System Telemetry)", prompt: "ram usage" },
        { name: "Task 7 (Volume Typo Understanding)", prompt: "vlume low" },
        { name: "Task 2 (File Search)", prompt: "find settings.py" },
        { name: "Task 4 (Clipboard AI)", prompt: "summarize clipboard" },
        { name: "Task 6 (Screenshot Capture)", prompt: "take a screenshot" },
        { name: "Task 6 (Screen Understanding)", prompt: "explain screen" },
        { name: "Task 3 & 9 (Smart Organizer)", prompt: "organize downloads" }
    ];

    addLog("=== 🧪 STARTING AUTOMATED DIAGNOSTIC SUITE (7 SAFE LIVE TESTS) ===", "warning");
    let passed = 0;

    for (let i = 0; i < testCases.length; i++) {
        const tc = testCases[i];
        addLog(`[TEST ${i + 1}/${testCases.length}] Testing ${tc.name} -> "${tc.prompt}"`, "system");
        const result = await sendGoalToBackend(tc.prompt);
        if (result && result.status === "completed") {
            passed++;
        }
        await new Promise(r => setTimeout(r, 500));
    }

    addLog(`=== ✅ DIAGNOSTIC COMPLETE: ${passed}/${testCases.length} TASKS PASSED ===`, "success");
}

function initWebSocket() {
    try {
        socket = new WebSocket(WS_URL);

        socket.onopen = () => {
            addLog("[WEBSOCKET] Telemetry channel connected.", "success");
        };

        socket.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            handleTelemetryEvent(msg);
        };

        socket.onclose = () => {
            setTimeout(initWebSocket, 3000);
        };
    } catch (e) {
        console.warn("WebSocket init failed:", e);
    }
}

function handleTelemetryEvent(payload) {
    const { event, data } = payload;
    if (event === "node_transition") {
        addLog(`[LANGGRAPH] Node: ${data.node}`, "system");
        highlightPipelineNode(data.node);
    } else if (event === "agent_action") {
        addLog(`[STEP ${data.step}] ${data.thought} -> ${data.action}`, "system");
    } else if (event === "approval_required") {
        showApprovalModal(data.prompt, data.token);
    } else if (event === "task_completed") {
        addLog(`[TASK COMPLETED] All steps verified.`, "success");
        setRunningState(false);
    }
}

function handleAgentResponse(data) {
    setRunningState(false);
    addLog(`[AGENT] ${data.response}`, "success");
    speakAgentResponse(data.response);

    if (data.tool_executed) {
        document.getElementById("executor-output").innerText = `Executed: ${data.tool_executed}`;
        document.getElementById("verifier-output").innerText = `Status: ${data.status.toUpperCase()}`;
        const badge = document.getElementById("last-tool-badge");
        if (badge) badge.innerText = `Last Tool: ${data.tool_executed}`;
        addLog(`[TOOL EXECUTION] Tool: ${data.tool_executed}`, "system");
    }

    if (data.requires_approval) {
        showApprovalModal(data.approval_prompt, data.approval_token);
    }
}

function highlightPipelineNode(node) {
    document.querySelectorAll(".pipeline-card").forEach(c => c.style.borderColor = "#334155");
    if (node === "planner") {
        const card = document.getElementById("card-planner");
        card.style.borderColor = "#38bdf8";
        document.getElementById("planner-output").innerText = "Generating atomic execution plan...";
    } else if (node === "executor") {
        const card = document.getElementById("card-executor");
        card.style.borderColor = "#f59e0b";
        document.getElementById("executor-output").innerText = "Invoking desktop tools...";
    } else if (node === "verifier") {
        const card = document.getElementById("card-verifier");
        card.style.borderColor = "#22c55e";
        document.getElementById("verifier-output").innerText = "Validating execution result...";
    }
}

function setRunningState(isRunning) {
    const btn = document.getElementById("run-btn");
    if (!btn) return;
    btn.disabled = isRunning;
    btn.querySelector("span").innerText = isRunning ? "Executing..." : "Execute Goal";
}

function showApprovalModal(promptText, token) {
    activeToken = token;
    document.getElementById("approval-prompt-text").innerText = promptText;
    document.getElementById("approval-token-code").innerText = token;
    document.getElementById("approval-modal").classList.remove("hidden");
    addLog(`[HUMAN-IN-THE-LOOP] Approval requested: ${promptText}`, "warning");
}

async function resolveApproval(isApproved) {
    document.getElementById("approval-modal").classList.add("hidden");
    if (!activeToken) return;

    addLog(`[USER DECISION] ${isApproved ? "Approved" : "Rejected"} action.`, isApproved ? "success" : "warning");

    try {
        const res = await fetch(`${API_BASE}/chat/approve`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ token: activeToken, approved: isApproved })
        });
        const data = await res.json();
        addLog(`[AGENT] ${data.response}`, "system");
    } catch (e) {
        addLog(`[ERROR] Approval submission failed: ${e.message}`, "error");
    }
    activeToken = null;
}

async function testHealth() {
    const backendDot = document.getElementById("backend-dot");
    const backendText = document.getElementById("backend-status-text");
    const ollamaDot = document.getElementById("ollama-dot");
    const ollamaText = document.getElementById("ollama-status-text");

    try {
        const res = await fetch(`${API_BASE}/health`);
        const data = await res.json();

        backendDot.className = "dot dot-green";
        backendText.innerText = "FastAPI Backend: Online";

        if (data.ollama && data.ollama.ready) {
            ollamaDot.className = "dot dot-green";
            ollamaText.innerText = "Llama 3.1 8B: Ready";
        } else {
            ollamaDot.className = "dot dot-green";
            ollamaText.innerText = "AI Engine: Semantic Active";
        }
    } catch (e) {
        backendDot.className = "dot dot-red";
        backendText.innerText = "FastAPI Backend: Offline";
    }
}

function addLog(text, type = "normal") {
    const body = document.getElementById("terminal-body");
    const line = document.createElement("div");
    line.className = `log-line ${type}`;
    line.innerText = `[${new Date().toLocaleTimeString()}] ${text}`;
    body.appendChild(line);
    body.scrollTop = body.scrollHeight;
}

function clearLogs() {
    const body = document.getElementById("terminal-body");
    body.innerHTML = '<div class="log-line system">[SYSTEM] Terminal logs cleared.</div>';
}

function openDocs() {
    window.open("http://127.0.0.1:8000/docs", "_blank");
}
