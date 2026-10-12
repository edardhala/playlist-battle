const room = document.querySelector("[data-version-url]");

function isTyping() {
  const field = document.activeElement;
  return field && field.tagName === "INPUT" && field.value !== "";
}

async function checkForChanges() {
  if (document.hidden || isTyping()) {
    return;
  }
  const response = await fetch(room.dataset.versionUrl);
  if (!response.ok) {
    return;
  }
  const data = await response.json();
  if (data.version !== room.dataset.version) {
    const url = new URL(window.location.href);
    url.searchParams.delete("error");
    window.location.replace(url);
  }
}

if (room) {
  setInterval(checkForChanges, 5000);
}
