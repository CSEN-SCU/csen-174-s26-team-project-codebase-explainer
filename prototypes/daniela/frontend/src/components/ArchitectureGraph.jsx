import cytoscape from "cytoscape";
import dagre from "cytoscape-dagre";
import { useEffect, useRef } from "react";

cytoscape.use(dagre);

const TYPE_COLORS = {
  entrypoint: "#1d4ed8",
  module: "#15803d",
  service: "#7c3aed",
  config: "#b45309",
  external: "#be123c",
  database: "#0369a1",
  test: "#4d7c0f",
};

function typeColor(t) {
  return TYPE_COLORS[String(t || "").toLowerCase()] || "#57534e";
}

export default function ArchitectureGraph({ nodes, edges, onSelectNode }) {
  const hostRef = useRef(null);
  const cyRef = useRef(null);

  useEffect(() => {
    const el = hostRef.current;
    if (!el || !nodes?.length) {
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
      return;
    }

    const elements = [];
    nodes.forEach((n) => {
      elements.push({
        data: {
          id: n.id,
          label: n.label,
          type: n.type,
          description: n.description,
          files: n.files || [],
          color: typeColor(n.type),
        },
      });
    });
    (edges || []).forEach((e, i) => {
      elements.push({
        data: {
          id: `e${i}`,
          source: e.source,
          target: e.target,
          label: e.label || "",
        },
      });
    });

    if (cyRef.current) {
      cyRef.current.destroy();
      cyRef.current = null;
    }

    const cy = cytoscape({
      container: el,
      elements,
      style: [
        {
          selector: "node",
          style: {
            "background-color": "data(color)",
            label: "data(label)",
            color: "#fafaf9",
            "font-size": "11px",
            "font-weight": "600",
            "text-valign": "center",
            "text-halign": "center",
            "text-wrap": "wrap",
            "text-max-width": "110px",
            "text-outline-color": "data(color)",
            "text-outline-width": "2px",
            shape: "round-rectangle",
            width: "label",
            height: "label",
            padding: "12px",
            "border-width": "2px",
            "border-color": "#d6d3d1",
          },
        },
        { selector: "node:selected", style: { "border-color": "#0f172a", "border-width": "3px" } },
        { selector: "node.highlighted", style: { "border-color": "#0f172a", "border-width": "3px" } },
        { selector: "node.dimmed", style: { opacity: 0.2 } },
        {
          selector: "edge",
          style: {
            width: 2,
            "line-color": "#a8a29e",
            "target-arrow-color": "#a8a29e",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            label: "data(label)",
            "font-size": "9px",
            color: "#57534e",
            "text-background-color": "#fafaf9",
            "text-background-opacity": 1,
            "text-background-padding": "2px",
            "edge-text-rotation": "autorotate",
            opacity: 0.88,
          },
        },
        {
          selector: "edge.highlighted",
          style: {
            "line-color": "#14532d",
            "target-arrow-color": "#14532d",
            opacity: 1,
            width: 2.5,
          },
        },
        { selector: "edge.dimmed", style: { opacity: 0.05 } },
      ],
      layout: {
        name: "dagre",
        rankDir: "TB",
        rankSep: 88,
        nodeSep: 54,
        edgeSep: 10,
        animate: true,
        animationDuration: 450,
        fit: true,
        padding: 52,
      },
      userZoomingEnabled: true,
      userPanningEnabled: true,
      boxSelectionEnabled: false,
    });

    cy.on("tap", "node", (evt) => {
      const node = evt.target;
      const d = node.data();
      cy.elements().removeClass("highlighted dimmed");
      const nbhd = node.closedNeighborhood();
      cy.elements().not(nbhd).addClass("dimmed");
      nbhd.addClass("highlighted");
      onSelectNode?.(d);
    });

    cy.on("tap", (evt) => {
      if (evt.target === cy) {
        cy.elements().removeClass("highlighted dimmed");
        onSelectNode?.(null);
      }
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [nodes, edges, onSelectNode]);

  if (!nodes?.length) {
    return (
      <div
        style={{
          padding: "2rem",
          textAlign: "center",
          color: "var(--ink-soft)",
          border: "1px dashed var(--ridge)",
          borderRadius: "12px",
          background: "linear-gradient(165deg, #faf7f0, #f0ebe3)",
        }}
      >
        No graph nodes returned. Try re-analyzing or pick another repository.
      </div>
    );
  }

  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        height: "100%",
        minHeight: "280px",
        background: "linear-gradient(165deg, #faf7f0, #f0ebe3)",
        borderRadius: "12px",
        border: "1px solid var(--ridge)",
        overflow: "hidden",
      }}
    >
      <div
        ref={hostRef}
        style={{ width: "100%", height: "100%", minHeight: "320px" }}
      />
      <div
        style={{
          position: "absolute",
          bottom: "10px",
          left: "10px",
          fontSize: "0.68rem",
          color: "var(--ink-soft)",
          background: "rgba(255,252,247,0.92)",
          border: "1px solid var(--ridge)",
          padding: "0.45rem 0.55rem",
          borderRadius: "8px",
          pointerEvents: "none",
          maxWidth: "min(90%, 220px)",
        }}
      >
        Scroll to zoom · drag to pan · click a node
      </div>
    </div>
  );
}
