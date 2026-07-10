import { eq } from "drizzle-orm";
import { knowledgeArticles } from "@db/schema";
import type { KnowledgeArticle } from "@db/schema";
import { getDb } from "./connection";

const STOPWORDS = new Set([
  "a","o","as","os","de","da","do","das","dos","e","em","um","uma","para",
  "com","por","que","como","meu","minha","the","to","of","is","and","how",
  "no","na","nos","nas","se","ao","à","é","ou","sobre","qual","quais",
]);

function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9\s]/g, " ")
    .split(/\s+/)
    .filter((w) => w.length > 2 && !STOPWORDS.has(w));
}

/**
 * Find the published KB article most relevant to a free-text message using a
 * simple keyword-overlap score. Returns null when nothing meaningful matches.
 */
export async function findRelevantArticle(
  message: string,
): Promise<KnowledgeArticle | null> {
  const terms = tokenize(message);
  if (terms.length === 0) return null;

  const articles = await getDb()
    .select()
    .from(knowledgeArticles)
    .where(eq(knowledgeArticles.status, "published"));

  let best: { article: KnowledgeArticle; score: number } | null = null;
  for (const article of articles) {
    const haystack = tokenize(
      `${article.title} ${article.summary ?? ""} ${article.tags ?? ""} ${article.content}`,
    );
    const hay = new Set(haystack);
    let score = 0;
    for (const t of terms) if (hay.has(t)) score += 1;
    if (score > 0 && (!best || score > best.score)) {
      best = { article, score };
    }
  }

  // Require at least two overlapping keywords to avoid weak matches.
  return best && best.score >= 2 ? best.article : null;
}
