import { useRef } from "react";

export default function ResizableSidebar({
  width,
  setWidth,
  minWidth = 300,
  maxWidth = 520,
  children,
  className = "",
}) {
  const dragging = useRef(false);

  const handleMouseDown = (e) => {
    e.preventDefault();
    dragging.current = true;

    const handleMouseMove = (event) => {
      if (!dragging.current) return;

      const newWidth = Math.min(
        maxWidth,
        Math.max(minWidth, event.clientX)
      );

      setWidth(newWidth);
    };

    const handleMouseUp = () => {
      dragging.current = false;

      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);

      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);

    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  };

  return (
    <>
      <aside className={`resizable-sidebar ${className}`}>
        {children}
      </aside>

      <div
        className="sidebar-resizer"
        onMouseDown={handleMouseDown}
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize sidebar"
      >
        <span />
      </div>
    </>
  );
}