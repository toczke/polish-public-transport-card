import "./editor.js";
import { MzkzgTransportCard } from "./card.js";
import { MZKZG_VERSION } from "./utils.js";

// Register Custom Elements
if (!customElements.get("mzkzg-transport-card")) {
  customElements.define("mzkzg-transport-card", MzkzgTransportCard);
}
if (!customElements.get("polish-transport-card")) {
  customElements.define("polish-transport-card", class extends MzkzgTransportCard {});
}

// Add to Home Assistant Custom Cards Registry
window.customCards = window.customCards || [];
window.customCards.push({
  type: "polish-transport-card",
  name: "Polish Transport Card",
  description: "Tablica odjazdów polskiej komunikacji miejskiej (dane z integracji mzkzg_transport)",
  preview: true,
  documentationURL: "https://github.com/toczke/polish-public-transport-card",
});

// Print version to console
console.info(
  `%c MZKZG-TRANSPORT %c v${MZKZG_VERSION} `,
  "background:#005eb8;color:#fff;padding:2px 6px;border-radius:4px 0 0 4px;font-weight:bold",
  "background:#1f2937;color:#fff;padding:2px 6px;border-radius:0 4px 4px 0"
);
