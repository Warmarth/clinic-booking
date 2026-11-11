export default function Message({ message }) {
  if (!message) return null;

  return <div className={message.ok ? "msg ok" : "msg bad"}>{message.text}</div>;
}
