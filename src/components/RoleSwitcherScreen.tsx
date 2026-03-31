import { motion } from 'motion/react';
import { Button } from './ui/button';
import { ShoppingBag, Store } from 'lucide-react';
import { useTranslation } from '../context/TranslationContext';

interface RoleSwitcherScreenProps {
  onSelectMode: (mode: 'buyer' | 'seller') => void;
}

export function RoleSwitcherScreen({ onSelectMode }: RoleSwitcherScreenProps) {
  const { t } = useTranslation();

  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-br from-[#af47ff] via-[#9935e6] to-[#7c24cc]">
      <div className="flex flex-1 flex-col items-center justify-center p-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-md text-center"
        >
          {/* Logo/Title */}
          <div className="mb-8">
            <h1 className="mb-2 text-white">UDX</h1>
            <p className="text-white/90">Choose your mode</p>
          </div>

          {/* Role Selection Cards */}
          <div className="space-y-4">
            {/* Buyer Mode */}
            <motion.div
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => onSelectMode('buyer')}
              className="cursor-pointer"
            >
              <div className="rounded-2xl bg-white p-6 shadow-lg transition-all hover:shadow-xl">
                <div className="flex items-center gap-4">
                  <div className="flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-[#af47ff] to-[#9935e6]">
                    <ShoppingBag className="h-8 w-8 text-white" />
                  </div>
                  <div className="flex-1 text-left">
                    <h2 className="mb-1">Buyer</h2>
                    <p className="text-gray-600">Browse and purchase products</p>
                  </div>
                </div>
              </div>
            </motion.div>

            {/* Seller Mode */}
            <motion.div
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => onSelectMode('seller')}
              className="cursor-pointer"
            >
              <div className="rounded-2xl bg-white p-6 shadow-lg transition-all hover:shadow-xl">
                <div className="flex items-center gap-4">
                  <div className="flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-[#af47ff] to-[#9935e6]">
                    <Store className="h-8 w-8 text-white" />
                  </div>
                  <div className="flex-1 text-left">
                    <h2 className="mb-1">Seller</h2>
                    <p className="text-gray-600">Manage and sell your products</p>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>

          {/* Info Text */}
          <p className="mt-8 text-sm text-white/80">
            You can switch between modes anytime from your profile
          </p>
        </motion.div>
      </div>
    </div>
  );
}
