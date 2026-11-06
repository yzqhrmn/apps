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

// Phones can drop an image request, and browsers then show it broken until a reload.
const retries = new WeakMap();

function retryImage(image) {
  const attempt = (retries.get(image) || 0) + 1;
  if (attempt > 4) return;
  retries.set(image, attempt);
  const url = new URL(image.src);
  url.searchParams.set("retry", attempt);
  setTimeout(() => { image.src = url.href; }, attempt * 1000);
}

document.addEventListener("error", (event) => {
  if (event.target.tagName === "IMG") retryImage(event.target);
}, true);

document.querySelectorAll("img").forEach((image) => {
  if (image.complete && image.naturalWidth === 0) retryImage(image);
});

// Screenshot collage: a thumbnail becomes the large picture.
const stageImage = document.querySelector(".stage img");
const thumbs = document.querySelectorAll(".thumbs a");

thumbs.forEach((thumb) => {
  thumb.addEventListener("click", (event) => {
    event.preventDefault();
    stageImage.src = thumb.getAttribute("href");
    stageImage.width = thumb.dataset.width;
    stageImage.height = thumb.dataset.height;
    thumbs.forEach((t) => t.removeAttribute("aria-current"));
    thumb.setAttribute("aria-current", "true");
  });
});

// Magic theme: sparkles trail the pointer.
if (document.body.classList.contains("theme-magic") && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
  const colors = ["#ffd36b", "#fff3c4", "#c9a6ff", "#ffffff"];
  let last = 0;
  document.addEventListener("pointermove", (event) => {
    const now = performance.now();
    if (now - last < 45) return;
    last = now;
    const star = document.createElement("span");
    star.className = "sparkle";
    star.textContent = Math.random() < .7 ? "✦" : "✧";
    star.style.left = `${event.clientX}px`;
    star.style.top = `${event.clientY}px`;
    star.style.setProperty("--size", `${8 + Math.random() * 12}px`);
    star.style.setProperty("--dx", `${(Math.random() - .5) * 40}px`);
    star.style.setProperty("--color", colors[Math.floor(Math.random() * colors.length)]);
    star.addEventListener("animationend", () => star.remove());
    document.body.append(star);
  }, { passive: true });
}
