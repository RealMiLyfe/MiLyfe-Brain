"use client";

import { motion } from "framer-motion";
import { clsx } from "clsx";
import {
  Gamepad2,
  Camera,
  FileText,
  Globe,
  Palette,
  Bot,
  Music,
  Calculator,
  BookOpen,
  Rocket,
  Shield,
  Heart,
} from "lucide-react";

interface Template {
  id: string;
  title: string;
  description: string;
  icon: typeof Gamepad2;
  color: string;
  bgGradient: string;
  prompt: string;
  difficulty: "easy" | "medium" | "hard";
  category: "fun" | "creative" | "productivity" | "learning";
}

const GUIDED_TEMPLATES: Template[] = [
  {
    id: "dino-game",
    title: "Build a Dino Game",
    description: "Create a fun Chrome-style dinosaur jumping game with obstacles and score!",
    icon: Gamepad2,
    color: "text-emerald-600",
    bgGradient: "from-emerald-100 to-green-200 dark:from-emerald-900/40 dark:to-green-900/30",
    prompt: "Build a browser-based dinosaur jumping game similar to Chrome's offline game. Use HTML5 Canvas with JavaScript. Include: a jumping dinosaur character, scrolling ground, random cacti obstacles, score counter, game over screen with restart, and increasing difficulty. Make it colorful and fun with simple pixel art style.",
    difficulty: "medium",
    category: "fun",
  },
  {
    id: "organize-photos",
    title: "Organize My Photos",
    description: "Sort photos into folders by date, location, or content automatically",
    icon: Camera,
    color: "text-blue-600",
    bgGradient: "from-blue-100 to-cyan-200 dark:from-blue-900/40 dark:to-cyan-900/30",
    prompt: "Create a Python script that organizes photos in a folder. The script should: read EXIF data from images, create subfolders by year/month (e.g., 2024/January), move photos into the correct folders, handle duplicates gracefully, generate a summary report of what was organized, and support JPG, PNG, HEIC formats.",
    difficulty: "easy",
    category: "productivity",
  },
  {
    id: "research-report",
    title: "Research & Write Report",
    description: "Research any topic and produce a well-structured report with sources",
    icon: FileText,
    color: "text-purple-600",
    bgGradient: "from-purple-100 to-violet-200 dark:from-purple-900/40 dark:to-violet-900/30",
    prompt: "Research the topic of renewable energy trends in 2024-2025. Produce a comprehensive report that includes: executive summary, current state of solar/wind/battery technology, market trends and growth statistics, key companies and innovations, challenges and opportunities, future outlook. Format as a professional markdown document with proper sections and citations.",
    difficulty: "medium",
    category: "learning",
  },
  {
    id: "personal-website",
    title: "Build My Website",
    description: "Create a beautiful personal portfolio website with your info",
    icon: Globe,
    color: "text-indigo-600",
    bgGradient: "from-indigo-100 to-blue-200 dark:from-indigo-900/40 dark:to-blue-900/30",
    prompt: "Build a modern personal portfolio website using HTML, CSS, and JavaScript. Include: hero section with animated text, about me section, project showcase grid with hover effects, skills section with progress bars, contact form, dark/light mode toggle, smooth scroll navigation, responsive mobile design, and subtle animations. Use a clean, minimal aesthetic with custom CSS (no frameworks).",
    difficulty: "medium",
    category: "creative",
  },
  {
    id: "art-generator",
    title: "Drawing App",
    description: "Build a colorful drawing canvas with brushes, colors, and stamps",
    icon: Palette,
    color: "text-pink-600",
    bgGradient: "from-pink-100 to-rose-200 dark:from-pink-900/40 dark:to-rose-900/30",
    prompt: "Create a web-based drawing application using HTML5 Canvas. Features: color picker with preset bright colors, adjustable brush size slider, eraser tool, clear canvas button, undo/redo, save as PNG, stamp tool (stars, hearts, smiley faces), fill bucket, and a fun rainbow brush mode. Make the UI colorful and kid-friendly with large buttons.",
    difficulty: "medium",
    category: "fun",
  },
  {
    id: "chatbot",
    title: "Build a Chatbot",
    description: "Create a friendly AI chatbot that can answer questions",
    icon: Bot,
    color: "text-cyan-600",
    bgGradient: "from-cyan-100 to-teal-200 dark:from-cyan-900/40 dark:to-teal-900/30",
    prompt: "Build a simple chatbot web interface that connects to the local Ollama API. Include: a chat UI with message bubbles, typing indicators, the ability to choose different personas (helpful assistant, pirate, scientist), message history that persists in localStorage, and a clean modern design. Use vanilla JavaScript with fetch() to call Ollama's /api/chat endpoint.",
    difficulty: "hard",
    category: "creative",
  },
  {
    id: "music-player",
    title: "Music Visualizer",
    description: "Create a music player with awesome audio visualizations",
    icon: Music,
    color: "text-violet-600",
    bgGradient: "from-violet-100 to-purple-200 dark:from-violet-900/40 dark:to-purple-900/30",
    prompt: "Build a web-based audio visualizer using the Web Audio API and Canvas. Features: file upload for MP3s, play/pause/seek controls, 3 visualization modes (bar graph, waveform, circular), color themes, fullscreen mode, and responsive design. The visualizations should react to the music's frequency data in real-time.",
    difficulty: "hard",
    category: "fun",
  },
  {
    id: "calculator",
    title: "Smart Calculator",
    description: "Build a calculator that can solve math problems step-by-step",
    icon: Calculator,
    color: "text-amber-600",
    bgGradient: "from-amber-100 to-yellow-200 dark:from-amber-900/40 dark:to-yellow-900/30",
    prompt: "Create a web calculator application with two modes: basic calculator (standard operations, memory, percentage) and a step-by-step solver that shows work for algebra problems. Include: clean button layout, history panel, keyboard support, and ability to copy results. Style with a modern glass-morphism design.",
    difficulty: "easy",
    category: "learning",
  },
  {
    id: "story-writer",
    title: "Story Creator",
    description: "Generate creative stories with characters, plot twists, and illustrations",
    icon: BookOpen,
    color: "text-rose-600",
    bgGradient: "from-rose-100 to-pink-200 dark:from-rose-900/40 dark:to-pink-900/30",
    prompt: "Create a story generator web app. The user picks: genre (fantasy, sci-fi, mystery, adventure), main character name and traits, setting, and story length. Then generate a creative short story with chapters, dialogue, and a plot twist. Display it in a book-like reading format with chapter navigation. Include a 'remix' button to regenerate with different twists.",
    difficulty: "medium",
    category: "creative",
  },
  {
    id: "automation",
    title: "Automate My Tasks",
    description: "Create scripts to automate boring repetitive computer tasks",
    icon: Rocket,
    color: "text-orange-600",
    bgGradient: "from-orange-100 to-red-200 dark:from-orange-900/40 dark:to-red-900/30",
    prompt: "Create a collection of useful automation scripts in Python. Include: 1) File organizer (sort downloads by type), 2) Bulk image resizer, 3) CSV data cleaner, 4) Email template generator, 5) Simple backup script with zip compression. Each script should have clear comments, error handling, and a simple CLI interface. Package them in a folder with a README explaining each one.",
    difficulty: "easy",
    category: "productivity",
  },
  {
    id: "security-audit",
    title: "Security Check",
    description: "Scan your code for vulnerabilities and get fix suggestions",
    icon: Shield,
    color: "text-red-600",
    bgGradient: "from-red-100 to-orange-200 dark:from-red-900/40 dark:to-orange-900/30",
    prompt: "Perform a security audit on the workspace code. Check for: hardcoded secrets/API keys, SQL injection vulnerabilities, XSS attack vectors, insecure dependencies, improper file permissions, missing input validation, CORS misconfiguration, and authentication bypasses. Generate a detailed report with severity levels (critical/high/medium/low), affected files, and specific remediation steps for each finding.",
    difficulty: "hard",
    category: "productivity",
  },
  {
    id: "wellness-tracker",
    title: "Wellness Tracker",
    description: "Build a daily mood and habit tracker with charts and streaks",
    icon: Heart,
    color: "text-pink-600",
    bgGradient: "from-pink-100 to-purple-200 dark:from-pink-900/40 dark:to-purple-900/30",
    prompt: "Build a wellness/habit tracker web app. Features: daily mood logging (emoji picker: great/good/ok/bad), habit checklist (customizable habits like exercise, reading, water), streak counter with fire emoji, weekly/monthly chart visualization using simple SVG or Canvas, motivational quotes, data stored in localStorage. Colorful, friendly UI with pastel colors and smooth animations.",
    difficulty: "medium",
    category: "learning",
  },
];

const DIFFICULTY_BADGES = {
  easy: { label: "Beginner", color: "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400" },
  medium: { label: "Intermediate", color: "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400" },
  hard: { label: "Advanced", color: "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400" },
};

const CATEGORY_LABELS = {
  fun: "Fun & Games",
  creative: "Creative",
  productivity: "Productivity",
  learning: "Learning",
};

interface GuidedTemplatesProps {
  onSelect: (prompt: string) => void;
  filter?: string;
}

export function GuidedTemplates({ onSelect, filter }: GuidedTemplatesProps) {
  const filtered = filter
    ? GUIDED_TEMPLATES.filter((t) => t.category === filter || t.difficulty === filter)
    : GUIDED_TEMPLATES;

  return (
    <div className="space-y-4">
      {/* Category pills */}
      <div className="flex flex-wrap gap-2">
        {Object.entries(CATEGORY_LABELS).map(([key, label]) => (
          <span
            key={key}
            className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 font-medium"
          >
            {label}
          </span>
        ))}
      </div>

      {/* Template grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {filtered.map((template, idx) => {
          const Icon = template.icon;
          const diffBadge = DIFFICULTY_BADGES[template.difficulty];

          return (
            <motion.button
              key={template.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.04 }}
              onClick={() => onSelect(template.prompt)}
              className={clsx(
                "group relative text-left p-4 rounded-xl border border-slate-200 dark:border-slate-700",
                "hover:border-primary-300 dark:hover:border-primary-600 hover:shadow-md",
                "transition-all duration-200 overflow-hidden"
              )}
            >
              {/* Background gradient on hover */}
              <div className={clsx(
                "absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-gradient-to-br",
                template.bgGradient
              )} />

              <div className="relative z-10">
                {/* Icon + difficulty */}
                <div className="flex items-center justify-between mb-2">
                  <div className={clsx("w-9 h-9 rounded-lg flex items-center justify-center bg-white/80 dark:bg-slate-800/80 shadow-sm")}>
                    <Icon className={clsx("w-5 h-5", template.color)} />
                  </div>
                  <span className={clsx("text-[10px] px-1.5 py-0.5 rounded-full font-medium", diffBadge.color)}>
                    {diffBadge.label}
                  </span>
                </div>

                {/* Title + description */}
                <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-100 mb-1 group-hover:text-primary-700 dark:group-hover:text-primary-300 transition-colors">
                  {template.title}
                </h4>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-2 leading-relaxed">
                  {template.description}
                </p>
              </div>
            </motion.button>
          );
        })}
      </div>
    </div>
  );
}
