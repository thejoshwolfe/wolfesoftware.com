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
    var previousLevel = 1;
    var nestingJump = 0;
    var result = sections.map(function(section) {
      if (section.level !== previousLevel) {
        nestingJump = section.level - previousLevel;
        previousLevel = section.level;
      }
      var leadingNewlines;
      if (nestingJump > 1)
        leadingNewlines = "\n";
      else
        leadingNewlines = "\n\n";
      if (section.content === "") return leadingNewlines + section.heading;
      if (nestingJump === 2) return leadingNewlines + section.heading + ": " + section.content;
      return leadingNewlines + section.heading + "\n" + section.content;
    }).join("").trim();
    // sanity check for non-ascii
    var badChars = result.replace(/[\u0000-\u007f]+/g, "");
    if (badChars.length !== 0) {
      alert("plain text rendering contains non-ascii characters: " + badChars);
    }
    return result;
  }
})());
