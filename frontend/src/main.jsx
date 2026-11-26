import React from "react";
import ReactDOM from "react-dom/client";
import "./styles.css";


function App() {
  return (
    <main>
      <h1>Urban Air Quality Assistant</h1>
      <p>Setup complete. AQI and personalized advice will appear here.</p>
    </main>
  );
}


ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
