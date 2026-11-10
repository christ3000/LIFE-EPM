import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Life EPM — Église Pentecôte Missionnaire",
    short_name: "Life EPM",
    description: "Gestion de l'Église Pentecôte Missionnaire.",
    start_url: "/",
    display: "standalone",
    background_color: "#f5f8fc",
    theme_color: "#1769aa",
    lang: "fr-CI",
    icons: [{ src: "/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" }],
  };
}
