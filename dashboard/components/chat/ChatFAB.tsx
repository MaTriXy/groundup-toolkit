"use client"

import { MessageSquare } from "lucide-react"
import { useChatStore } from "@/lib/store/chatStore"
import { motion, AnimatePresence } from "framer-motion"

export function ChatFAB() {
  const { isOpen, openChat } = useChatStore()

  return (
    <AnimatePresence>
      {!isOpen && (
        <motion.button
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0, opacity: 0 }}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => openChat()}
          className="fixed bottom-6 right-6 z-30 flex h-12 w-12 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg shadow-primary/25 hover:shadow-primary/40 transition-shadow"
        >
          <MessageSquare className="h-5 w-5" />
        </motion.button>
      )}
    </AnimatePresence>
  )
}
