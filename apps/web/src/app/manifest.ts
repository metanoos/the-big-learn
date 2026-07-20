import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "The Big Learn",
    short_name: "Big Learn",
    description: "A line-by-line reader for classical Chinese texts.",
    start_url: "/",
    display: "standalone",
    background_color: "#fafaf9",
    theme_color: "#b45309",
  };
}
