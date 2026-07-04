// Clean display names — the catalog `title` field holds the source document
// title (provenance), not a human-facing book name. Centralized so both the
// library and book pages use the same mapping.
export function displayName(slug: string): string {
  const names: Record<string, string> = {
    "da-xue": "Da Xue 大學",
    "zhong-yong": "Zhong Yong 中庸",
    lunyu: "Lunyu 論語",
    mengzi: "Mengzi 孟子",
    daodejing: "Daodejing 道德經",
    "sunzi-bingfa": "Sunzi Bingfa 孫子兵法",
    "san-zi-jing": "San Zi Jing 三字經",
    "qian-zi-wen": "Qian Zi Wen 千字文",
    "sanguo-yanyi": "Sanguo Yanyi 三國演義",
    "chengyu-catalog": "Chengyu Catalog 成語目錄",
  };
  return names[slug] ?? slug;
}
