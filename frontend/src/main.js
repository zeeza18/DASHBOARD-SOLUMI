import "./style.css";
import Chart from "chart.js/auto";

const app = document.querySelector("#app");

// Store chart instances for cleanup
const chartInstances = new Map();

const examplePrompts = [
  { text: "Find compliance documents for UML from 2024", icon: "bi-shield-check" },
  { text: "Bank statements for UML from january 2025 to july 2025", icon: "bi-bank" },
  { text: "Show billing documents for UML", icon: "bi-receipt" },
  { text: "Legal and Compliance documents", icon: "bi-file-earmark-text" },
  { text: "Find all files from june 2023 to july 2025", icon: "bi-calendar-range" },
];

const state = {
  theme: localStorage.getItem("theme") || "dark",
  sidebarCollapsed: false,
  sidebarOpen: false,
  chats: [],
  activeChatId: null,
  results: [],
  meta: {
    sql: null,
    total: 0,
    returned: 0,
    source: "mock",
    error: null,
    show_all_available: false,
  },
  lastQuery: "",
  lastChatId: null,
  loading: false,
  dbConnected: false,
  // Note: droppedFiles and summaryConversationId are now stored per-chat
};

const layout = `
  <div class="background-gradient"></div>

  <div class="app-shell">
    <!-- Top Navigation Bar -->
    <header class="topbar glass">
      <!-- Mobile sidebar toggle (only visible on mobile, positioned absolute) -->
      <button class="icon-btn mobile-sidebar-toggle" id="toggleSidebarBtn" title="Toggle conversations">
        <i class="bi bi-layout-sidebar-inset"></i>
      </button>

      <div class="topbar__brand">
        <div class="brand-info">
          <h1 class="brand-title">BISMILLAH</h1>
          <span class="brand-subtitle">Search and analyze files</span>
        </div>
      </div>

      <div class="topbar__actions">
        <div class="status-indicator" id="dbStatus">
          <span class="status-dot"></span>
          <span class="status-text" id="statusText">Connecting...</span>
        </div>
        <div class="record-count" id="recordCount">
          <i class="bi bi-files"></i>
          <span>-- records</span>
        </div>
        <button class="icon-btn" id="themeToggle" title="Toggle theme">
          <i class="bi bi-moon-stars-fill" id="themeIcon"></i>
        </button>
      </div>
    </header>

    <!-- Loading Bar -->
    <div class="load-bar" id="loadBar"></div>

    <!-- Main 3-Panel Grid -->
    <div class="main-grid" id="mainGrid">

      <!-- Mobile Sidebar Backdrop -->
      <div class="sidebar-backdrop" id="sidebarBackdrop"></div>

      <!-- Left Sidebar - Chat History -->
      <aside class="sidebar glass" id="sidebar">
        <div class="sidebar__header">
          <div class="sidebar__title">
            <div>
              <h3>Conversations</h3>
            </div>
          </div>
          <div class="sidebar__actions">
            <button class="icon-btn primary" id="newChatBtn" title="New chat">
              <i class="bi bi-plus-lg"></i>
            </button>
            <button class="icon-btn" id="collapseSidebarBtn" title="Toggle sidebar">
              <i class="bi bi-layout-sidebar-inset"></i>
            </button>
            <button class="icon-btn mobile-close-btn" id="closeSidebarBtn" title="Close">
              <i class="bi bi-x-lg"></i>
            </button>
          </div>
        </div>
        <div class="chat-list" id="chatList"></div>
        <div class="sidebar__footer">
          <div class="sidebar__stats">
            <i class="bi bi-activity"></i>
            <span id="chatCount">0 conversations</span>
          </div>
        </div>
      </aside>

      <!-- Center - Chat/Query Panel -->
      <section class="conversation-pane glass">
        <div class="conversation__header">
          <i class="bi bi-stars"></i>
          <div>
            <h2>Ask Anything</h2>
            <p>Type your query in natural language</p>
          </div>
        </div>

        <div class="conversation__feed" id="messageFeed"></div>

        <div class="composer" id="composerArea">
          <!-- Drop zone for SUMMARY mode files -->
          <div class="composer__drop-zone" id="dropZone">
            <div class="drop-zone__content">
              <i class="bi bi-file-earmark-arrow-down"></i>
              <span>Drop files here for SUMMARY</span>
            </div>
          </div>
          <!-- Dropped files display -->
          <div class="composer__dropped-files" id="droppedFilesArea"></div>
          <div class="composer__input-wrapper">
            <i class="bi bi-search composer__icon"></i>
           <textarea id="messageInput" rows="1" placeholder="Ask to search and analyze"></textarea>
            <button class="send-btn" id="sendBtn" title="Send query">
              <i class="bi bi-send-fill"></i>
            </button>
          </div>
          <div class="composer__filters">
            <div class="pill-select">
              <label for="entitySelect">Entity</label>
              <select id="entitySelect">
                <option value="UML" selected>UML</option>
                <option value="MMM">MMM</option>
                <option value="">Any</option>
              </select>
            </div>
            <div class="pill-select">
              <label for="typeSelect">Type</label>
              <select id="typeSelect">
                <option value="">Type</option>
                <option value="MAILS">MAILS</option>
                <option value="DRIVE">DRIVE</option>
              </select>
            </div>
            <div class="pill-select">
              <label for="taskSelect">Task</label>
              <select id="taskSelect">
                <option value="SEARCH" selected>SEARCH</option>
                <option value="SUMMARY">SUMMARY</option>
                <option value="ANALYSE">ANALYSE</option>
                <option value="COMPLIANCE CHECK">COMPLIANCE CHECK</option>
                <option value="">Other</option>
              </select>
            </div>
          </div>
          <div class="composer__hint">
            <i class="bi bi-info-circle"></i>
            <span>Press Enter to send, Shift+Enter for new line</span>
          </div>
        </div>
      </section>

      <!-- Right - Results Panel -->
      <section class="results-pane glass" id="resultsPaneEl">
        <div class="results__header">
          <div class="results__title">
            <i class="bi bi-table"></i>
            <div>
              <h3>Search Results</h3>
              <p class="eyebrow" id="resultsSubtitle">Run a query to see results</p>
            </div>
          </div>
          <div class="results__header-actions">
            <div class="results__badges">
              <span class="badge primary" id="totalBadge">
                <i class="bi bi-collection"></i> Total: 0
              </span>
              <span class="badge" id="returnedBadge">
                <i class="bi bi-eye"></i> Showing: 0
              </span>
            </div>
            <button class="icon-btn mobile-close-btn" id="closeResultsBtn" title="Close results">
              <i class="bi bi-x-lg"></i>
            </button>
          </div>
        </div>

        <!-- SQL Preview Section -->
        <div class="sql-section collapsed" id="sqlSection">
          <div class="sql-header">
            <div class="sql-title">
              <i class="bi bi-code-square"></i>
              <span>Generated SQL</span>
              <span class="sql-badge">AI Generated</span>
            </div>
            <div class="sql-actions">
              <button class="icon-btn small" id="copySqlBtn" title="Copy SQL">
                <i class="bi bi-clipboard"></i>
              </button>
              <button class="icon-btn small" id="toggleSqlBtn" title="Toggle SQL">
                <i class="bi bi-chevron-down"></i>
              </button>
            </div>
          </div>
          <pre class="sql-code" id="sqlPreview">-- Your SQL query will appear here after searching</pre>
        </div>

        <!-- Action Buttons -->
        <div class="results__actions" id="resultsActions">
          <button class="action-btn primary" id="showAllBtn" style="display:none;">
            <i class="bi bi-arrows-fullscreen"></i>
            Show All Results
          </button>
          <button class="action-btn" id="exportBtn">
            <i class="bi bi-download"></i>
            Export CSV
          </button>
        </div>

        <!-- Results Grid -->
        <div class="results__grid" id="resultsGrid">
          <div class="empty-state">
            <div class="empty-icon">
              <i class="bi bi-inbox"></i>
            </div>
            <h4>No Results Yet</h4>
            <p>Enter a query to search documents</p>
          </div>
        </div>
      </section>
    </div>

    <!-- Mobile Results FAB (Floating Action Button) -->
    <button class="results-fab" id="resultsFab" title="View results">
      <i class="bi bi-files"></i>
      <span class="results-fab__count" id="fabCount">0</span>
    </button>
  </div>

  <!-- Record Detail Modal -->
  <div class="modal" id="recordModal">
    <div class="modal__backdrop" id="modalBackdrop"></div>
    <div class="modal__card glass">
      <div class="modal__header">
        <div class="modal__title">
          <i class="bi bi-file-earmark-text"></i>
          <div>
            <p class="eyebrow">Document Details</p>
            <h3 id="modalTitle">Document</h3>
          </div>
        </div>
        <button class="icon-btn" id="closeModalBtn" title="Close">
          <i class="bi bi-x-lg"></i>
        </button>
      </div>
      <div class="modal__body" id="modalBody"></div>
      <div class="modal__footer">
        <a class="action-btn primary" id="openFileLink" target="_blank" rel="noopener noreferrer">
          <i class="bi bi-box-arrow-up-right"></i>
          Open File
        </a>
      </div>
    </div>
  </div>

  <!-- Table View Modal -->
  <div class="table-modal" id="tableModal">
    <div class="table-modal__backdrop" id="tableModalBackdrop"></div>
    <div class="table-modal__content glass">
      <div class="table-modal__header">
        <div class="table-modal__title">
          <i class="bi bi-table"></i>
          <h3>All Results</h3>
          <span class="table-modal__count" id="tableResultCount">0 records</span>
        </div>
        <button class="icon-btn" id="closeTableModalBtn" title="Close">
          <i class="bi bi-x-lg"></i>
        </button>
      </div>
      <div class="table-modal__body" id="tableModalBody"></div>
    </div>
  </div>
`;

app.innerHTML = layout;

// Element references
const els = {
  mainGrid: document.getElementById("mainGrid"),
  themeToggle: document.getElementById("themeToggle"),
  themeIcon: document.getElementById("themeIcon"),
  toggleSidebarBtn: document.getElementById("toggleSidebarBtn"),
  sidebar: document.getElementById("sidebar"),
  sidebarBackdrop: document.getElementById("sidebarBackdrop"),
  chatList: document.getElementById("chatList"),
  chatCount: document.getElementById("chatCount"),
  newChatBtn: document.getElementById("newChatBtn"),
  collapseSidebarBtn: document.getElementById("collapseSidebarBtn"),
  closeSidebarBtn: document.getElementById("closeSidebarBtn"),
  messageFeed: document.getElementById("messageFeed"),
  messageInput: document.getElementById("messageInput"),
  sendBtn: document.getElementById("sendBtn"),
  resultsPaneEl: document.getElementById("resultsPaneEl"),
  resultsGrid: document.getElementById("resultsGrid"),
  resultsSubtitle: document.getElementById("resultsSubtitle"),
  closeResultsBtn: document.getElementById("closeResultsBtn"),
  resultsFab: document.getElementById("resultsFab"),
  fabCount: document.getElementById("fabCount"),
  sqlSection: document.getElementById("sqlSection"),
  sqlPreview: document.getElementById("sqlPreview"),
  totalBadge: document.getElementById("totalBadge"),
  returnedBadge: document.getElementById("returnedBadge"),
  showAllBtn: document.getElementById("showAllBtn"),
  toggleSqlBtn: document.getElementById("toggleSqlBtn"),
  copySqlBtn: document.getElementById("copySqlBtn"),
  exportBtn: document.getElementById("exportBtn"),
  loadBar: document.getElementById("loadBar"),
  dbStatus: document.getElementById("dbStatus"),
  statusText: document.getElementById("statusText"),
  recordCount: document.getElementById("recordCount"),
  modal: document.getElementById("recordModal"),
  modalBackdrop: document.getElementById("modalBackdrop"),
  modalBody: document.getElementById("modalBody"),
  modalTitle: document.getElementById("modalTitle"),
  closeModalBtn: document.getElementById("closeModalBtn"),
  openFileLink: document.getElementById("openFileLink"),
  resultsActions: document.getElementById("resultsActions"),
  tableModal: document.getElementById("tableModal"),
  tableModalBackdrop: document.getElementById("tableModalBackdrop"),
  tableModalBody: document.getElementById("tableModalBody"),
  tableResultCount: document.getElementById("tableResultCount"),
  closeTableModalBtn: document.getElementById("closeTableModalBtn"),
  // SUMMARY mode elements
  composerArea: document.getElementById("composerArea"),
  dropZone: document.getElementById("dropZone"),
  droppedFilesArea: document.getElementById("droppedFilesArea"),
};

// Theme Management
function applyTheme(theme) {
  state.theme = theme;
  document.body.setAttribute("data-theme", theme);
  localStorage.setItem("theme", theme);
  els.themeIcon.className = theme === "light" ? "bi bi-sun-fill" : "bi bi-moon-stars-fill";
}

function toggleTheme() {
  applyTheme(state.theme === "light" ? "dark" : "light");
}

// Chat Management
function createChat(title = "New chat") {
  const id = `chat-${Date.now()}`;
  return {
    id,
    title,
    messages: [],
    droppedFiles: [],  // Per-chat dropped files for SUMMARY mode
    summaryConversationId: null,  // Per-chat conversation ID
    // Per-chat results
    results: [],
    meta: {
      sql: null,
      total: 0,
      returned: 0,
      source: "mock",
      error: null,
      show_all_available: false,
    },
  };
}

function normalizeTitle(title) {
  return (title || "").toLowerCase().replace(/[^a-z0-9]+/g, "").trim();
}

function findChatByTitle(title) {
  if (!title) return null;
  const key = normalizeTitle(title);
  const match = state.chats.find((c) => {
    const t = normalizeTitle(c.title);
    return t === key || t.includes(key) || key.includes(t);
  }) || null;
  return match;
}

function dedupeChats(chats) {
  const seen = new Map();
  const result = [];

  chats.forEach((chat) => {
    const key = (chat.title || "").trim().toLowerCase();
    if (!seen.has(key)) {
      // clone to avoid shared refs
      const normalized = {
        id: chat.id || `chat-${Date.now()}-${Math.random()}`,
        title: chat.title || "New chat",
        messages: Array.isArray(chat.messages) ? [...chat.messages] : [],
      };
      seen.set(key, normalized);
      result.push(normalized);
    } else {
      const existing = seen.get(key);
      if (Array.isArray(chat.messages) && chat.messages.length) {
        existing.messages = [...existing.messages, ...chat.messages];
      }
    }
  });

  return result;
}

async function loadChatsFromServer() {
  try {
    const res = await fetch("/chats");
    if (!res.ok) throw new Error(`Server returned ${res.status}`);

    const text = await res.text();
    if (!text || text.trim() === "") {
      console.log("No chats data from server");
      return;
    }

    let data;
    try {
      data = JSON.parse(text);
    } catch (e) {
      console.error("Failed to parse chats JSON:", e, text.substring(0, 200));
      return;
    }

    if (Array.isArray(data.chats) && data.chats.length) {
      // Ensure each chat has required properties
      const validChats = data.chats.map(chat => ({
        id: chat.id,
        title: chat.title || "New chat",
        messages: Array.isArray(chat.messages) ? chat.messages : [],
        droppedFiles: Array.isArray(chat.droppedFiles) ? chat.droppedFiles : [],
        summaryConversationId: chat.summaryConversationId || null,
        analyseConversationId: chat.analyseConversationId || null,
        results: [],  // Don't load results from server
        meta: { sql: null, total: 0, returned: 0, source: "mock", error: null, show_all_available: false },
      }));

      const deduped = dedupeChats(validChats);
      state.chats = deduped;
      state.activeChatId = state.chats[0]?.id || null;
    }
  } catch (err) {
    console.error("loadChatsFromServer error:", err);
  }
}

function persistChats() {
  // Strip out results/meta before saving (they're large and transient)
  const chatsToSave = state.chats.map((chat) => ({
    id: chat.id,
    title: chat.title,
    messages: chat.messages,
    droppedFiles: chat.droppedFiles || [],
    summaryConversationId: chat.summaryConversationId || null,
    analyseConversationId: chat.analyseConversationId || null,
    // Don't persist results/meta - they're in-memory only
  }));

  fetch("/save-chats", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chats: chatsToSave }),
  }).catch(() => {});
}

function setActiveChat(chatId) {
  state.activeChatId = chatId;
  state.lastChatId = chatId;
  renderChats();
  renderMessages();
  renderDroppedFiles();  // Update dropped files display for this chat
  renderResults();  // Update results display for this chat
}

function renderChats() {
  els.chatList.innerHTML = "";

  if (state.chats.length === 0) {
    els.chatList.innerHTML = `
      <div class="chat-empty">
        <i class="bi bi-chat-square-dots"></i>
        <p>No conversations yet</p>
      </div>
    `;
    els.chatCount.textContent = "0 conversations";
    return;
  }

  state.chats.forEach((chat) => {
    const item = document.createElement("div");
    item.className = `chat-item ${chat.id === state.activeChatId ? "is-active" : ""}`;
    item.dataset.chatId = chat.id;
    item.innerHTML = `
      <div class="chat-item__icon">
        <i class="bi bi-chat-text"></i>
      </div>
      <div class="chat-item__content">
        <span class="chat-item__title">${escapeHtml(chat.title)}</span>
        <span class="chat-item__meta">
          <i class="bi bi-chat-dots"></i> ${chat.messages.length} messages
        </span>
      </div>
      <button class="chat-item__delete" data-delete="${chat.id}" title="Delete">
        <i class="bi bi-trash3"></i>
      </button>
    `;
    els.chatList.appendChild(item);
  });

  els.chatCount.textContent = `${state.chats.length} conversation${state.chats.length !== 1 ? 's' : ''}`;
}

function renderMessages() {
  const chat = state.chats.find((c) => c.id === state.activeChatId);
  if (!chat) return;

  els.messageFeed.innerHTML = "";

  if (!chat.messages.length) {
    const empty = document.createElement("div");
    empty.className = "example-prompts";
    empty.innerHTML = `
      <div class="prompts-header">
        <i class="bi bi-lightbulb"></i>
        <h4>Try one of these examples</h4>
      </div>
      <div class="prompts-grid">
        ${examplePrompts.map((p) => `
          <button class="prompt-chip" data-prompt="${escapeHtml(p.text)}">
            <i class="bi ${p.icon}"></i>
            <span>${escapeHtml(p.text)}</span>
          </button>
        `).join("")}
      </div>
    `;
    els.messageFeed.appendChild(empty);

    empty.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-prompt]");
      if (!btn) return;
      els.messageInput.value = btn.dataset.prompt;
      els.messageInput.focus();
      autoResizeTextarea();
    });
    return;
  }

  chat.messages.forEach((msg, msgIndex) => {
    const bubble = document.createElement("div");
    bubble.className = `message message--${msg.role}`;
    bubble.innerHTML = `
      <div class="message__avatar">
        <i class="bi ${msg.role === "user" ? "bi-person-fill" : "bi-robot"}"></i>
      </div>
      <div class="message__content">
        <div class="message__header">
          <span class="message__role">${msg.role === "user" ? "You" : "Assistant"}</span>
        </div>
        <div class="message__text">${formatContent(msg.content)}</div>
        ${msg.sql ? `
          <div class="message__sql">
            <div class="message__sql-header">
              <i class="bi bi-code-square"></i>
              <span>SQL Query</span>
              <div class="message__sql-actions">
                <button class="sql-action-btn" data-sql-run="${msgIndex}" title="Re-run this query">
                  <i class="bi bi-play-fill"></i>
                </button>
                <button class="sql-action-btn" data-sql-copy="${msgIndex}" title="Copy SQL">
                  <i class="bi bi-clipboard"></i>
                </button>
              </div>
            </div>
            <pre>${escapeHtml(msg.sql)}</pre>
          </div>
        ` : ""}
        ${msg.analysis ? `<div class="message__analysis" id="analysis-${msgIndex}"></div>` : ""}
      </div>
    `;
    els.messageFeed.appendChild(bubble);

    // Render analysis charts if present
    if (msg.analysis) {
      renderAnalysisCharts(`analysis-${msgIndex}`, msg.analysis);
    }
  });

  // Add click handlers for SQL action buttons
  els.messageFeed.querySelectorAll("[data-sql-run]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const msgIdx = parseInt(btn.dataset.sqlRun, 10);
      const msg = chat.messages[msgIdx];
      if (msg?.sql) {
        rerunSqlQuery(msg.sql);
      }
    });
  });

  els.messageFeed.querySelectorAll("[data-sql-copy]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const msgIdx = parseInt(btn.dataset.sqlCopy, 10);
      const msg = chat.messages[msgIdx];
      if (msg?.sql) {
        navigator.clipboard.writeText(msg.sql).then(() => {
          const icon = btn.querySelector("i");
          icon.className = "bi bi-check2";
          setTimeout(() => {
            icon.className = "bi bi-clipboard";
          }, 2000);
        });
      }
    });
  });

  els.messageFeed.scrollTop = els.messageFeed.scrollHeight;
}

function renderResults() {
  // Get results from active chat (per-chat results)
  const chat = state.chats.find((c) => c.id === state.activeChatId);
  const results = chat?.results || [];
  const meta = chat?.meta || {
    sql: null,
    total: 0,
    returned: 0,
    source: "mock",
    error: null,
    show_all_available: false,
  };

  // Update SQL preview
  if (meta.sql) {
    els.sqlPreview.textContent = meta.sql;
    els.sqlSection.classList.add("has-sql");
  } else {
    els.sqlPreview.textContent = "-- Your SQL query will appear here after searching";
    els.sqlSection.classList.remove("has-sql");
  }

  // Update badges
  els.totalBadge.innerHTML = `<i class="bi bi-collection"></i> Total: ${meta.total || 0}`;
  els.returnedBadge.innerHTML = `<i class="bi bi-eye"></i> Showing: ${meta.returned || 0}`;

  // Update subtitle
  if (meta.total > 0) {
    els.resultsSubtitle.textContent = `Found ${meta.total} matching documents`;
  } else if (meta.error) {
    els.resultsSubtitle.textContent = `Error: ${meta.error}`;
  } else {
    els.resultsSubtitle.textContent = "Run a query to see results";
  }

  // Show "Show All" button when there are results
  if (results.length > 0) {
    els.showAllBtn.style.display = "inline-flex";
  } else {
    els.showAllBtn.style.display = "none";
  }

  // Render results as styled cards
  els.resultsGrid.innerHTML = "";

  // Update mobile FAB count
  updateFabCount();

  if (!results.length) {
    els.resultsGrid.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">
          <i class="bi bi-inbox"></i>
        </div>
        <h4>No Results Yet</h4>
        <p>Enter a query to search documents</p>
      </div>
    `;
    return;
  }

  // Auto-open results panel on mobile when we have results
  if (isMobile() && results.length > 0) {
    openMobileResults();
  }

  // Create cards for each result
  results.forEach((record, index) => {
    const card = document.createElement("article");
    card.className = "result-card";
    card.draggable = true;  // Make draggable for SUMMARY mode
    card.dataset.recordIndex = index;  // Store index for drag data

    const fileUrl = record.filepath ? `/open-file?path=${encodeURIComponent(record.filepath)}` : '#';
    const hasFile = !!record.filepath;

    card.innerHTML = `
      <div class="result-card__drag-handle">
        <i class="bi bi-grip-vertical"></i>
      </div>
      <div class="result-card__icon">
        <i class="bi ${getFileIcon(record.filename)}"></i>
      </div>
      <div class="result-card__content">
        <h4 class="result-card__filename">${escapeHtml(record.filename || "Untitled")}</h4>
        <span class="result-card__category">${escapeHtml(record.category || "Uncategorized")}</span>
      </div>
      <div class="result-card__actions">
        <a class="result-card__action" href="${hasFile ? fileUrl : '#'}" ${hasFile ? 'target="_blank" rel="noopener noreferrer"' : ''} title="Open file" ${!hasFile ? 'class="result-card__action disabled"' : ''}>
          <i class="bi bi-link-45deg"></i>
        </a>
        <button class="result-card__action info-btn" title="View details">
          <i class="bi bi-info-circle"></i>
        </button>
      </div>
    `;

    // Drag events for SUMMARY mode
    card.addEventListener("dragstart", (e) => {
      e.dataTransfer.setData("application/json", JSON.stringify(record));
      e.dataTransfer.effectAllowed = "copy";
      card.classList.add("dragging");
    });

    card.addEventListener("dragend", () => {
      card.classList.remove("dragging");
    });

    // Link click - prevent if no file
    const linkBtn = card.querySelector('a.result-card__action');
    if (!hasFile) {
      linkBtn.addEventListener('click', (e) => e.preventDefault());
    }

    // Info button opens modal
    card.querySelector('.info-btn').addEventListener('click', () => {
      openRecordModal(record);
    });

    els.resultsGrid.appendChild(card);
  });
}

function getFileIcon(filename) {
  if (!filename) return "bi-file-earmark";
  const ext = filename.split('.').pop()?.toLowerCase();
  const icons = {
    pdf: "bi-file-earmark-pdf",
    doc: "bi-file-earmark-word",
    docx: "bi-file-earmark-word",
    xls: "bi-file-earmark-excel",
    xlsx: "bi-file-earmark-excel",
    csv: "bi-file-earmark-spreadsheet",
    txt: "bi-file-earmark-text",
    jpg: "bi-file-earmark-image",
    jpeg: "bi-file-earmark-image",
    png: "bi-file-earmark-image",
  };
  return icons[ext] || "bi-file-earmark";
}

// ============================================
// SUMMARY MODE: Drag-and-Drop & File Handling
// ============================================

// Get the active chat's dropped files
function getActiveDroppedFiles() {
  const chat = state.chats.find((c) => c.id === state.activeChatId);
  if (!chat) return [];
  // Ensure droppedFiles array exists (for older chats)
  if (!chat.droppedFiles) chat.droppedFiles = [];
  return chat.droppedFiles;
}

// Get the active chat's summary conversation ID
function getActiveSummaryConversationId() {
  const chat = state.chats.find((c) => c.id === state.activeChatId);
  return chat?.summaryConversationId || null;
}

// Set the active chat's summary conversation ID
function setActiveSummaryConversationId(convId) {
  const chat = state.chats.find((c) => c.id === state.activeChatId);
  if (chat) {
    chat.summaryConversationId = convId;
    persistChats();
  }
}

function renderDroppedFiles() {
  const droppedFiles = getActiveDroppedFiles();

  if (!droppedFiles.length) {
    els.droppedFilesArea.innerHTML = "";
    els.droppedFilesArea.classList.remove("has-files");
    return;
  }

  els.droppedFilesArea.classList.add("has-files");
  els.droppedFilesArea.innerHTML = droppedFiles.map((file, idx) => `
    <div class="file-chip" data-index="${idx}">
      <i class="bi ${getFileIcon(file.filename)}"></i>
      <span class="file-chip__name">${escapeHtml(file.filename || "Document")}</span>
      <button class="file-chip__remove" data-remove="${idx}" title="Remove file">
        <i class="bi bi-x"></i>
      </button>
    </div>
  `).join("");

  // Add remove handlers
  els.droppedFilesArea.querySelectorAll("[data-remove]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const idx = parseInt(btn.dataset.remove, 10);
      removeDroppedFile(idx);
    });
  });
}

function addDroppedFile(record) {
  const chat = state.chats.find((c) => c.id === state.activeChatId);
  if (!chat) return false;

  // Ensure droppedFiles array exists
  if (!chat.droppedFiles) chat.droppedFiles = [];

  // Check if file already added (by filename)
  const exists = chat.droppedFiles.some((f) => f.filename === record.filename);
  if (exists) return false;

  chat.droppedFiles.push(record);
  // Reset conversation when files change
  chat.summaryConversationId = null;
  chat.analyseConversationId = null;
  persistChats();
  renderDroppedFiles();
  return true;
}

function removeDroppedFile(index) {
  const chat = state.chats.find((c) => c.id === state.activeChatId);
  if (!chat || !chat.droppedFiles) return;

  chat.droppedFiles.splice(index, 1);
  // Reset conversation when files change
  chat.summaryConversationId = null;
  chat.analyseConversationId = null;
  persistChats();
  renderDroppedFiles();
}

function clearDroppedFiles() {
  const chat = state.chats.find((c) => c.id === state.activeChatId);
  if (!chat) return;

  chat.droppedFiles = [];
  chat.summaryConversationId = null;
  chat.analyseConversationId = null;
  persistChats();
  renderDroppedFiles();
}

function setupDropZone() {
  const composer = els.composerArea;
  const dropZone = els.dropZone;

  // Prevent default drag behaviors on whole document
  ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
    document.body.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
    }, false);
  });

  // Highlight drop zone when dragging over composer
  composer.addEventListener("dragenter", (e) => {
    e.preventDefault();
    composer.classList.add("dragover");
    dropZone.classList.add("active");
  });

  composer.addEventListener("dragover", (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
  });

  composer.addEventListener("dragleave", (e) => {
    // Only remove highlight if leaving the composer entirely
    if (!composer.contains(e.relatedTarget)) {
      composer.classList.remove("dragover");
      dropZone.classList.remove("active");
    }
  });

  composer.addEventListener("drop", (e) => {
    e.preventDefault();
    composer.classList.remove("dragover");
    dropZone.classList.remove("active");

    try {
      const data = e.dataTransfer.getData("application/json");
      if (data) {
        const record = JSON.parse(data);
        if (addDroppedFile(record)) {
          // Auto-switch to SUMMARY mode when file is dropped
          const taskSelect = document.getElementById("taskSelect");
          if (taskSelect && taskSelect.value !== "SUMMARY") {
            taskSelect.value = "SUMMARY";
          }
        }
      }
    } catch (err) {
      // Not valid JSON data, ignore
    }
  });
}

// Run SUMMARY mode query with dropped files
async function runSummaryQuery(message, targetChatId) {
  const chat = state.chats.find((c) => c.id === targetChatId);
  const droppedFiles = chat?.droppedFiles || [];

  if (!droppedFiles.length) {
    alert("Please drop files from the search results to use SUMMARY mode.");
    return;
  }

  state.loading = true;
  els.loadBar.classList.add("is-active");
  els.sendBtn.disabled = true;

  try {
    const res = await fetch("/summary-chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        files: droppedFiles.map((f) => ({
          filename: f.filename,
          description: f.description || "",
          category: f.category || "",
          filepath: f.filepath || "",
        })),
        message: message,
        conversation_id: chat?.summaryConversationId || "",
      }),
    });

    if (!res.ok) {
      throw new Error(`Server returned ${res.status}`);
    }

    const data = await res.json();

    if (data.success) {
      // Store conversation ID for follow-up questions (per-chat)
      if (chat) {
        chat.summaryConversationId = data.conversation_id;
        persistChats();
      }

      // Add assistant message to chat
      addMessageToChat(targetChatId, {
        role: "assistant",
        content: data.response,
        sql: null,  // No SQL for SUMMARY mode
      });
    } else {
      throw new Error(data.error || "Unknown error");
    }

  } catch (error) {
    addMessageToChat(targetChatId, {
      role: "assistant",
      content: `Error: ${error.message}`,
      sql: null,
    });
  } finally {
    state.loading = false;
    els.loadBar.classList.remove("is-active");
    els.sendBtn.disabled = false;
    renderMessages();
  }
}

// Run ANALYSE mode query with dropped files - generates visualizations
async function runAnalyseQuery(message, targetChatId) {
  const chat = state.chats.find((c) => c.id === targetChatId);
  const droppedFiles = chat?.droppedFiles || [];

  if (!droppedFiles.length) {
    alert("Please drop files from the search results to use ANALYSE mode.");
    return;
  }

  state.loading = true;
  els.loadBar.classList.add("is-active");
  els.sendBtn.disabled = true;

  try {
    const res = await fetch("/analyse-chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        files: droppedFiles.map((f) => ({
          filename: f.filename,
          description: f.description || "",
          category: f.category || "",
          filepath: f.filepath || "",
        })),
        message: message,
        conversation_id: chat?.analyseConversationId || "",
      }),
    });

    if (!res.ok) {
      throw new Error(`Server returned ${res.status}`);
    }

    const data = await res.json();

    if (data.success) {
      // Store conversation ID for follow-up questions
      if (chat) {
        chat.analyseConversationId = data.conversation_id;
        persistChats();
      }

      // Add assistant message with analysis data
      addMessageToChat(targetChatId, {
        role: "assistant",
        content: data.analysis.analysis_text || "Analysis complete.",
        sql: null,
        analysis: data.analysis,  // Store full analysis data for chart rendering
      });
    } else {
      throw new Error(data.error || "Unknown error");
    }

  } catch (error) {
    addMessageToChat(targetChatId, {
      role: "assistant",
      content: `Error: ${error.message}`,
      sql: null,
    });
  } finally {
    state.loading = false;
    els.loadBar.classList.remove("is-active");
    els.sendBtn.disabled = false;
    renderMessages();
  }
}

// Render analysis charts using Chart.js
function renderAnalysisCharts(containerId, analysis) {
  const container = document.getElementById(containerId);
  if (!container || !analysis) return;

  // Render key findings
  if (analysis.key_findings?.length) {
    const findingsHtml = `
      <div class="analysis__findings">
        <h4><i class="bi bi-lightbulb"></i> Key Findings</h4>
        <ul>
          ${analysis.key_findings.map(f => `<li>${escapeHtml(f)}</li>`).join('')}
        </ul>
      </div>
    `;
    container.insertAdjacentHTML('beforeend', findingsHtml);
  }

  // Render charts
  if (analysis.charts?.length) {
    analysis.charts.forEach((chartConfig, idx) => {
      const chartWrapper = document.createElement('div');
      chartWrapper.className = 'analysis__chart';
      chartWrapper.innerHTML = `
        <h4>${escapeHtml(chartConfig.title || `Chart ${idx + 1}`)}</h4>
        <div class="chart-container">
          <canvas id="${containerId}-chart-${idx}"></canvas>
        </div>
      `;
      container.appendChild(chartWrapper);

      // Create the chart
      const canvas = document.getElementById(`${containerId}-chart-${idx}`);
      if (canvas) {
        // Destroy existing chart if any
        const existingChart = chartInstances.get(canvas.id);
        if (existingChart) {
          existingChart.destroy();
        }

        const newChart = new Chart(canvas, {
          type: chartConfig.type || 'bar',
          data: {
            labels: chartConfig.labels || [],
            datasets: (chartConfig.datasets || []).map(ds => ({
              ...ds,
              borderWidth: ds.borderWidth || 1,
              borderColor: ds.borderColor || ds.backgroundColor,
            }))
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                labels: { color: '#9ca3af' }
              },
              title: {
                display: false
              }
            },
            scales: chartConfig.type !== 'pie' && chartConfig.type !== 'doughnut' ? {
              x: {
                ticks: { color: '#9ca3af' },
                grid: { color: 'rgba(255,255,255,0.1)' }
              },
              y: {
                ticks: { color: '#9ca3af' },
                grid: { color: 'rgba(255,255,255,0.1)' }
              }
            } : undefined
          }
        });

        chartInstances.set(canvas.id, newChart);
      }
    });
  }

  // Render tables
  if (analysis.tables?.length) {
    analysis.tables.forEach((tableConfig, idx) => {
      const tableWrapper = document.createElement('div');
      tableWrapper.className = 'analysis__table';
      tableWrapper.innerHTML = `
        <h4>${escapeHtml(tableConfig.title || `Table ${idx + 1}`)}</h4>
        <div class="table-container">
          <table>
            <thead>
              <tr>
                ${(tableConfig.headers || []).map(h => `<th>${escapeHtml(h)}</th>`).join('')}
              </tr>
            </thead>
            <tbody>
              ${(tableConfig.rows || []).map(row => `
                <tr>
                  ${row.map(cell => `<td>${escapeHtml(String(cell))}</td>`).join('')}
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;
      container.appendChild(tableWrapper);
    });
  }
}

// Utility functions
function escapeHtml(input) {
  const div = document.createElement("div");
  div.textContent = input ?? "";
  return div.innerHTML;
}

// Universal Markdown Renderer
function renderMarkdown(text) {
  if (!text) return "";

  let html = escapeHtml(text);

  // Code blocks (```) - must be before inline code
  html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (match, lang, code) => {
    return `<pre class="md-code-block"><code>${code.trim()}</code></pre>`;
  });

  // Inline code (`)
  html = html.replace(/`([^`]+)`/g, '<code class="md-inline-code">$1</code>');

  // Headers (### ## #)
  html = html.replace(/^### (.+)$/gm, '<h4 class="md-h3">$1</h4>');
  html = html.replace(/^## (.+)$/gm, '<h3 class="md-h2">$1</h3>');
  html = html.replace(/^# (.+)$/gm, '<h2 class="md-h1">$1</h2>');

  // Bold (**text** or __text__)
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/__([^_]+)__/g, '<strong>$1</strong>');

  // Italic (*text* or _text_)
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  html = html.replace(/_([^_]+)_/g, '<em>$1</em>');

  // Strikethrough (~~text~~)
  html = html.replace(/~~([^~]+)~~/g, '<del>$1</del>');

  // Horizontal rule (--- or ***)
  html = html.replace(/^(-{3,}|\*{3,})$/gm, '<hr class="md-hr">');

  // Unordered lists (- item or * item)
  html = html.replace(/^[\-\*] (.+)$/gm, '<li class="md-li">$1</li>');
  html = html.replace(/(<li class="md-li">.*<\/li>\n?)+/g, '<ul class="md-ul">$&</ul>');

  // Ordered lists (1. item)
  html = html.replace(/^\d+\. (.+)$/gm, '<li class="md-li-ordered">$1</li>');
  html = html.replace(/(<li class="md-li-ordered">.*<\/li>\n?)+/g, '<ol class="md-ol">$&</ol>');

  // Blockquotes (> text)
  html = html.replace(/^&gt; (.+)$/gm, '<blockquote class="md-blockquote">$1</blockquote>');

  // Links [text](url)
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener" class="md-link">$1</a>');

  // Line breaks
  html = html.replace(/\n/g, '<br>');

  // Clean up extra <br> after block elements
  html = html.replace(/<\/(h[234]|pre|ul|ol|blockquote|hr)><br>/g, '</$1>');
  html = html.replace(/<br><(h[234]|pre|ul|ol|blockquote|hr)/g, '<$1');

  return html;
}

function formatContent(input) {
  return renderMarkdown(input || "");
}

function addMessageToChat(chatId, message) {
  const chat = state.chats.find((c) => c.id === chatId);
  if (!chat) return;
  chat.messages.push(message);

  // Update chat title from first user message
  if (chat.title === "New chat" && message.role === "user" && message.content) {
    const snippet = message.content.trim();
    if (snippet) {
      chat.title = snippet.length > 35 ? snippet.slice(0, 35).trimEnd() + "..." : snippet;
      renderChats();
    }
  }

  persistChats();
}

// Auto-resize textarea
function autoResizeTextarea() {
  const textarea = els.messageInput;
  textarea.style.height = "auto";
  textarea.style.height = Math.min(textarea.scrollHeight, 150) + "px";
}

// Re-run a specific SQL query from chat history
async function rerunSqlQuery(sql) {
  if (!sql) return;

  const chat = state.chats.find((c) => c.id === state.activeChatId);
  if (!chat) return;

  // Ensure chat has results/meta arrays
  if (!chat.results) chat.results = [];
  if (!chat.meta) chat.meta = { sql: null, total: 0, returned: 0, source: "mock", error: null, show_all_available: false };

  state.loading = true;
  els.loadBar.classList.add("is-active");

  try {
    const res = await fetch("/run-sql", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sql }),
    });

    if (!res.ok) {
      throw new Error(`Server returned ${res.status}`);
    }

    const data = await res.json();
    const results = data.results || [];

    const totalCount = data.total_count ?? results.length;
    const returnedCount = data.returned_count ?? results.length;

    // Store in active chat (per-chat)
    chat.results = results;
    chat.meta = {
      sql: sql,
      total: totalCount,
      returned: returnedCount,
      source: "db",
      error: null,
      show_all_available: totalCount > returnedCount,
    };
    persistChats();

  } catch (error) {
    chat.results = [];
    chat.meta = {
      sql: sql,
      total: 0,
      returned: 0,
      source: "error",
      error: error.message,
      show_all_available: false,
    };
    persistChats();
  } finally {
    state.loading = false;
    els.loadBar.classList.remove("is-active");
    renderResults();
  }
}

// API calls
async function runQuery(text, showAll = false, targetChatId = null) {
  if (!text) return;

  state.loading = true;
  state.lastQuery = text;
  const chatId = targetChatId || state.lastChatId || state.activeChatId;
  const chat = state.chats.find((c) => c.id === chatId);

  // Ensure chat has results/meta arrays (for older chats)
  if (chat && !chat.results) chat.results = [];
  if (chat && !chat.meta) chat.meta = { sql: null, total: 0, returned: 0, source: "mock", error: null, show_all_available: false };

  els.loadBar.classList.add("is-active");
  els.sendBtn.disabled = true;
  els.showAllBtn.disabled = true;

  try {
    const res = await fetch("/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: text,
        show_all: showAll,
        chat_id: chatId,
      }),
    });

    if (!res.ok) {
      throw new Error(`Server returned ${res.status}`);
    }

    // Get response text first to handle empty/invalid JSON
    const responseText = await res.text();
    if (!responseText || responseText.trim() === "") {
      throw new Error("Empty response from server");
    }

    let data;
    try {
      data = JSON.parse(responseText);
    } catch (parseError) {
      throw new Error(`Invalid JSON: ${responseText.substring(0, 100)}`);
    }

    const results = data.results || [];

    // Normalize meta from either backend format
    const meta = data.meta || {};
    const totalCount = meta.total ?? data.total_count ?? results.length;
    const returnedCount = meta.returned ?? data.returned_count ?? results.length;

    // Store results in chat (per-chat)
    if (chat) {
      chat.results = results;
      chat.meta = {
        sql: meta.sql || data.sql || null,
        total: totalCount,
        returned: returnedCount,
        source: meta.source || (data.sql ? "db" : "mock"),
        error: meta.error || null,
        show_all_available: meta.show_all_available || (totalCount > returnedCount),
      };
      persistChats();
    }

    // Add assistant message if present
    if (data.messages?.length) {
      const assistant = data.messages.find((m) => m.role === "assistant");
      if (assistant) {
        addMessageToChat(chatId, {
          role: "assistant",
          content: assistant.content,
          sql: assistant.sql || data.sql,
        });
      }
    } else if (data.sql) {
      // Fallback: create assistant message from SQL
      addMessageToChat(chatId, {
        role: "assistant",
        content: `Found ${totalCount} results.`,
        sql: data.sql,
      });
    }

  } catch (error) {
    // Store error in chat (per-chat)
    if (chat) {
      chat.results = [];
      chat.meta = {
        sql: null,
        total: 0,
        returned: 0,
        source: "error",
        error: error.message,
        show_all_available: false,
      };
      persistChats();
    }

    addMessageToChat(chatId, {
      role: "assistant",
      content: `Error: ${error.message}`,
      sql: null,
    });
  } finally {
    state.loading = false;
    els.loadBar.classList.remove("is-active");
    els.sendBtn.disabled = false;
    els.showAllBtn.disabled = false;
    renderMessages();
    renderResults();
  }
}

function sendMessage(showAll = false) {
  const text = els.messageInput.value.trim();
  let queryText = showAll ? state.lastQuery : text;
  if (!queryText) return;

  // Get task selection (SEARCH, SUMMARY, etc.)
  const task = document.getElementById("taskSelect")?.value || "SEARCH";

  if (!showAll) {
    // If a chat with this title already exists, route the message there
    const existing = findChatByTitle(queryText);
    let targetChatId = state.activeChatId;
    if (existing) {
      targetChatId = existing.id;
      if (existing.id !== state.activeChatId) {
        setActiveChat(existing.id);
      }
    } else {
      // No existing chat matched: if current chat is unnamed/new, retitle it to this query
      const current = state.chats.find((c) => c.id === targetChatId);
      if (current && normalizeTitle(current.title) === normalizeTitle("New chat")) {
        current.title = queryText.length > 35 ? queryText.slice(0, 35).trimEnd() + "..." : queryText;
        renderChats();
        persistChats();
      }
    }

    // Ensure active chat is the target so assistant replies go to the same thread
    if (state.activeChatId !== targetChatId) {
      setActiveChat(targetChatId);
    }

    addMessageToChat(targetChatId, { role: "user", content: queryText });
    renderMessages();
    els.messageInput.value = "";
    autoResizeTextarea();
    state.lastChatId = targetChatId;

    // Route based on task type
    if (task === "SUMMARY") {
      // SUMMARY mode: use dropped files and OpenAI for Q&A
      runSummaryQuery(queryText, state.lastChatId);
      return;
    }

    if (task === "ANALYSE") {
      // ANALYSE mode: use dropped files and OpenAI for visualizations
      runAnalyseQuery(queryText, state.lastChatId);
      return;
    }
  } else {
    // showAll uses last chat
    state.lastChatId = state.lastChatId || state.activeChatId;
  }

  // SEARCH mode (default): SQL query
  runQuery(queryText, showAll, state.lastChatId);
}

// Modal
function openRecordModal(record) {
  els.modalTitle.textContent = record.filename || "Document";
  els.modalBody.innerHTML = buildRecordDetail(record);

  if (record.filepath) {
    els.openFileLink.href = `/open-file?path=${encodeURIComponent(record.filepath)}`;
    els.openFileLink.classList.remove("is-disabled");
  } else {
    els.openFileLink.removeAttribute("href");
    els.openFileLink.classList.add("is-disabled");
  }

  els.modal.classList.add("is-open");
  document.body.style.overflow = "hidden";
}

function closeRecordModal() {
  els.modal.classList.remove("is-open");
  document.body.style.overflow = "";
}

function buildRecordDetail(record) {
  const fields = [
    { key: "company", label: "Company", icon: "bi-building" },
    { key: "name", label: "Name", icon: "bi-person" },
    { key: "dob", label: "Date of Birth", icon: "bi-calendar-heart" },
    { key: "date", label: "Date", icon: "bi-calendar" },
    { key: "email", label: "Email", icon: "bi-envelope" },
    { key: "category", label: "Category", icon: "bi-tag" },
    { key: "match_reason", label: "Match Reason", icon: "bi-bullseye" },
    { key: "filepath", label: "File Path", icon: "bi-folder2" },
    { key: "description", label: "Description", icon: "bi-text-paragraph" },
  ];

  return fields.map(({ key, label, icon }) => `
    <div class="detail-row ${key === 'match_reason' ? 'highlight' : ''} ${key === 'description' ? 'full-width' : ''}">
      <div class="detail-label">
        <i class="bi ${icon}"></i>
        <span>${label}</span>
      </div>
      <div class="detail-value">${escapeHtml(record[key] || "—")}</div>
    </div>
  `).join("");
}

// Export CSV
function exportToCSV() {
  if (!state.results.length) return;

  // Define column order for export
  const exportColumns = [
    { key: "filename", label: "Filename" },
    { key: "name", label: "Name" },
    { key: "date", label: "Date" },
    { key: "dob", label: "DOB" },
    { key: "email", label: "Email" },
    { key: "company", label: "Company" },
    { key: "category", label: "Category" },
    { key: "match_reason", label: "Match Reason" },
    { key: "description", label: "Description" },
    { key: "filepath", label: "File Path" },
  ];

  // Header row
  let csv = exportColumns.map(c => c.label).join(",") + "\n";

  // Data rows
  state.results.forEach((row) => {
    const values = exportColumns.map(({ key }) => {
      let val = row[key] ?? "";
      val = String(val).replace(/"/g, '""');
      if (val.includes(",") || val.includes("\n") || val.includes('"')) {
        val = `"${val}"`;
      }
      return val;
    });
    csv += values.join(",") + "\n";
  });

  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `uml_search_${Date.now()}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// Show All Results in Table View
function showAllResultsTable() {
  const rows = state.results;
  if (!rows.length) {
    alert("No results to display");
    return;
  }

  els.tableResultCount.textContent = `${rows.length} records`;

  // Build card-style rows for a cleaner, modern look
  const cardsHTML = rows
    .map((record, idx) => {
      const fileUrl = record.filepath ? `/open-file?path=${encodeURIComponent(record.filepath)}` : "#";
      const hasFile = !!record.filepath;
      const descValue = record.description ? String(record.description) : "";
      const shortDesc = descValue.length > 160 ? `${descValue.slice(0, 160)}...` : descValue;
      const reasonValue = record.match_reason ? String(record.match_reason) : "";
      const shortReason = reasonValue.length > 120 ? `${reasonValue.slice(0, 120)}...` : reasonValue;
      const category = record.category || "Uncategorized";
      const filename = record.filename || "Untitled";
      const metaParts = [
        record.company,
        record.name,
        record.email,
        record.date || record.dob,
      ].filter(Boolean);
      const detailFields = [
        { label: "DOS", value: record.date || "" },
        { label: "DOB", value: record.dob || "" },
        { label: "Email", value: record.email || "" },
        { label: "Company", value: record.company || "" },
        { label: "Name", value: record.name || "" },
      ];

      return `
        <article class="table-card">
          <div class="table-card__icon">
            <i class="bi ${getFileIcon(record.filename)}"></i>
          </div>
          <div class="table-card__content">
            <div class="table-card__title">${escapeHtml(filename)}</div>
            <div class="table-card__meta">${escapeHtml(metaParts.join(" • ") || "No metadata")}</div>
            <div class="table-card__chips">
              <span class="chip chip--category">${escapeHtml(category)}</span>
              ${shortReason ? `<span class="chip chip--reason">${escapeHtml(shortReason)}</span>` : ""}
            </div>
            <div class="table-card__details">
              ${detailFields
                .map(
                  (f) => `
                  <div class="detail-chip">
                    <span class="detail-chip__label">${escapeHtml(f.label)}</span>
                    <span class="detail-chip__value">${escapeHtml(f.value || "—")}</span>
                  </div>
                `
                )
                .join("")}
            </div>
            ${shortDesc ? `<p class="table-card__desc">${escapeHtml(shortDesc)}</p>` : ""}
          </div>
          <div class="table-card__actions">
            <a class="table-card__action ${hasFile ? "" : "disabled"}" href="${fileUrl}" ${
        hasFile ? 'target="_blank" rel="noopener noreferrer"' : ""
      } title="Open file">
              <i class="bi bi-link-45deg"></i>
            </a>
            <button class="table-card__action" data-card-info="${idx}" title="View details">
              <i class="bi bi-info-circle"></i>
            </button>
          </div>
        </article>
      `;
    })
    .join("");

  els.tableModalBody.innerHTML = `<div class="table-card-list">${cardsHTML}</div>`;

  // Add click handlers for info buttons
  els.tableModalBody.querySelectorAll("[data-card-info]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const idx = parseInt(btn.dataset.cardInfo, 10);
      openRecordModal(rows[idx]);
    });
  });

  // Show modal
  els.tableModal.classList.add("is-open");
  document.body.style.overflow = "hidden";
}

function closeTableModal() {
  els.tableModal.classList.remove("is-open");
  document.body.style.overflow = "";
}

// Copy SQL
function copySQL() {
  if (!state.meta.sql) return;
  navigator.clipboard.writeText(state.meta.sql).then(() => {
    els.copySqlBtn.innerHTML = '<i class="bi bi-check2"></i>';
    setTimeout(() => {
      els.copySqlBtn.innerHTML = '<i class="bi bi-clipboard"></i>';
    }, 2000);
  });
}

// Health check
function pingHealth() {
  fetch("/health")
    .then((res) => res.json())
    .then((data) => {
      // Handle both backend formats
      const connected = data.status === "healthy" || data?.db?.connected;
      state.dbConnected = connected;

      els.dbStatus.classList.toggle("connected", connected);
      els.dbStatus.classList.toggle("disconnected", !connected);
      els.statusText.textContent = connected ? "Connected" : "Offline";

      const count = data.total_records ?? data.total ?? 0;
      if (count) {
        els.recordCount.innerHTML = `<i class="bi bi-files"></i> <span>${count.toLocaleString()} records</span>`;
      }
    })
    .catch(() => {
      els.dbStatus.classList.add("disconnected");
      els.statusText.textContent = "Error";
    });
}

// Toggle SQL visibility
let sqlCollapsed = true;
function toggleSQL() {
  sqlCollapsed = !sqlCollapsed;
  els.sqlSection.classList.toggle("collapsed", sqlCollapsed);
  els.toggleSqlBtn.innerHTML = sqlCollapsed
    ? '<i class="bi bi-chevron-down"></i>'
    : '<i class="bi bi-chevron-up"></i>';
}

// Mobile: Check if mobile screen
function isMobile() {
  return window.innerWidth <= 1200;
}

// Mobile: Toggle sidebar (default closed)
function toggleSidebarMobile(force) {
  const shouldOpen = typeof force === "boolean" ? force : !state.sidebarOpen;
  state.sidebarOpen = shouldOpen;
  els.sidebar.classList.toggle("mobile-open", shouldOpen);
  els.sidebarBackdrop.classList.toggle("active", shouldOpen);
  document.body.style.overflow = shouldOpen ? "hidden" : "";
}

// Mobile: Close sidebar (alias for consistency)
function closeMobileSidebar() {
  toggleSidebarMobile(false);
}

// Mobile: Open results panel
function openMobileResults() {
  els.resultsPaneEl.classList.add("mobile-open");
  els.resultsFab.classList.add("hidden");
}

// Mobile: Close results panel
function closeMobileResults() {
  els.resultsPaneEl.classList.remove("mobile-open");
  // Show FAB if we have results
  if (state.results.length > 0 && isMobile()) {
    els.resultsFab.classList.remove("hidden");
  }
}

// Mobile: Update FAB count
function updateFabCount() {
  const chat = state.chats.find((c) => c.id === state.activeChatId);
  const count = chat?.meta?.total || 0;
  els.fabCount.textContent = count > 99 ? "99+" : count;
  // Show FAB on mobile when we have results and results panel is closed
  if (count > 0 && isMobile() && !els.resultsPaneEl.classList.contains("mobile-open")) {
    els.resultsFab.classList.remove("hidden");
  } else if (!isMobile()) {
    els.resultsFab.classList.add("hidden");
  }
}

// Draggable FAB functionality
function initDraggableFab() {
  const fab = els.resultsFab;
  let isDragging = false;
  let hasMoved = false;
  let startX, startY, startLeft, startTop;

  // Get initial position (convert from bottom/right to top/left)
  function getPosition() {
    const rect = fab.getBoundingClientRect();
    return { left: rect.left, top: rect.top };
  }

  function onStart(e) {
    if (fab.classList.contains("hidden")) return;

    isDragging = true;
    hasMoved = false;
    fab.classList.add("dragging");

    const touch = e.touches ? e.touches[0] : e;
    startX = touch.clientX;
    startY = touch.clientY;

    const pos = getPosition();
    startLeft = pos.left;
    startTop = pos.top;

    // Switch from bottom/right to top/left positioning
    fab.style.bottom = "auto";
    fab.style.right = "auto";
    fab.style.left = startLeft + "px";
    fab.style.top = startTop + "px";
  }

  function onMove(e) {
    if (!isDragging) return;
    e.preventDefault();

    const touch = e.touches ? e.touches[0] : e;
    const deltaX = touch.clientX - startX;
    const deltaY = touch.clientY - startY;

    // Consider it a move if dragged more than 5px
    if (Math.abs(deltaX) > 5 || Math.abs(deltaY) > 5) {
      hasMoved = true;
    }

    let newLeft = startLeft + deltaX;
    let newTop = startTop + deltaY;

    // Constrain to viewport
    const fabWidth = fab.offsetWidth;
    const fabHeight = fab.offsetHeight;
    const maxLeft = window.innerWidth - fabWidth;
    const maxTop = window.innerHeight - fabHeight;

    newLeft = Math.max(0, Math.min(newLeft, maxLeft));
    newTop = Math.max(0, Math.min(newTop, maxTop));

    fab.style.left = newLeft + "px";
    fab.style.top = newTop + "px";
  }

  function onEnd() {
    if (!isDragging) return;
    isDragging = false;
    fab.classList.remove("dragging");

    // If didn't move much, trigger click to open results
    if (!hasMoved) {
      openMobileResults();
    }
  }

  // Mouse events
  fab.addEventListener("mousedown", onStart);
  document.addEventListener("mousemove", onMove);
  document.addEventListener("mouseup", onEnd);

  // Touch events
  fab.addEventListener("touchstart", onStart, { passive: false });
  document.addEventListener("touchmove", onMove, { passive: false });
  document.addEventListener("touchend", onEnd);
}

// Initialize
function init() {
  // Load chats from server, then set up UI
  loadChatsFromServer().finally(() => {
    if (!state.chats.length) {
      const chat = createChat("New chat");
      state.chats.push(chat);
      state.activeChatId = chat.id;
    }

    applyTheme(state.theme);
    renderChats();
    renderMessages();
    renderResults();
    renderDroppedFiles();  // Initialize dropped files display
    toggleSidebarMobile(false);
    setupDropZone();  // Set up drag-and-drop for SUMMARY mode

    // Ensure SQL starts collapsed
    els.sqlSection.classList.add("collapsed");
    els.toggleSqlBtn.innerHTML = '<i class="bi bi-chevron-down"></i>';

    // Event listeners
    els.themeToggle.addEventListener("click", toggleTheme);

    els.newChatBtn.addEventListener("click", () => {
      const chat = createChat("New chat");
      state.chats.unshift(chat);
      setActiveChat(chat.id);
      persistChats();
    });

    els.collapseSidebarBtn.addEventListener("click", () => {
      state.sidebarCollapsed = !state.sidebarCollapsed;
      els.sidebar.classList.toggle("collapsed", state.sidebarCollapsed);
      els.mainGrid.classList.toggle("sidebar-collapsed", state.sidebarCollapsed);
    });

    els.chatList.addEventListener("click", (e) => {
      const deleteBtn = e.target.closest("[data-delete]");
      if (deleteBtn) {
        const chatId = deleteBtn.dataset.delete;
        state.chats = state.chats.filter((c) => c.id !== chatId);
        if (state.activeChatId === chatId) {
          if (state.chats.length) {
            state.activeChatId = state.chats[0].id;
          } else {
            const newChat = createChat("New chat");
            state.chats.push(newChat);
            state.activeChatId = newChat.id;
          }
        }
        renderChats();
        renderMessages();
        persistChats();
        return;
      }

      const item = e.target.closest("[data-chat-id]");
      if (item) setActiveChat(item.dataset.chatId);
    });

    els.sendBtn.addEventListener("click", () => sendMessage(false));
    els.showAllBtn.addEventListener("click", showAllResultsTable);
    els.toggleSqlBtn.addEventListener("click", toggleSQL);
    els.copySqlBtn.addEventListener("click", copySQL);

    // Table modal events
    els.closeTableModalBtn.addEventListener("click", closeTableModal);
    els.tableModalBackdrop.addEventListener("click", closeTableModal);
    els.exportBtn.addEventListener("click", exportToCSV);

    els.messageInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage(false);
      }
    });

    els.messageInput.addEventListener("input", autoResizeTextarea);

    els.modalBackdrop.addEventListener("click", closeRecordModal);
    els.closeModalBtn.addEventListener("click", closeRecordModal);

    // Close modal on Escape
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        closeRecordModal();
        closeMobileSidebar();
        closeMobileResults();
      }
    });

    // Mobile event listeners
    els.toggleSidebarBtn.addEventListener("click", () => toggleSidebarMobile());
    els.closeSidebarBtn.addEventListener("click", () => toggleSidebarMobile(false));
    els.sidebarBackdrop.addEventListener("click", () => toggleSidebarMobile(false));

    // Close sidebar when selecting a chat on mobile
    els.chatList.addEventListener("click", (e) => {
      if (isMobile() && e.target.closest("[data-chat-id]")) {
        toggleSidebarMobile(false);
      }
    });

    // Mobile results panel event listeners
    els.closeResultsBtn.addEventListener("click", closeMobileResults);

    // Initialize draggable FAB (handles click internally)
    initDraggableFab();

    // Hide FAB initially
    els.resultsFab.classList.add("hidden");
  });
}

init();
pingHealth();
