import React from "react";

/**
 * Card component with lilac/purple accent, shadow, rounded corners
 */
export function Card({ children, accentColor = "#8b5cf6", style = {} }) {
  const cardStyle = {
    backgroundColor: "#fff",
    borderLeft: `6px solid ${accentColor}`,
    borderRadius: "16px",
    boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
    overflow: "hidden",
    ...style, // allow additional custom styles
  };

  return <div style={cardStyle}>{children}</div>;
}

/**
 * CardContent wraps inner content of a card
 */
export function CardContent({ children, style = {} }) {
  const contentStyle = {
    display: "flex",
    alignItems: "center",
    gap: "16px",
    padding: "20px",
    ...style,
  };

  return <div style={contentStyle}>{children}</div>;
}
