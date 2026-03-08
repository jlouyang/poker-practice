/**
 * Toast notification system for transient error/info messages.
 *
 * ToastContainer renders a stack of toasts in the top-right corner.
 * Each toast auto-dismisses after 5 seconds, or can be clicked to dismiss.
 * Uses aria-live="polite" for screen reader announcements.
 */
import { useEffect } from "react";

export interface ToastMessage {
  id: number;
  text: string;
  type: "error" | "info";
}

interface ToastContainerProps {
  toasts: ToastMessage[];
  onDismiss: (id: number) => void;
}

export default function ToastContainer({ toasts, onDismiss }: ToastContainerProps) {
  if (toasts.length === 0) return null;

  return (
    <div className="toast-container" aria-live="polite">
      {toasts.map((t) => (
        <ToastItem key={t.id} toast={t} onDismiss={onDismiss} />
      ))}
    </div>
  );
}

function ToastItem({ toast, onDismiss }: { toast: ToastMessage; onDismiss: (id: number) => void }) {
  useEffect(() => {
    const timer = setTimeout(() => onDismiss(toast.id), 5000);
    return () => clearTimeout(timer);
  }, [toast.id, onDismiss]);

  return (
    <div
      className={`toast toast-${toast.type}`}
      onClick={() => onDismiss(toast.id)}
      role="alert"
    >
      {toast.text}
    </div>
  );
}
