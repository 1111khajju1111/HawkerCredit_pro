'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { LogOut, LogIn } from 'lucide-react';

export function HeaderAuthControls() {
  const { user, logout } = useAuth();
  const router = useRouter();

  if (!user) {
    return (
      <Link
        href="/login"
        className="brutal-btn px-3 py-2 bg-white text-black dark:bg-black dark:text-white text-xs flex items-center gap-1.5"
      >
        <LogIn className="w-3.5 h-3.5 text-brandRed" /> SIGN IN
      </Link>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <span className="hidden lg:inline text-[10px] font-black uppercase text-gray-500">
        {user.email} &middot; {user.role}
      </span>
      <button
        onClick={() => {
          logout();
          router.push('/login');
        }}
        className="brutal-btn px-3 py-2 bg-white text-black dark:bg-black dark:text-white text-xs flex items-center gap-1.5"
      >
        <LogOut className="w-3.5 h-3.5 text-brandRed" /> LOG OUT
      </button>
    </div>
  );
}
