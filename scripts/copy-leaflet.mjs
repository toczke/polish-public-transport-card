import { cpSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = fileURLToPath(new URL(".", import.meta.url));
const root = dirname(scriptDir);
const source = join(root, "node_modules", "leaflet", "dist");
const target = join(root, "custom_components", "mzkzg_transport", "www", "leaflet");

mkdirSync(target, { recursive: true });
for (const file of ["leaflet.js", "leaflet.css"]) {
  cpSync(join(source, file), join(target, file));
}
cpSync(join(source, "images"), join(target, "images"), { recursive: true });
cpSync(join(root, "node_modules", "leaflet", "LICENSE"), join(target, "LICENSE"));

console.log(`Copied Leaflet assets to ${target}`);
