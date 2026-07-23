/* Trench Digitization Pipeline — frontend bootstrap. */

import("./app/index.js").catch((error) => {
  console.error("Could not start frontend:", error);

  const content = document.getElementById("content");

  if (content) {
    const pre = document.createElement("pre");
    pre.textContent =
      error && error.stack
        ? error.stack
        : String(error);

    content.replaceChildren(pre);
  }
});
