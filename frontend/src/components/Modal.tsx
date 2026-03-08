/**
 * Accessible modal dialog component.
 *
 * Features:
 *   - role="dialog", aria-modal, aria-labelledby for screen readers
 *   - Focus trap: Tab cycles within the modal, Shift+Tab goes backwards
 *   - Escape key closes the modal
 *   - Click on overlay (outside panel) closes the modal
 *   - Saves and restores focus to the previously focused element
 *   - Auto-focuses the first focusable element on open
 */
import { useEffect, useRef, useCallback, type ReactNode } from "react";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  maxWidth?: number;
  /** ID used for aria-labelledby; auto-generated if omitted */
  titleId?: string;
}

export default function Modal({ open, onClose, title, children, maxWidth = 600, titleId }: ModalProps) {
  const overlayRef = useRef<HTMLDivElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const previousFocus = useRef<HTMLElement | null>(null);
  const id = titleId ?? "modal-title";

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key === "Tab" && panelRef.current) {
        const focusable = panelRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    },
    [onClose]
  );

  useEffect(() => {
    if (!open) return;
    previousFocus.current = document.activeElement as HTMLElement;
    document.addEventListener("keydown", handleKeyDown);

    requestAnimationFrame(() => {
      const firstFocusable = panelRef.current?.querySelector<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      firstFocusable?.focus();
    });

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      previousFocus.current?.focus();
    };
  }, [open, handleKeyDown]);

  if (!open) return null;

  return (
    <div
      ref={overlayRef}
      className="modal-overlay"
      onClick={(e) => { if (e.target === overlayRef.current) onClose(); }}
      role="dialog"
      aria-modal="true"
      aria-labelledby={id}
    >
      <div ref={panelRef} className="modal-panel" style={{ maxWidth }}>
        <div className="modal-header">
          <h2 id={id} className="modal-title">{title}</h2>
          <button onClick={onClose} className="btn-close" aria-label="Close dialog">
            Close
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
