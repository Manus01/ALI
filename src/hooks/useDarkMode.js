import { useEffect, useState } from 'react';

const THEME_KEY = 'theme'; // 'light' | 'dark' | 'system'

function getSystemPrefersDark() {
  try {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  } catch (e) {
    return false;
  }
}

function readStoredTheme() {
  try {
    return localStorage.getItem(THEME_KEY);
  } catch (e) {
    return null;
  }
}

export default function useDarkMode() {
  const [theme, setThemeState] = useState(() => {
    if (typeof window === 'undefined') return 'system';
    const stored = readStoredTheme();
    return stored || 'system';
  });

  // apply theme to documentElement
  useEffect(() => {
    const root = document.documentElement;
    const apply = (choice) => {
      if (choice === 'system' || !choice) {
        root.classList.toggle('dark', getSystemPrefersDark());
      } else {
        root.classList.toggle('dark', choice === 'dark');
      }
    };
    apply(theme);

    // listen for system changes when in 'system' mode
    let mq;
    const onChange = (e) => {
      if (theme === 'system') {
        root.classList.toggle('dark', e.matches);
      }
    };
    try {
      mq = window.matchMedia('(prefers-color-scheme: dark)');
      mq && mq.addEventListener && mq.addEventListener('change', onChange);
    } catch (e) {
      // ignore
    }

    return () => {
      try {
        mq && mq.removeEventListener && mq.removeEventListener('change', onChange);
      } catch (e) {}
    };
  }, [theme]);

  // persist to localStorage
  useEffect(() => {
    try {
      if (theme === 'system') localStorage.removeItem(THEME_KEY); else localStorage.setItem(THEME_KEY, theme);
    } catch (e) {
      // ignore
    }
  }, [theme]);

  const setTheme = (choice) => {
    setThemeState(choice);
  };

  return [theme, setTheme];
}
