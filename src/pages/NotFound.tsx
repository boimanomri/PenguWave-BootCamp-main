import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div style={{ textAlign: "center", padding: "80px 20px" }}>
      <pre style={{ fontSize: 14, lineHeight: 1.3, display: "inline-block", textAlign: "left" }}>
{`
       .--.
      |o_o |
      |:_/ |
     //   \\ \\
    (|     | )
   /'\\_   _/\`\\
   \\___)=(___/
`}
      </pre>
      <h1 style={{ fontSize: 48, margin: "20px 0 10px", color: "#333" }}>404</h1>
      <p style={{ fontSize: 18, color: "#666", marginBottom: 8 }}>
        This penguin got lost at sea 🐧
      </p>
      <p style={{ color: "#999", marginBottom: 30 }}>
        The page you're looking for doesn't exist or has been moved.
      </p>
      <Link to="/events" style={{ color: "#0066cc" }}>
        ← Back to shore
      </Link>
    </div>
  );
}
