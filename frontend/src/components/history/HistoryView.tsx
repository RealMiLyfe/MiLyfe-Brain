"use client";

import { useEffect, useState } from "react";
import { PlayCircle, Trash2, CheckCircle, XCircle, Clock } from "lucide-react";
import { playbookApi } from "@/lib/api";
import { useBrainStore } from "@/lib/store";

export function HistoryView() {
  const [playbooks, setPlaybooks] = useState<any[]>([]);
  const setCurrentPlaybook = useBrainStore((s) => s.setCurrentPlaybook);

  const load = async () => { try { setPlaybooks(await playbookApi.list()); } catch {} };
  useEffect(() => { load(); }, []);

  const statusIcon = (status: string) => {
    switch (status) {
      case "completed": return <CheckCircle className="w-4 h-4 text-green-400" />;
      case "failed": return <XCircle className="w-4 h-4 text-red-400" />;
      case "running": return <PlayCircle className="w-4 h-4 text-blue-400 animate-pulse" />;
      default: return <Clock className="w-4 h-4 text-gray-500" />;
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-8">
      <h1 className="text-2xl font-bold text-white mb-6">Playbook History</h1>

      <div className="space-y-2">
        {playbooks.length === 0 ? (
          <div className="text-center py-16 text-gray-500">
            <History className="w-10 h-10 mx-auto mb-3 text-gray-600" />
            <p>No playbooks yet</p>
          </div>
        ) : (
          playbooks.map((pb) => (
            <div key={pb.id} className="flex items-center gap-3 bg-gray-900 border border-gray-800 rounded-lg p-4 hover:border-gray-700">
              {statusIcon(pb.status)}
              <div className="flex-1">
                <p className="text-sm text-white font-medium">{pb.title}</p>
                <p className="text-xs text-gray-500">{pb.description?.slice(0, 80)}</p>
              </div>
              <span className="text-xs text-gray-500">{new Date(pb.created_at).toLocaleDateString()}</span>
              <button onClick={() => { playbookApi.rerun(pb.id); }} className="p-1.5 text-gray-500 hover:text-blue-400" title="Re-run">
                <PlayCircle className="w-4 h-4" />
              </button>
              <button onClick={async () => { await playbookApi.delete(pb.id); load(); }} className="p-1.5 text-gray-500 hover:text-red-400" title="Delete">
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function History(props: any) {
  return <Clock {...props} />;
}
