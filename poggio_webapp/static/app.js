/* Trench Digitization Pipeline — frontend bootstrap. */

import("./app/index.js").catch((error) => {
  console.error("Could not start frontend:", error);

  const content = document.getElementById("content");

  if (content) {
    const panel = document.createElement("div");
    panel.className = "panel";
    panel.innerHTML = `
      <div class="stage-kicker">The guide could not start</div>
      <h2>Refresh the page and try again</h2>
      <p class="lede">If this message returns, copy the technical details below
      and send them to the person who maintains this app.</p>
    `;
    const details = document.createElement("details");
    details.className = "technical-details";
    const summary = document.createElement("summary");
    summary.textContent = "Technical details";
    const pre = document.createElement("pre");
    pre.textContent =
      error && error.stack
        ? error.stack
        : String(error);
    details.appendChild(summary);
    details.appendChild(pre);
    panel.appendChild(details);
    content.replaceChildren(panel);
  }
});
