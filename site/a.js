var sidebarContent = '' +
  '<div class="avatar" style="background-image:url(/site/josh.jpg)"></div>' +
  '<h3>Josh Wolfe</h3>' +
  '<div class="fancy-divider-line"></div>' +
  '<p class="snippet">I like working on open-source games.</p>' +
  '<div class="fancy-divider-line"></div>' +
  '<ul class="nav">' +
  '  <li><a href="/">Home</a>' +
  '    <ul>' +
  '      <li><a href="/#games">Games</a></li>' +
  '      <li><a href="/#game-utilities">Utilities for Games</a></li>' +
  '      <li><a href="/#academia">Academia</a></li>' +
  '    </ul>' +
  '  </li>' +
  '  <li><a href="/resume">Resume</a></li>' +
  '  <li><a href="github.com/thejoshwolfe">Github</a></li>' +
  '</ul>';
document.getElementById("sidebar").innerHTML = sidebarContent;
