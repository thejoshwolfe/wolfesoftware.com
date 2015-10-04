document.getElementById("plainTextDownload").setAttribute("href", (function() {
  var finalText = "";
  visit(document.body);
  return "data:text/plain;charset=US-ASCII," + encodeURIComponent(finalText);

  function visit(node) {
    if (node.nodeType === Node.TEXT_NODE) {
      handleText(node.textContent);
    }
    if (node.nodeType !== Node.ELEMENT_NODE) return;
    if (node.classList.contains("no-print")) return;
    var tagName = node.tagName.toLowerCase();
    if (tagName === "li") {
      finalText += " * ";
    }
    var children = node.childNodes;
    for (var i = 0; i < children.length; i++) {
      visit(children[i]);
    }
    if (["h1", "h2", "h3", "div", "p", "li"].indexOf(tagName) !== -1) {
      if (finalText !== "" && finalText[finalText.length - 1] !== "\n") {
        finalText += "\n";
      }
    }
  }

  function handleText(text) {
    if (text.trim() === "") return;
    text = text.replace(/\s+/g, " ");
    text = text.replace(/\u00ae/g, "(R)");
    text = text.replace(/\u2122/g, "(TM)");
    if (finalText === "" || finalText[finalText.length - 1] === "\n") text = text.trimLeft();
    finalText += text;
  }
})());
