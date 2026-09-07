'use client';

import './globals.css';
import Link from 'next/link';
import { ThemeProvider } from '@/components/ThemeProvider';
import { ThemeToggle } from '@/components/ThemeToggle';
import { Cpu, ShieldCheck, UserCheck, Play, LayoutDashboard, Sparkles } from 'lucide-react';
import { AuthProvider } from '@/lib/auth';
import { HeaderAuthControls } from '@/components/HeaderAuthControls';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head>
        <title>HAWKERCREDIT QUANTUM — Minimalist Brutalist AI + Quantum Credit Platform</title>
        <meta name="description" content="AI + Quantum-Enhanced Alternative Credit Intelligence for Street Vendors in Minimalist Red, Black, and White Brutalism." />
      </head>
      <body className="bg-lightBg dark:bg-darkBg text-black dark:text-white min-h-screen flex flex-col font-sans border-t-4 border-t-brandRed">
        <AuthProvider>
        <ThemeProvider>
          {/* Header Navigation */}
          <header className="border-b-4 border-black dark:border-white bg-lightSurface dark:bg-darkSurface sticky top-0 z-50">
            <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
              {/* Brand Logo */}
              <Link href="/" className="flex items-center gap-2 group">
                <div className="w-8 h-8 bg-brandRed text-white flex items-center justify-center font-mono font-black text-lg border-2 border-black dark:border-white shadow-[2px_2px_0px_0px_#000] dark:shadow-[2px_2px_0px_0px_#fff]">
                  HQ
                </div>
                <div className="flex flex-col">
                  <span className="font-mono font-black text-base tracking-tighter uppercase text-black dark:text-white">
                    HAWKERCREDIT
                  </span>
                  <span className="text-[9px] font-mono font-black tracking-widest text-brandRed uppercase">
                    QUANTUM // DEMO READY
                  </span>
                </div>
              </Link>

              {/* Navigation Links */}
              <nav className="hidden md:flex items-center gap-6 font-mono text-xs font-bold uppercase tracking-wider">
                <Link href="/vendor/dashboard" className="text-black dark:text-white hover:text-brandRed dark:hover:text-brandRed transition-colors flex items-center gap-1.5">
                  <LayoutDashboard className="w-3.5 h-3.5 text-brandRed" /> Vendor
                </Link>
                <Link href="/lender/dashboard" className="text-black dark:text-white hover:text-brandRed dark:hover:text-brandRed transition-colors flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-brandRed" /> Lender
                </Link>
                <Link href="/lender/portfolio/optimizer" className="text-black dark:text-white hover:text-brandRed dark:hover:text-brandRed transition-colors flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-brandRed" /> Quantum Engine
                </Link>
                <Link href="/admin/dashboard" className="text-black dark:text-white hover:text-brandRed dark:hover:text-brandRed transition-colors flex items-center gap-1.5">
                  <UserCheck className="w-3.5 h-3.5 text-brandRed" /> Admin
                </Link>
              </nav>

              {/* Controls */}
              <div className="flex items-center gap-3">
                <ThemeToggle />
                <Link href="/demo" className="brutal-btn px-4 py-2 bg-brandRed text-white text-xs flex items-center gap-1.5">
                  <Play className="w-3.5 h-3.5 fill-white" /> LIVE DEMO
                </Link>
                <HeaderAuthControls />
              </div>
            </div>
          </header>

          {/* Page Content */}
          <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-6 space-y-6">
            {children}
          </main>

          {/* Footer */}
          <footer className="border-t-4 border-black dark:border-white bg-lightSurface dark:bg-darkSurface py-6 mt-12 text-center text-xs font-mono">
            <div className="max-w-7xl mx-auto px-4 flex flex-col md:flex-row items-center justify-between gap-4">
              <p className="font-bold text-black dark:text-white">
                © 2026 HAWKERCREDIT QUANTUM — MINIMALIST BRUTALISM EDITION
              </p>
              <p className="text-brandRed font-black text-[11px] uppercase tracking-wider">
                [RESPONSIBLE AI]: AI & QUANTUM RECOMMENDATIONS REQUIRE HUMAN LENDER APPROVAL
              </p>
            </div>
          </footer>
        </ThemeProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
