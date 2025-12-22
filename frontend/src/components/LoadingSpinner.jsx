import React from "react";

const LoadingSpinner = () => (
  <div style={{ textAlign: "center", padding: "20px" }}>
    <div className="spinner" />
    <p>Loading...</p>
    <style>
      {`
        .spinner {
          border: 4px solid #f3f3f3;
          border-top: 4px solid #1f2937;
          border-radius: 50%;
          width: 24px;
          height: 24px;
          animation: spin 1s linear infinite;
          margin: 0 auto;
        }
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}
    </style>
  </div>
);

export default LoadingSpinner;
