"use client";

import { useState, useEffect, useRef } from "react";
import { Upload, FileText, Trash2, Search } from "lucide-react";
import axios from "axios";
import toast from "react-hot-toast";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Doc {
  id: string;
  filename: string;
  file_type: string;
  num_chunks: number;
  status: string;
  uploaded_at: string;
}

export default function KnowledgeBase() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [uploading, setUploading] = useState(false);
  const [query, setQuery] = useState("");
  const [queryResults, setQueryResults] = useState<
    { text: string; source: string; score: number }[]
  >([]);
  const fileRef = useRef<HTMLInputElement>(null);

  const fetchDocs = () => {
    axios
      .get(`${API}/api/rag/documents`)
      .then((r) => setDocs(r.data))
      .catch(() => {});
  };

  useEffect(() => {
    fetchDocs();
  }, []);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    const form = new FormData();
    form.append("file", file);
    try {
      await axios.post(`${API}/api/rag/upload`, form);
      toast.success(`${file.name} uploaded and indexed!`);
      fetchDocs();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Upload failed";
      toast.error(msg);
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const handleDelete = async (id: string, filename: string) => {
    try {
      await axios.delete(`${API}/api/rag/documents/${id}`);
      toast.success(`${filename} removed`);
      fetchDocs();
    } catch {
      toast.error("Delete failed");
    }
  };

  const handleQuery = async () => {
    if (!query.trim()) return;
    try {
      const r = await axios.post(`${API}/api/rag/query`, { query, top_k: 3 });
      setQueryResults(r.data.results);
    } catch {
      toast.error("Query failed");
    }
  };

  const STATUS_COLORS: Record<string, string> = {
    indexed: "bg-green-900/50 text-green-400",
    processing: "bg-yellow-900/50 text-yellow-400",
    error: "bg-red-900/50 text-red-400",
  };

  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-xl font-semibold text-white">Knowledge Base</h1>
        <p className="text-sm text-gray-500">
          Upload product documents to power the AI agent&apos;s answers
        </p>
      </div>

      <div
        onClick={() => fileRef.current?.click()}
        className="border-2 border-dashed border-gray-700 hover:border-brand-500 rounded-xl p-8 text-center cursor-pointer transition-colors"
      >
        <Upload className="w-10 h-10 text-gray-500 mx-auto mb-3" />
        <p className="text-gray-400 font-medium">
          {uploading ? "Uploading..." : "Click to upload PDF, TXT or DOCX"}
        </p>
        <p className="text-xs text-gray-600 mt-1">
          Files are chunked, embedded and indexed automatically
        </p>
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.txt,.docx"
          className="hidden"
          onChange={handleUpload}
        />
      </div>

      <div>
        <h2 className="text-sm font-medium text-gray-400 mb-3">
          Indexed Documents ({docs.length})
        </h2>
        <div className="space-y-2">
          {docs.length === 0 && (
            <p className="text-gray-600 text-sm text-center py-6">
              No documents yet. Upload your first document above.
            </p>
          )}
          {docs.map((doc) => (
            <div key={doc.id} className="card flex items-center justify-between">
              <div className="flex items-center gap-3">
                <FileText className="w-5 h-5 text-gray-500 shrink-0" />
                <div>
                  <p className="text-sm font-medium text-white">{doc.filename}</p>
                  <p className="text-xs text-gray-500">
                    {doc.num_chunks} chunks · {new Date(doc.uploaded_at).toLocaleDateString()}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span
                  className={`text-xs px-2 py-0.5 rounded-full ${
                    STATUS_COLORS[doc.status] || "bg-gray-700 text-gray-400"
                  }`}
                >
                  {doc.status}
                </span>
                <button
                  onClick={() => handleDelete(doc.id, doc.filename)}
                  className="text-gray-600 hover:text-red-400 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h2 className="text-sm font-medium text-gray-400 mb-3">Test RAG Retrieval</h2>
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleQuery()}
            placeholder="Ask anything about your documents..."
            className="input flex-1"
          />
          <button onClick={handleQuery} className="btn-primary flex items-center gap-2">
            <Search className="w-4 h-4" /> Search
          </button>
        </div>
        {queryResults.length > 0 && (
          <div className="mt-3 space-y-3">
            {queryResults.map((r, i) => (
              <div key={i} className="card border-brand-800">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-brand-400">{r.source}</span>
                  <span className="text-xs text-gray-600">Score: {r.score.toFixed(3)}</span>
                </div>
                <p className="text-sm text-gray-300 leading-relaxed">{r.text}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
