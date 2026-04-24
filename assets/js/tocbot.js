tocbot.init({
  // Where to render the table of contents.
  tocSelector: '.toc',
  // Where to grab the headings to build the table of contents.
  contentSelector: '.page__content',
  // Which headings to grab inside of the contentSelector element.
  headingSelector: 'h1, h2, h3',
  // 处理page__content的嵌套标签，开启后，兼容性更好
  hasInnerContainers: true,
  //目录默认折叠到哪一级
  collapseDepth: 2,
  scrollSmooth: true,
  headingsOffset: 80,
  scrollSmoothOffset: -80
});
