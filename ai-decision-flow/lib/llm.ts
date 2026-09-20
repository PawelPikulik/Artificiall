import OpenAI from "openai";

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

export async function askLLM(prompt: string): Promise<"YES" | "NO"> {
  const response = await openai.chat.completions.create({
    model: "gpt-4o-mini",
    messages: [
      {
        role: "system",
        content:
          "You are a strict binary classifier. Respond with ONLY the word YES or NO. No explanation, no punctuation, no extra text.",
      },
      {
        role: "user",
        content: prompt,
      },
    ],
    temperature: 0,
    max_tokens: 5,
  });

  const raw = response.choices[0].message.content?.trim().toUpperCase() ?? "NO";
  if (raw.startsWith("YES")) return "YES";
  return "NO";
}
