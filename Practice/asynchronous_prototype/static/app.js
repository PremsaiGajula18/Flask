/**
 * ============================================================================
 * Tea Shop Simulator - Sync vs Async Concept Prototype
 * ============================================================================
 * 
 * 🎓 EDUCATIONAL CORE CONCEPTS:
 * 
 * 1. THE JAVASCRIPT EVENT LOOP:
 *    - JavaScript is single-threaded; it has only ONE Call Stack.
 *    - In SYNCHRONOUS code: If a function performs a heavy or blocking task
 *      (like our while-loop below), it stays on the Call Stack. The browser
 *      CANNOT handle user input (typing), cannot repaint animations, and cannot
 *      accept new orders until the stack is completely empty.
 * 
 * 2. ASYNCHRONOUS (NON-BLOCKING) EXECUTION:
 *    - In ASYNCHRONOUS code (e.g. fetch(), setTimeout): The heavy waiting is
 *      delegated to the browser's Web APIs / background timer.
 *    - The Call Stack is immediately freed! The cashier can accept another order,
 *      and the user can type in real time.
 *    - When the timer finishes, its callback is queued in the Event Loop,
 *      allowing a 2-second order to finish before an earlier 5-second order.
 * ============================================================================
 */

// Global state tracking
let localOrders = [];
let localCounter = 1;

// DOM Elements
const customerNameInput = document.getElementById('customer-name');
const typingTestInput = document.getElementById('typing-test');
const typingCounter = document.getElementById('typing-counter');
const liveEcho = document.getElementById('live-echo');
const btnSync = document.getElementById('btn-sync');
const btnAsync = document.getElementById('btn-async');
const btnClear = document.getElementById('btn-clear');
const btnClearLog = document.getElementById('btn-clear-log');
const listPreparing = document.getElementById('list-preparing');
const listReady = document.getElementById('list-ready');
const countPreparing = document.getElementById('count-preparing');
const countReady = document.getElementById('count-ready');
const activityLog = document.getElementById('activity-log');
const threadStatus = document.getElementById('thread-status');
const threadMonitor = document.getElementById('thread-monitor');

// ============================================================================
// 1. Interactive Typing Responsiveness Test
// ============================================================================
typingTestInput.addEventListener('input', (e) => {
  const text = e.target.value;
  typingCounter.textContent = `${text.length} chars typed`;
  liveEcho.innerHTML = text 
    ? `Echo: <strong>${escapeHtml(text)}</strong>` 
    : `Echo: <em>(nothing typed yet)</em>`;
});

// ============================================================================
// 2. Button A: Synchronous (Blocking) Order Execution
// ============================================================================
btnSync.addEventListener('click', () => {
  handleSyncOrder();
});

function handleSyncOrder() {
  const duration = getSelectedDuration();
  const customerName = getCustomerName();
  const durationMs = duration * 1000;

  // Step 1: Create local order object
  const order = {
    id: localCounter++,
    name: customerName,
    duration: duration,
    mode: 'sync',
    status: 'Preparing',
    createdAt: getTimestamp()
  };
  localOrders.push(order);

  // Step 2: Render order in "Preparing" bucket & log
  renderOrders();
  logActivity(
    `🔴 [SYNC] Order #${order.id} for "${order.name}" (${duration}s) started. THREAD WILL FREEZE for ${duration}s!`, 
    'log-sync'
  );

  // Set thread monitor visual indicator to Blocked
  setThreadState(false);

  /**
   * ⚠️ WHY setTimeout(..., 20) HERE?
   * In browsers, DOM updates do not visually paint until the Call Stack clears.
   * If we executed the blocking while-loop instantly in this same tick, the
   * browser wouldn't even paint the "Preparing" card before locking up!
   * A tiny 20ms tick allows the browser to paint the preparing card first,
   * so the student visibly sees the red card freeze in real-time.
   */
  setTimeout(() => {
    const startTime = Date.now();
    const targetEnd = startTime + durationMs;

    // ⛔ THE BLOCKING ACTION:
    // A tight CPU busy-wait loop that holds the Call Stack hostage.
    // Notice: NO events, clicks, or keystrokes can be processed during this!
    while (Date.now() < targetEnd) {
      // Intentionally blocking the single thread
    }

    // Call stack is freed now!
    order.status = 'Ready';
    order.completedAt = getTimestamp();

    // Re-enable active thread status
    setThreadState(true);

    // Update UI and post to Flask backend
    renderOrders();
    logActivity(
      `🎉 [SYNC] Order #${order.id} for "${order.name}" is READY! (Thread unblocked after ${duration}s)`, 
      'log-done'
    );

    // Sync state with Flask API
    syncOrderWithBackend(order);
  }, 20);
}

// ============================================================================
// 3. Button B: Asynchronous (Non-Blocking) Order Execution
// ============================================================================
btnAsync.addEventListener('click', async () => {
  await handleAsyncOrder();
});

async function handleAsyncOrder() {
  const duration = getSelectedDuration();
  const customerName = getCustomerName();
  const durationMs = duration * 1000;

  // Step 1: Create order with Flask API asynchronously via fetch()
  let order = {
    id: localCounter++,
    name: customerName,
    duration: duration,
    mode: 'async',
    status: 'Preparing',
    createdAt: getTimestamp(),
    startTime: Date.now()
  };

  try {
    // Notify Flask API non-blockingly
    const response = await fetch('/api/orders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        customer_name: order.name,
        duration: order.duration,
        mode: 'async',
        status: 'Preparing'
      })
    });
    const result = await response.json();
    if (result.success && result.order) {
      order.id = result.order.id;
    }
  } catch (err) {
    console.warn("Backend fetch failed, continuing locally:", err);
  }

  localOrders.push(order);
  renderOrders();
  logActivity(
    `🟢 [ASYNC] Order #${order.id} for "${order.name}" (${duration}s) queued. Cashier is FREE!`, 
    'log-async'
  );

  /**
   * 🌟 THE NON-BLOCKING ACTION:
   * Instead of a tight while-loop, we use `setTimeout` wrapped in a Promise.
   * This hands off the timer to the browser's Web APIs.
   * The Call Stack is IMMEDIATELY released:
   * - You can type smoothly in the typing box!
   * - You can place another order immediately!
   * - A 2-second order finishes BEFORE a 20-second or 30-second order!
   */
  startProgressBar(order.id, durationMs);

  await waitAsync(durationMs);

  // Move order to Ready
  order.status = 'Ready';
  order.completedAt = getTimestamp();
  renderOrders();
  logActivity(
    `🍵 [ASYNC] Order #${order.id} for "${order.name}" is READY after ${duration}s!`, 
    'log-done'
  );

  // Notify backend order is complete
  try {
    await fetch('/api/orders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id: order.id,
        status: 'Ready'
      })
    });
  } catch (err) {
    console.warn("Could not sync complete status to backend:", err);
  }
}

// ============================================================================
// 4. Utility Functions & Render Helpers
// ============================================================================

// Helper promise for non-blocking wait
function waitAsync(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Get selected duration from radio buttons (2, 5, 20, or 30)
function getSelectedDuration() {
  const checked = document.querySelector('input[name="duration"]:checked');
  return checked ? parseInt(checked.value, 10) : 2;
}

// Get customer name or generate default
function getCustomerName() {
  const val = customerNameInput.value.trim();
  if (val) {
    // Clear input for next customer
    customerNameInput.value = '';
    return val;
  }
  const defaultNames = ['Aria', 'Leo', 'Maya', 'Kai', 'Sofia', 'Devin', 'Chloe', 'Zane'];
  return defaultNames[Math.floor(Math.random() * defaultNames.length)];
}

// Render Order Buckets
function renderOrders() {
  const preparingOrders = localOrders.filter(o => o.status === 'Preparing');
  const readyOrders = localOrders.filter(o => o.status === 'Ready');

  countPreparing.textContent = preparingOrders.length;
  countReady.textContent = readyOrders.length;

  // Render Preparing Bucket
  if (preparingOrders.length === 0) {
    listPreparing.innerHTML = `<div class="empty-state">No tea currently brewing</div>`;
  } else {
    listPreparing.innerHTML = preparingOrders.map(order => {
      const durationMs = order.duration * 1000;
      let pct = order.mode === 'sync' ? 100 : 5;
      let timerText = `Brewing: ${order.duration}s`;

      if (order.mode === 'async' && order.startTime) {
        const elapsed = Date.now() - order.startTime;
        pct = Math.min(100, Math.round((elapsed / durationMs) * 100));
        const remainingSec = Math.max(0, Math.ceil((durationMs - elapsed) / 1000));
        timerText = `⏳ ${remainingSec}s left (${pct}%)`;
      }

      return `
      <div class="order-card" id="order-card-${order.id}">
        <div class="order-top">
          <span class="order-name">#${order.id} ${escapeHtml(order.name)}</span>
          <span class="order-badge ${order.mode === 'sync' ? 'badge-mode-sync' : 'badge-mode-async'}">
            ${order.mode === 'sync' ? '🔴 SYNC' : '🟢 ASYNC'}
          </span>
        </div>
        <div class="order-meta">
          <span id="timer-${order.id}">${timerText}</span>
          <span>Started: ${order.createdAt}</span>
        </div>
        <div class="progress-bar-bg">
          <div class="progress-bar-fill" id="progress-${order.id}" style="width: ${pct}%"></div>
        </div>
      </div>
    `;
    }).join('');
  }

  // Render Ready Bucket
  if (readyOrders.length === 0) {
    listReady.innerHTML = `<div class="empty-state">No orders finished yet</div>`;
  } else {
    // Show newest ready orders at top
    listReady.innerHTML = readyOrders.slice().reverse().map(order => `
      <div class="order-card">
        <div class="order-top">
          <span class="order-name">#${order.id} ${escapeHtml(order.name)}</span>
          <span class="order-badge ${order.mode === 'sync' ? 'badge-mode-sync' : 'badge-mode-async'}">
            ${order.mode === 'sync' ? '🔴 SYNC' : '🟢 ASYNC'}
          </span>
        </div>
        <div class="order-meta">
          <span>Duration: ${order.duration}s</span>
          <span>Ready at: ${order.completedAt || order.createdAt}</span>
        </div>
      </div>
    `).join('');
  }
}

// Animate progress bar for Async orders
function startProgressBar(orderId, durationMs) {
  const startTime = Date.now();
  const interval = setInterval(() => {
    const el = document.getElementById(`progress-${orderId}`);
    const timerEl = document.getElementById(`timer-${orderId}`);
    if (!el) {
      clearInterval(interval);
      return;
    }
    const elapsed = Date.now() - startTime;
    const pct = Math.min(100, Math.round((elapsed / durationMs) * 100));
    const remainingSec = Math.max(0, Math.ceil((durationMs - elapsed) / 1000));
    el.style.width = `${pct}%`;
    if (timerEl) {
      timerEl.textContent = `⏳ ${remainingSec}s left (${pct}%)`;
    }
    if (elapsed >= durationMs) {
      clearInterval(interval);
    }
  }, 100);
}

// Log message to activity feed
function logActivity(message, cssClass = '') {
  const time = getTimestamp();
  const entry = document.createElement('div');
  entry.className = `log-entry ${cssClass}`;
  entry.innerHTML = `
    <span class="log-time">[${time}]</span>
    <span class="log-msg">${escapeHtml(message)}</span>
  `;
  // Prepend entry so newest is visible at top (or bottom with column-reverse)
  activityLog.insertBefore(entry, activityLog.firstChild);
}

// Toggle Thread Monitor visual status
function setThreadState(isActive) {
  if (isActive) {
    threadStatus.textContent = 'Active';
    threadStatus.style.color = 'var(--text-primary)';
    threadMonitor.style.borderColor = 'var(--border-color)';
    threadMonitor.style.background = 'var(--bg-subtle)';
  } else {
    threadStatus.textContent = 'BLOCKED (Frozen)';
    threadStatus.style.color = 'var(--sync-red-dark)';
    threadMonitor.style.borderColor = 'var(--sync-red)';
    threadMonitor.style.background = 'var(--sync-bg)';
  }
}

// Get clean HH:MM:SS timestamp
function getTimestamp() {
  const d = new Date();
  return d.toTimeString().split(' ')[0];
}

// Sync with backend API
async function syncOrderWithBackend(order) {
  try {
    await fetch('/api/orders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        customer_name: order.name,
        duration: order.duration,
        mode: order.mode,
        status: order.status
      })
    });
  } catch (err) {
    console.warn("Backend sync failed:", err);
  }
}

// Clear all orders
btnClear.addEventListener('click', async () => {
  localOrders = [];
  localCounter = 1;
  renderOrders();
  try {
    await fetch('/api/orders/clear', { method: 'POST' });
  } catch (err) {
    console.warn("Clear failed on backend:", err);
  }
  logActivity('🗑️ Kitchen cleared. Ready for fresh tests!', 'log-system');
});

// Clear log button
btnClearLog.addEventListener('click', () => {
  activityLog.innerHTML = `
    <div class="log-entry log-system">
      <span class="log-time">[${getTimestamp()}]</span>
      <span class="log-msg">Activity log cleared.</span>
    </div>
  `;
});

// Escape HTML for XSS safety
function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, function (m) {
    return {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    }[m];
  });
}

// Load initial orders from backend on page load
window.addEventListener('DOMContentLoaded', async () => {
  try {
    const res = await fetch('/api/orders');
    const data = await res.json();
    if (data.success && data.orders && data.orders.length > 0) {
      localOrders = data.orders.map(o => ({
        id: o.id,
        name: o.customer_name,
        duration: o.duration,
        mode: o.mode,
        status: o.status,
        createdAt: o.created_at,
        completedAt: o.completed_at
      }));
      localCounter = Math.max(...localOrders.map(o => o.id), 0) + 1;
      renderOrders();
      logActivity(`Loaded ${localOrders.length} existing order(s) from server.`, 'log-system');
    }
  } catch (err) {
    console.log("No previous server orders loaded.", err);
  }
});
