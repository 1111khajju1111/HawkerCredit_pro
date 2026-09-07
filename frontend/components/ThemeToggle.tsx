'use client';

import { useTheme } from './ThemeProvider';
import { Sun, Moon } from 'lucide-react';

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className="p-2 rounded-none border-2 border-black dark:border-white bg-white dark:bg-black text-black dark:text-white font-extrabold text-xs flex items-center gap-1.5 shadow-[2px_2px_0px_0px_#dc2626] hover:translate-x-[-1px] hover:translate-y-[-1px] transition-transform"
      aria-label="Toggle theme"
    >
      {theme === 'dark' ? (
        <>
          <Sun className="w-4 h-4 text-brandRed" />
          <span className="uppercase tracking-wider font-mono text-[10px]">LIGHT</span>
        </>
      ) : (
        <>
          <Moon className="w-4 h-4 text-brandRed" />
          <span className="uppercase tracking-wider font-mono text-[10px]">DARK</span>
        </>
      )}
    </button>
  );
}
