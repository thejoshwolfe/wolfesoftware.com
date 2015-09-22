var sidebarContent = '' +
  '<div class="avatar bg-cover" style="background-image:url(/site/josh.jpg)"></div>' +
  '<h3>Josh Wolfe</h3>' +
  '<div class="fancy-divider-line"></div>' +
  '<p class="snippet">Software developer with a passion for compilers, games, and open-source software.</p>' +
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