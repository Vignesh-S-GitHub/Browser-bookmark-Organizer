import { env, pipeline } from "@huggingface/transformers";

type BookmarkInput = {
  id: number;
  title: string;
  url: string;
  description: string | null;
};

type WorkerRequest = {
  id: string;
  modelId: string;
  bookmarks: BookmarkInput[];
};

type TextGenerator = (
  input: string,
  options: Record<string, unknown>,
) => Promise<Array<{ generated_text?: string | Array<{ role: string; content: string }> }>>;

env.allowLocalModels = false;
env.useBrowserCache = true;

let loadedModelId = "";
let generator: TextGenerator | null = null;

function post(id: string, payload: Record<string, unknown>) {
  self.postMessage({ id, ...payload });
}

self.onmessage = async (event: MessageEvent<WorkerRequest>) => {
  const { id, modelId, bookmarks } = event.data;

  try {
    post(id, { type: "status", message: "Loading local model. First run downloads to browser cache." });

    if (!generator || loadedModelId !== modelId) {
      generator = await loadGenerator(modelId);
      loadedModelId = modelId;
    }

    post(id, { type: "status", message: "Running local LLM analysis." });

    const prompt = buildPrompt(bookmarks);
    const output = await generator(prompt, {
      max_new_tokens: 700,
      temperature: 0.2,
      do_sample: false,
      return_full_text: false,
    });

    post(id, {
      type: "result",
      text: readGeneratedText(output),
    });
  } catch (error) {
    post(id, {
      type: "error",
      message: error instanceof Error ? error.message : "Local LLM failed",
    });
  }
};

async function loadGenerator(modelId: string) {
  try {
    return (await pipeline("text-generation", modelId, {
      dtype: "q4f16",
      device: "webgpu",
    })) as TextGenerator;
  } catch {
    return (await pipeline("text-generation", modelId, {
      dtype: "q4",
      device: "wasm",
    })) as TextGenerator;
  }
}

function buildPrompt(bookmarks: BookmarkInput[]) {
  return `You organize browser bookmarks.
Return ONLY valid JSON. No markdown.
Schema:
{"items":[{"id":number,"category":"short folder name","tags":["tag1","tag2","tag3"],"summary":"one short sentence"}]}

Rules:
- Use practical folder names like Development, Design, AI, Learning, Tools, Shopping, Reading, News.
- Keep tags lowercase and short.
- Do not invent URLs.

Bookmarks:
${JSON.stringify(bookmarks, null, 2)}
`;
}

function readGeneratedText(output: Awaited<ReturnType<TextGenerator>>) {
  const first = output[0]?.generated_text;
  if (Array.isArray(first)) {
    return first.map((message) => message.content).join("\n");
  }
  return first || "";
}
