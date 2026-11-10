import type { Metadata } from "next";
import "./globals.css";
import "./visual-theme.css";

// Métadonnées de l'onglet du navigateur communes à toutes les pages.
export const metadata: Metadata = {
  title: "Life EPM — Église Pentecôte Missionnaire",
  description: "Plateforme de gestion de l'Église Pentecôte Missionnaire.",
};

// Conteneur HTML racine ; les styles globaux sont chargés ici une seule fois.
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
