import type { MetadataRoute } from "next";
import { getBooks } from "@/lib/api";
import { absoluteUrl } from "@/lib/site";

export const dynamic = "force-dynamic";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const books = await getBooks();
  const routes: MetadataRoute.Sitemap = [
    { url: absoluteUrl("/"), changeFrequency: "weekly", priority: 1 },
  ];
  for (const book of books) {
    routes.push({
      url: absoluteUrl(`/books/${book.slug}`),
      changeFrequency: book.available === false ? "monthly" : "weekly",
      priority: book.available === false ? 0.3 : 0.8,
    });
    if (book.available === false) continue;
    for (const chapter of book.chapters ?? []) {
      routes.push({
        url: absoluteUrl(`/books/${book.slug}/${chapter.order}`),
        changeFrequency: "monthly",
        priority: 0.7,
      });
    }
  }
  return routes;
}
