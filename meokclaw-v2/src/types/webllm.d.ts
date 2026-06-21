declare module "@mlc-ai/web-llm" {
  export interface ChatCompletionMessageParam {
    role: "user" | "assistant" | "system";
    content: string;
  }
  export interface ChatCompletionChunk {
    choices: Array<{
      delta: { content?: string };
    }>;
  }
  export interface MLCEngine {
    chat: {
      completions: {
        create(params: {
          messages: ChatCompletionMessageParam[];
          temperature?: number;
          max_tokens?: number;
          stream?: boolean;
        }): Promise<any>;
      };
    };
  }
  export function CreateMLCEngine(
    modelId: string,
    options?: {
      initProgressCallback?: (report: { progress: number; text: string }) => void;
    }
  ): Promise<MLCEngine>;
}

declare global {
  interface Navigator {
    gpu?: any;
  }
}
