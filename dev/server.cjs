const http = require("http");
const fs = require("fs");
const path = require("path");

const PORT = 8095;
const MIME = { ".html": "text/html", ".js": "application/javascript", ".css": "text/css" };

http.createServer((req, res) => {
  const file = req.url === "/" ? "/dev/index.html" : req.url;
  const filePath = path.join(__dirname, "..", file);
  const ext = path.extname(filePath);
  fs.readFile(filePath, (err, data) => {
    if (err) { res.writeHead(404); res.end("Not found"); return; }
    res.writeHead(200, { "Content-Type": MIME[ext] || "text/plain" });
    res.end(data);
  });
}).listen(PORT, () => console.log(`Dev server: http://localhost:${PORT}`));
