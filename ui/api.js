const TIMEOUT_MS = 8000;

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
    throw new ApiError("Can't connect right now. Try again in a moment.", 0);
  } finally {
    clearTimeout(timer);
  }
  const data = response.status === 204 ? {} : await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(data.error || "Something went wrong.", response.status);
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
