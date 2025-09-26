import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { CopilotKit } from "@copilotkit/react-core";
import { LEARNING_AGENT_KEY } from "@/components/copilot/types";
import "@copilotkit/react-ui/styles.css";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Learning Agent",
  description: "AI-powered deep agent system",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className={inter.className}>
        <CopilotKit runtimeUrl="/api/copilotkit" agent={LEARNING_AGENT_KEY} showDevConsole={false}>
          {children}
        </CopilotKit>
      </body>
    </html>
  );
}
