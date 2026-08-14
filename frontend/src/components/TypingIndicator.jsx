import logo from "../assets/logo.png";

export default function TypingIndicator() {
  return (
    <div className="typing-row">
      <img className="assistant-avatar" src={logo} alt="AI" />
      <div className="typing-dots">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
      </div>
    </div>
  );
}
