import { ChatbotEditor } from "@/components/app/chatbots/chatbot-editor";

export default async function ChatbotPage({ params }: { params: Promise<{ agentId: string }> }) {
  const { agentId } = await params;
  return <ChatbotEditor agentId={agentId} />;
}
