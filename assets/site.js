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
