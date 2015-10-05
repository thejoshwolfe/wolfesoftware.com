document.getElementById("plainTextDownload").setAttribute("href", (function() {
  var sections = [];
  var currentSection = null;
  var textBuffer = "";
  visit(document.body);
  flushCurrentSection();
  return "data:text/plain;charset=US-ASCII," + encodeURIComponent(renderAsPlainText(sections));

  function visit(node) {
    if (node.nodeType === Node.TEXT_NODE) {
      handleText(node.textContent);
    }
    if (node.nodeType !== Node.ELEMENT_NODE) return;
    if (node.classList.contains("no-print")) return;
    var tagName = node.tagName.toLowerCase();
    switch (tagName) {
      case "li":
        textBuffer += " * ";
        break;
      case "h1":
      case "h2":
      case "h3":
        flushCurrentSection();
        break;
      case "ul":
        textBuffer = textBuffer.trimRight();
        textBuffer += "\n";
        break;
    }
    var children = node.childNodes;
    for (var i = 0; i < children.length; i++) {
      visit(children[i]);
    }
    switch (tagName) {
      case "li":
        textBuffer += "\n";
        break;
      case "h1":
      case "h2":
      case "h3":
        currentSection = {
          heading: textBuffer,
          content: null,
          level: parseInt(tagName.substring(1), 10),
          classList: node.classList,
        }
        textBuffer = "";
        break;
    }
    if (node.classList.contains("date")) {
      currentSection.heading += " (" + textBuffer + ")";
      textBuffer = "";
    }
  }

  function handleText(text) {
    if (text.trim() === "") return;
    text = text.replace(/\s+/g, " ");
    // turn unicode to ascii
    text = text.replace(/\u00ae/g, "(R)");
    text = text.replace(/\u2122/g, "(TM)");
    if (textBuffer === "" || textBuffer[textBuffer.length - 1] === "\n") text = text.trimLeft();
    textBuffer += text;
  }

  function flushCurrentSection() {
    if (currentSection == null) return;
    currentSection.content = textBuffer.trim();
    sections.push(currentSection);
    textBuffer = "";
  }

  function renderAsPlainText(sections) {
    var result = sections.map(function(section) {
      var oneLine = section.classList.contains("plain-text-one-line");
      var result = "";
      if (oneLine) {
        result = "\n" + section.heading + ": " + section.content;
      } else if (section.content === "") {
        var length = section.heading.length;
        result = "\n\n\n" + section.heading + "\n";
        for (var i = 0; i < length; i++) {
          result += "=";
        }
      } else {
        result = "\n\n" + section.heading + "\n" + section.content;
      }
      return result;
    }).join("").trim();
    // sanity check for non-ascii
    var badChars = result.replace(/[\u0000-\u007f]+/g, "");
    if (badChars.length !== 0) {
      alert("plain text rendering contains non-ascii characters: " + badChars);
    }
    return result;
  }
})());
