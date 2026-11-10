const error = document.getElementById("error");
const createForm = document.getElementById("create-form");
const joinForm = document.getElementById("join-form");

document.getElementById("code").value = new URLSearchParams(location.search).get("code") || "";

function goToRoom(room, me) {
  location.href = `room.html?${new URLSearchParams({ code: room.code, me })}`;
}

async function submit(event, send) {
  event.preventDefault();
  const button = event.target.querySelector("button");
  button.disabled = true;
  showMessage(error, "");
  try {
    await send(Object.fromEntries(new FormData(event.target)));
  } catch (err) {
    showMessage(error, err.message);
  } finally {
    button.disabled = false;
  }
}

createForm.addEventListener("submit", (event) =>
  submit(event, async (form) => {
    const room = await rooms("/rooms", { method: "POST", body: form });
    goToRoom(room, form.your_name.trim());
  }),
);

joinForm.addEventListener("submit", (event) =>
  submit(event, async (form) => {
    const code = encodeURIComponent(form.code.trim());
    const room = await rooms(`/rooms/${code}/members`, { method: "POST", body: { your_name: form.your_name } });
    goToRoom(room, form.your_name.trim());
  }),
);
