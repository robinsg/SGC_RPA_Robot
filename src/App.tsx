import { useState, useEffect } from 'react';
import { Terminal, FileCode, Play, AlertCircle, Info, FolderTree, Search, CheckCircle2, Sun, Moon } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

export default function App() {
  const [theme, setTheme] = useState<'light' | 'dark'>('dark');
  const [lastScreen, setLastScreen] = useState<string>('');

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  return (
    <div className={`min-h-screen font-sans transition-colors duration-300 ${theme === 'dark' ? 'bg-zinc-950 text-zinc-100' : 'bg-zinc-50 text-zinc-900'} p-8`}>
      <header className="max-w-5xl mx-auto mb-12 flex justify-between items-start">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <Terminal className={`w-8 h-8 ${theme === 'dark' ? 'text-blue-400' : 'text-blue-600'}`} />
            <h1 className="text-3xl font-bold tracking-tight">5250 RPA Robot</h1>
          </div>
          <p className={`${theme === 'dark' ? 'text-zinc-400' : 'text-zinc-500'} text-lg`}>Simple, robust YAML-driven automation for IBM i terminals.</p>
        </div>
        
        <button 
          onClick={toggleTheme}
          className={`p-2 rounded-full border transition-all ${theme === 'dark' ? 'border-zinc-800 bg-zinc-900 hover:bg-zinc-800 text-yellow-400' : 'border-zinc-200 bg-white hover:bg-zinc-100 text-zinc-600 shadow-sm'}`}
          title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
        >
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={theme}
              initial={{ opacity: 0, rotate: -20, scale: 0.8 }}
              animate={{ opacity: 1, rotate: 0, scale: 1 }}
              exit={{ opacity: 0, rotate: 20, scale: 0.8 }}
              transition={{ duration: 0.2 }}
            >
              {theme === 'light' ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5" />}
            </motion.div>
          </AnimatePresence>
        </button>
      </header>

      <main className="max-w-5xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Script Preview */}
        <motion.section 
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          className="lg:col-span-1 space-y-6"
        >
          <div className={`${theme === 'dark' ? 'bg-zinc-900 border-zinc-800' : 'bg-white border-zinc-200'} rounded-xl shadow-sm border p-6`}>
            <div className={`flex items-center gap-2 mb-4 font-semibold ${theme === 'dark' ? 'text-blue-400' : 'text-blue-700'}`}>
              <FileCode className="w-5 h-5" />
              <h2>Example Script</h2>
            </div>
            <div className="bg-zinc-950 rounded-lg p-4 font-mono text-xs text-zinc-300 overflow-auto max-h-[500px] border border-zinc-800/50">
              <pre>{`name: "Logout Script"
tmux_session: "5250_robot"

steps:
  - type: "wait_for_text"
    text: "MAIN MENU"
    row: 1
    col: 28

  - type: "wait_for_text"
    text: "Selection or command"
    row: 19
    col: 1
    end_row: 21
    end_col: 40

  - type: "press_key_if_text_present"
    text: "Sign On Information"
    key: "Enter"

  - type: "send_key"
    key: "F3"
    
  - type: "capture"
    filename: "logout_state"`}</pre>
            </div>
          </div>

          <div className={`${theme === 'dark' ? 'bg-blue-950/30 border-blue-900/50' : 'bg-blue-50 border-blue-100'} border rounded-xl p-6`}>
            <h3 className={`font-semibold mb-3 flex items-center gap-2 ${theme === 'dark' ? 'text-blue-300' : 'text-blue-800'}`}>
              <Search className="w-4 h-4" />
              Search Capabilities
            </h3>
            <ul className={`text-sm space-y-2 ${theme === 'dark' ? 'text-blue-200/80' : 'text-blue-700'}`}>
              <li className="flex gap-2">
                <CheckCircle2 className={`w-4 h-4 mt-0.5 flex-shrink-0 ${theme === 'dark' ? 'text-blue-400' : 'text-blue-500'}`} />
                <span><strong>Block Search:</strong> Scan rectangular areas.</span>
              </li>
              <li className="flex gap-2">
                <CheckCircle2 className={`w-4 h-4 mt-0.5 flex-shrink-0 ${theme === 'dark' ? 'text-blue-400' : 'text-blue-500'}`} />
                <span><strong>Precise Search:</strong> Match specific coordinates.</span>
              </li>
              <li className="flex gap-2">
                <CheckCircle2 className={`w-4 h-4 mt-0.5 flex-shrink-0 ${theme === 'dark' ? 'text-blue-400' : 'text-blue-500'}`} />
                <span><strong>Message Line:</strong> Auto-detect status lines.</span>
              </li>
            </ul>
          </div>
        </motion.section>

        {/* Center/Right Column: Setup and Logs */}
        <div className="lg:col-span-2 space-y-8">
          <motion.section 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={`${theme === 'dark' ? 'bg-zinc-900 border-zinc-800' : 'bg-white border-zinc-200'} rounded-xl shadow-sm border p-6`}
          >
            <div className={`flex items-center gap-2 mb-6 font-semibold ${theme === 'dark' ? 'text-green-400' : 'text-green-700'}`}>
              <Play className="w-5 h-5" />
              <h2>Quick Start Guide</h2>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className={`${theme === 'dark' ? 'bg-zinc-950 border-zinc-800' : 'bg-zinc-50 border-zinc-200'} p-4 border rounded-lg`}>
                <h3 className="font-medium mb-2 text-sm">1. Configure Terminal</h3>
                <p className={`text-xs mb-2 ${theme === 'dark' ? 'text-zinc-500' : 'text-zinc-500'}`}>Update <code>.env</code> with LPAR details:</p>
                <code className="block bg-black text-zinc-300 p-2 rounded text-xs whitespace-pre overflow-x-auto border border-zinc-800/50">
                  TN5250_HOST=10.0.0.5{"\n"}
                  TN5250_SSL=on{"\n"}
                  TN5250_DEVICE_NAME=ROBOT01
                </code>
              </div>
              <div className={`${theme === 'dark' ? 'bg-zinc-950 border-zinc-800' : 'bg-zinc-50 border-zinc-200'} p-4 border rounded-lg`}>
                <h3 className="font-medium mb-2 text-sm">2. Credentials</h3>
                <p className={`text-xs mb-2 ${theme === 'dark' ? 'text-zinc-500' : 'text-zinc-500'}`}>Loaded into <code>\${"{"}USERNAME{"}"}</code> variables:</p>
                <code className="block bg-black text-zinc-300 p-2 rounded text-xs whitespace-pre border border-zinc-800/50">
                  USERNAME=OPERATOR{"\n"}
                  PASSWORD=SECRET
                </code>
              </div>
            </div>

            <div className="mt-8 p-4 bg-black rounded-lg flex items-center justify-between group border border-zinc-800">
              <div className="font-mono text-sm text-green-500">
                $ bash run-robot.sh logout.yaml
              </div>
              <div className="text-zinc-600 transition-colors text-xs font-mono">
                [EXHIBIT ONLY]
              </div>
            </div>
          </motion.section>

          <motion.section 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className={`${theme === 'dark' ? 'bg-zinc-900 border-zinc-800' : 'bg-white border-zinc-200'} rounded-xl shadow-sm border p-6`}
          >
            <div className={`flex items-center gap-2 mb-4 font-semibold ${theme === 'dark' ? 'text-purple-400' : 'text-purple-700'}`}>
              <FolderTree className="w-5 h-5" />
              <h2>LPAR-Aware Captures</h2>
            </div>
            <p className={`text-sm mb-4 ${theme === 'dark' ? 'text-zinc-400' : 'text-zinc-600'}`}>Captures are automatically organized by host and timestamped for easy auditing across multiple LPARs.</p>
            <div className={`${theme === 'dark' ? 'bg-zinc-950/50 text-zinc-400' : 'bg-zinc-50 text-zinc-500'} rounded-lg p-4 font-mono text-xs space-y-1 border ${theme === 'dark' ? 'border-zinc-800' : 'border-zinc-200'}`}>
              <div className="flex items-center gap-2">
                <FolderTree className="w-3 h-3" /> captures/
              </div>
              <div className="ml-4 flex items-center gap-2">
                 <FolderTree className={`w-3 h-3 ${theme === 'dark' ? 'text-purple-500' : 'text-purple-400'}`} /> 10.0.0.5/
              </div>
              <div className={theme === 'dark' ? 'ml-8 text-zinc-500' : 'ml-8 text-zinc-400'}>
                - login_state_2024-04-27T06-00-00Z.txt
              </div>
              <div className={theme === 'dark' ? 'ml-8 text-zinc-500' : 'ml-8 text-zinc-400'}>
                - logout_state_2024-04-27T06-05-10Z.txt
              </div>
              <div className="ml-4 flex items-center gap-2">
                <FolderTree className={`w-3 h-3 ${theme === 'dark' ? 'text-purple-500' : 'text-purple-400'}`} /> 10.0.0.12/
              </div>
              <div className={theme === 'dark' ? 'ml-8 text-zinc-500' : 'ml-8 text-zinc-400'}>
                - error_state_2024-04-27T06-12-45Z.txt
              </div>
            </div>
          </motion.section>
        </div>
      </main>

      <footer className={`max-w-5xl mx-auto mt-12 text-sm border-t pt-8 flex items-center justify-between ${theme === 'dark' ? 'border-zinc-800 text-zinc-500' : 'border-zinc-100 text-zinc-400'}`}>
        <p>Built for resilience and simple terminal orchestration.</p>
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1 font-mono text-xs"><Terminal className="w-3 h-3" /> Tmux</span>
          <span className="flex items-center gap-1 font-mono text-xs"><FileCode className="w-3 h-3" /> YAML</span>
          <span className="flex items-center gap-1 font-mono text-xs"><AlertCircle className="w-3 h-3" /> No-Code</span>
        </div>
      </footer>
    </div>
  );
}



