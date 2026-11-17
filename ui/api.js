const TIMEOUT_MS = 45000;
const STARTING_UP =
  "Can't reach the server. If the app was idle, it is starting up, which can take up to a minute. Try again shortly.";

async function call(baseUrl, path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  let response;
  try {
    response = await fetch(baseUrl + path, {
      ...options,
      headers: options.body ? { "Content-Type": "application/json" } : {},
      body: options.body ? JSON.stringify(options.body) : undefined,
      signal: controller.signal,
    });
  } catch {
    throw new ApiError(STARTING_UP, 0);
  } finally {
    clearTimeout(timer);
  }
  const data = response.status === 204 ? {} : await response.json().catch(() => ({}));
  if (!response.ok) {
    const fallback = response.status === 503 ? STARTING_UP : "Something went wrong.";
    throw new ApiError(data.error || fallback, response.status);
  }
  return data;
}

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

const rooms = (path, options) => call(window.CONFIG.ROOMS_URL, path, options);
const battle = (path, options) => call(window.CONFIG.BATTLE_URL, path, options);

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") node.className = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value);
  }
  node.append(...children.filter((child) => child !== null && child !== undefined));
  return node;
}

function showMessage(node, message) {
  node.textContent = message || "";
  node.hidden = !message;
}
