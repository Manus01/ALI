import React from 'react';
import useDarkMode from '../hooks/useDarkMode';

export default function ThemeToggle() {
  const [theme, setTheme] = useDarkMode();

  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        aria-pressed={theme === 'light'}
        aria-label="Light theme"
        onClick={() => setTheme('light')}
        className="px-3 py-1 rounded border bg-white text-black dark:bg-gray-800 dark:text-white"
      >
        Light
      </button>

      <button
        type="button"
        aria-pressed={theme === 'dark'}
        aria-label="Dark theme"
        onClick={() => setTheme('dark')}
        className="px-3 py-1 rounded border bg-gray-900 text-white dark:bg-gray-700 dark:text-white"
      >
        Dark
      </button>

      <button
        type="button"
        aria-pressed={theme === 'system'}
        aria-label="System theme"
        onClick={() => setTheme('system')}
        className="px-3 py-1 rounded border bg-transparent"
      >
        System
      </button>
    </div>
  );
}
