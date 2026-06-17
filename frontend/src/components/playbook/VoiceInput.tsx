"use client";

import { useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Mic, MicOff, Loader2, Square } from "lucide-react";
import { clsx } from "clsx";
import { toast } from "sonner";

interface VoiceInputProps {
  onTranscript: (text: string) => void;
  disabled?: boolean;
}

/**
 * Voice input button using the Web Speech API (browser-native).
 * Falls back gracefully if not supported.
 * For local Whisper: could POST audio to backend /api/voice/transcribe endpoint.
 */
export function VoiceInput({ onTranscript, disabled }: VoiceInputProps) {
  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const [volume, setVolume] = useState(0);

  const isSupported = typeof window !== "undefined" && (
    "SpeechRecognition" in window || "webkitSpeechRecognition" in window
  );

  const startListening = useCallback(() => {
    if (!isSupported) {
      toast.error("Voice input not supported in this browser. Try Chrome or Edge.");
      return;
    }

    try {
      const SpeechRecognition = window.SpeechRecognition || (window as any).webkitSpeechRecognition;
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = "en-US";

      let finalTranscript = "";

      recognition.onresult = (event: SpeechRecognitionEvent) => {
        let interim = "";
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += transcript + " ";
          } else {
            interim = transcript;
          }
        }
        // Simulate volume from transcript length changes
        setVolume(Math.min(1, interim.length / 20));
      };

      recognition.onend = () => {
        setIsListening(false);
        setIsProcessing(true);
        setVolume(0);

        if (finalTranscript.trim()) {
          onTranscript(finalTranscript.trim());
          toast.success("Voice captured!");
        } else {
          toast.info("No speech detected. Try again.");
        }
        setIsProcessing(false);
      };

      recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
        console.error("Speech recognition error:", event.error);
        setIsListening(false);
        setVolume(0);
        if (event.error !== "aborted") {
          toast.error(`Voice error: ${event.error}`);
        }
      };

      recognition.start();
      recognitionRef.current = recognition;
      setIsListening(true);
    } catch (err) {
      toast.error("Failed to start voice input");
      console.error(err);
    }
  }, [isSupported, onTranscript]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
    setIsListening(false);
  }, []);

  const handleClick = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  if (!isSupported) {
    return null; // Hide button if not supported
  }

  return (
    <div className="relative inline-flex items-center">
      {/* Pulse rings when listening */}
      <AnimatePresence>
        {isListening && (
          <>
            <motion.div
              initial={{ scale: 1, opacity: 0.6 }}
              animate={{ scale: 2.2, opacity: 0 }}
              transition={{ duration: 1.5, repeat: Infinity }}
              className="absolute inset-0 rounded-full bg-red-400"
            />
            <motion.div
              initial={{ scale: 1, opacity: 0.4 }}
              animate={{ scale: 1.8, opacity: 0 }}
              transition={{ duration: 1.5, repeat: Infinity, delay: 0.3 }}
              className="absolute inset-0 rounded-full bg-red-400"
            />
          </>
        )}
      </AnimatePresence>

      <motion.button
        onClick={handleClick}
        disabled={disabled || isProcessing}
        whileTap={{ scale: 0.9 }}
        className={clsx(
          "relative z-10 w-10 h-10 rounded-full flex items-center justify-center transition-all duration-200",
          isListening
            ? "bg-red-500 text-white shadow-lg shadow-red-500/30"
            : "bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-primary-100 dark:hover:bg-primary-900/30 hover:text-primary-600",
          (disabled || isProcessing) && "opacity-50 cursor-not-allowed"
        )}
        title={isListening ? "Stop recording" : "Voice input"}
      >
        {isProcessing ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : isListening ? (
          <Square className="w-4 h-4" />
        ) : (
          <Mic className="w-4 h-4" />
        )}
      </motion.button>

      {/* Volume indicator */}
      {isListening && (
        <motion.div
          initial={{ opacity: 0, x: -5 }}
          animate={{ opacity: 1, x: 0 }}
          className="ml-2 flex items-center gap-0.5"
        >
          {[0, 1, 2, 3, 4].map((i) => (
            <motion.div
              key={i}
              animate={{ scaleY: volume > i * 0.2 ? 1 : 0.3 }}
              className="w-1 h-4 rounded-full bg-red-400"
              style={{ originY: 1 }}
            />
          ))}
          <span className="ml-1.5 text-xs text-red-500 font-medium">Listening...</span>
        </motion.div>
      )}
    </div>
  );
}
