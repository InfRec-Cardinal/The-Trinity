(function (root) {
  'use strict';
  const key = 'trinity-studio.theme';
  const normalize = value => value === 'dark' ? 'dark' : 'light';
  let theme = 'light';
  try {theme = normalize(root.localStorage.getItem(key));} catch (_) {}
  document.documentElement.dataset.theme = theme;
  root.TrinityTheme = Object.freeze({
    get: () => theme,
    set: value => {
      theme = normalize(value);
      document.documentElement.dataset.theme = theme;
      try {root.localStorage.setItem(key, theme);} catch (_) {}
    },
  });
})(globalThis);
