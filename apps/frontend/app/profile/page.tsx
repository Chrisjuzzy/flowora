"use client";
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import { getMe } from '@/lib/api';
import { useAuthStore } from '@/store/auth';

export default function Profile() {
  const [user, setUser] = useState<{email: string, id: number} | null>(null);
  const router = useRouter();
  const clear = useAuthStore((state) => state.clear);

  useEffect(() => {
    async function load() {
      try {
        const data = await getMe();
        setUser(data);
      } catch (e) {
        console.error(e);
        router.push('/login');
      }
    }
    load();
  }, [router]);

  const handleLogout = () => {
    clear();
    router.push('/login');
  };

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 p-8">
        <h1 className="text-3xl font-bold mb-8 text-gray-900">Profile</h1>
        {user ? (
          <div className="bg-white p-8 rounded-lg shadow-sm border border-gray-200 max-w-md">
            <div className="mb-6">
              <label className="block text-sm font-bold text-gray-500 uppercase tracking-wide mb-1">Email</label>
              <p className="text-xl text-gray-900 font-medium">{user.email}</p>
            </div>
            <div className="mb-8">
              <label className="block text-sm font-bold text-gray-500 uppercase tracking-wide mb-1">User ID</label>
              <p className="text-xl text-gray-900 font-medium">#{user.id}</p>
            </div>
            <button
              onClick={handleLogout}
              className="w-full bg-red-50 text-red-600 py-3 rounded-lg hover:bg-red-100 transition-colors font-semibold border border-red-200"
            >
              Sign Out
            </button>
          </div>
        ) : (
          <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-600"></div>
          </div>
        )}
      </div>
    </div>
  );
}
