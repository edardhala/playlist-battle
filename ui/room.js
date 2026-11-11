const params = new URLSearchParams(location.search);
const code = (params.get("code") || "").trim().toUpperCase();
const me = params.get("me") || "";
const path = `/rooms/${encodeURIComponent(code)}`;
const $ = (id) => document.getElementById(id);

const shareLink = new URL(`index.html?${new URLSearchParams({ code })}`, location.href).href;
$("share-link").href = shareLink;
$("share-link").textContent = shareLink;
$("join-link").href = shareLink;
$("room-code").textContent = code;
$("add-card").hidden = !me;
$("join-card").hidden = Boolean(me);

let iAmHost = false;
let hasSongs = false;

function youtube(song) {
  return `https://www.youtube.com/results?search_query=${encodeURIComponent(`${song.title} ${song.artist}`)}`;
}

function updatePlayButton() {
  $("play").hidden = !(iAmHost && hasSongs);
}

async function loadRoom() {
  try {
    const room = await rooms(path);
    showMessage($("rooms-notice"), "");
    $("room-name").textContent = room.name;
    document.title = `${room.name} · Playlist Battle`;
    iAmHost = room.members.some((member) => member.name === me && member.is_host);
    $("people-title").textContent = `People (${room.members.length})`;
    $("members").replaceChildren(
      ...room.members.map((member, index) =>
        el(
          "li",
          { class: "member" },
          el("span", { class: `avatar avatar-${index % 5}`, "aria-hidden": "true" }, member.name[0].toUpperCase()),
          member.name,
          member.is_host ? el("span", { class: "tag" }, "host") : null,
          member.name === me ? el("span", { class: "tag" }, "you") : null,
        ),
      ),
    );
  } catch (err) {
    iAmHost = false;
    if (err.status === 404) {
      $("room-name").textContent = "Room not found";
    }
    showMessage($("rooms-notice"), "Can't load the people in this room right now.");
  }
  updatePlayButton();
}

function songItem(song, index, topVotes) {
  const action = !me
    ? null
    : song.voted_by_me
      ? el("button", { class: "button-ghost button-small", type: "button", onclick: () => unvote(song.id) }, "Remove vote")
      : el("button", { class: "button-small", type: "button", onclick: () => vote(song.id) }, "▲ Vote");
  return el(
    "li",
    { class: "song" },
    el("span", { class: `rank rank-${index + 1}` }, String(index + 1)),
    el(
      "div",
      {},
      el("div", { class: "song-title" }, song.title),
      el("div", { class: "song-meta" }, `${song.artist} · ${song.votes} vote${song.votes === 1 ? "" : "s"}, added by ${song.added_by}`),
      el("div", { class: "vote-bar", "aria-hidden": "true" }, el("span", { style: `width: ${topVotes ? (song.votes / topVotes) * 100 : 0}%` })),
    ),
    el(
      "div",
      { class: "song-actions" },
      el("a", { class: "button button-ghost button-small", href: youtube(song), target: "_blank", rel: "noopener", "aria-label": `Listen to ${song.title} on YouTube` }, "Listen"),
      action,
    ),
  );
}

function renderPlaylist(data) {
  hasSongs = data.songs.length > 0;
  const topVotes = Math.max(0, ...data.songs.map((song) => song.votes));
  $("playlist").replaceChildren(
    hasSongs
      ? el("ol", { class: "playlist" }, ...data.songs.map((song, index) => songItem(song, index, topVotes)))
      : el("div", { class: "empty" }, el("p", {}, "No songs yet. Add the first one!")),
  );
  const [current, ...earlier] = data.played;
  $("now-playing").replaceChildren(
    current
      ? el(
          "section",
          { class: "card now-playing" },
          el("div", { class: "equalizer", "aria-hidden": "true" }, el("span"), el("span"), el("span"), el("span")),
          el(
            "div",
            {},
            el("div", { class: "now-label" }, "Now playing"),
            el("div", { class: "song-title" }, current.title),
            el("div", { class: "song-meta" }, `${current.artist} · added by ${current.added_by}`),
          ),
          el("a", { class: "button button-small", href: youtube(current), target: "_blank", rel: "noopener" }, "▶ Listen"),
        )
      : "",
  );
  $("played-card").hidden = earlier.length === 0;
  $("played").replaceChildren(
    ...earlier.map((song) =>
      el("li", {}, el("span", { class: "song-title" }, song.title), " ", el("span", { class: "song-meta" }, `· ${song.artist}`)),
    ),
  );
}

async function loadPlaylist() {
  try {
    const data = await battle(`${path}/playlist?${new URLSearchParams({ me })}`);
    renderPlaylist(data);
    showMessage(
      $("battle-notice"),
      data.rooms_available ? "" : "You can see the playlist, but you can't add songs or vote right now.",
    );
  } catch (err) {
    showMessage($("battle-notice"), "Can't load the playlist right now.");
  }
  updatePlayButton();
}

function refresh() {
  return Promise.all([loadRoom(), loadPlaylist()]);
}

async function act(request) {
  showMessage($("error"), "");
  try {
    await request();
  } catch (err) {
    showMessage($("error"), err.message);
  }
  await loadPlaylist();
}

function vote(songId) {
  return act(() => battle(`${path}/songs/${songId}/vote`, { method: "POST", body: { me } }));
}

function unvote(songId) {
  return act(() => battle(`${path}/songs/${songId}/vote?${new URLSearchParams({ me })}`, { method: "DELETE" }));
}

$("play").addEventListener("click", () => act(() => battle(`${path}/play`, { method: "POST", body: { me } })));

$("add-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = Object.fromEntries(new FormData(event.target));
  act(async () => {
    await battle(`${path}/songs`, { method: "POST", body: { ...form, me } });
    event.target.reset();
  });
});

function isTyping() {
  const field = document.activeElement;
  return field && field.tagName === "INPUT" && field.value !== "";
}

refresh();
setInterval(() => {
  if (!document.hidden && !isTyping()) {
    refresh();
  }
}, 5000);
