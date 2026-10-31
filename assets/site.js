// Moves the download for the visitor's device to the front.
function detectPlatform() {
  const ua = navigator.userAgent;
  if (/Android/i.test(ua)) return "android";
  if (/iPhone|iPad|iPod/i.test(ua)) return "ios";
  if (/Macintosh/i.test(ua)) return navigator.maxTouchPoints > 1 ? "ios" : "mac";
  if (/Windows/i.test(ua)) return "windows";
  return null;
}

const mine = document.querySelector(`.dl[data-platform="${detectPlatform()}"]`);
if (mine) {
  mine.classList.add("mine");
  mine.parentElement.prepend(mine);
}

// Platform filter on the home page.
const buttons = document.querySelectorAll("[data-filter]");
const rows = document.querySelectorAll(".app");
const empty = document.querySelector(".empty");

buttons.forEach((button) => {
  button.addEventListener("click", () => {
    const filter = button.dataset.filter;
    buttons.forEach((b) => b.setAttribute("aria-pressed", String(b === button)));
    let shown = 0;
    rows.forEach((row) => {
      row.hidden = filter !== "all" && !row.dataset.platforms.split(" ").includes(filter);
      if (!row.hidden) shown += 1;
    });
    empty.hidden = shown > 0;
  });
});
