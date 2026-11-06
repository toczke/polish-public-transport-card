import { escapeHtml, routeColor, parseVehiclePosition, t } from "./utils.js";

let leafletLoadPromise = null;
let leafletCssPromise = null;

export class VehicleMap {
  constructor(card) { this.card = card; }
  destroy() {
    if (this.mapCtx) this.mapCtx.destroy();
  }

  ensureLeafletCss() {
    // HA loads Leaflet JS globally on some dashboards, but not necessarily its
    // stylesheet. Without the CSS, tiles have `position: static` and the map
    // renders as offset/checkerboard squares.
    if (leafletCssPromise) return leafletCssPromise;
    leafletCssPromise = new Promise((resolve) => {
      const existing = document.getElementById("polish-transport-leaflet-css");
      if (existing) {
        if (existing.sheet) {
          resolve();
          return;
        }
        existing.addEventListener("load", () => resolve(), { once: true });
        existing.addEventListener("error", () => resolve(), { once: true });
        return;
      }
      const link = document.createElement("link");
      link.id = "polish-transport-leaflet-css";
      link.rel = "stylesheet";
      link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
      link.addEventListener("load", () => resolve(), { once: true });
      link.addEventListener("error", () => resolve(), { once: true });
      document.head.appendChild(link);
    });
    return leafletCssPromise;
  }

  preloadLeaflet() {
    // Share one loader across every card on the dashboard instead of injecting
    // duplicate Leaflet stylesheets/scripts per card.
    if (leafletLoadPromise) return leafletLoadPromise;

    leafletLoadPromise = this.ensureLeafletCss().then(() => {
      if (window.L) return window.L;
      return new Promise((resolve, reject) => {
        let script = document.getElementById("polish-transport-leaflet-js");
        if (!script) {
          script = document.createElement("script");
          script.id = "polish-transport-leaflet-js";
          script.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
          document.head.appendChild(script);
        }
        const onLoad = () => {
          script.removeEventListener("error", onError);
          resolve(window.L);
        };
        const onError = () => {
          script.removeEventListener("load", onLoad);
          script.remove();
          leafletLoadPromise = null;
          reject(new Error("Failed to load Leaflet"));
        };
        script.addEventListener("load", onLoad, { once: true });
        script.addEventListener("error", onError, { once: true });
      });
    });
    return leafletLoadPromise;
  }

  buildVehicleMarker(bearing, color, route, vehicleType, info, isMobile) {
    const size = isMobile ? 32 : 40;
    const fontSize = isMobile ? 11 : 13;
    const pad = 5;
    const box = size + pad * 2;
    const center = box / 2;
    const radius = size / 2 - 2;
    const tip = radius + 5;
    const halfBase = 6;
    // A clean circular puck centred on the vehicle, with a small direction
    // pointer drawn inside the padded viewBox. The old bottom pointer rotated
    // around the circle centre and could be clipped into a stray sliver.
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${box}" height="${box}" viewBox="0 0 ${box} ${box}">
      <g transform="rotate(${bearing}, ${center}, ${center})">
        <path d="M${center},${center - tip} L${center - halfBase},${center - radius + 2} L${center + halfBase},${center - radius + 2} Z" fill="${color}" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/>
      </g>
      <circle cx="${center}" cy="${center}" r="${radius}" fill="${color}" stroke="#fff" stroke-width="2"/>
      <text x="${center}" y="${center}" text-anchor="middle" dominant-baseline="central" font-weight="700" font-size="${fontSize}" fill="#fff" font-family="system-ui,sans-serif">${escapeHtml(route)}</text>
    </svg>`;

    return { svg, size: box };
  }

  buildPopupContent(d) {
    const delay = Math.round((d.delay_seconds || 0) / 60);
    const delayTag = delay > 0 ? `+${delay} min` : delay < 0 ? `${delay} min` : t("on_time");
    const delayClass = delay > 0 ? "zm-popup-delay" : delay < 0 ? "zm-popup-delay early" : "zm-popup-delay ontime";
    return `<div class="zm-popup"><div class="zm-popup-route">${escapeHtml(d.route)}</div>${d.headsign ? `<div class="zm-popup-headsign">→ ${escapeHtml(d.headsign)}</div>` : ""}${d.vehicle_code ? `<div class="zm-popup-meta">#${escapeHtml(d.vehicle_code)}</div>` : ""}<div class="zm-popup-delay-row"><span class="${delayClass}">${escapeHtml(delayTag)}</span></div></div>`;
  }

  showVehicleMap(lat, lng, info) {
    if (this.mapCtx) { this.mapCtx.destroy(); }

    const isMobile = window.innerWidth < 480;
    const w = Math.min(window.innerWidth * 0.92, 520);
    const h = Math.min(window.innerHeight * 0.65, 420);
    const dark = this._isDarkTheme();

    const overlay = document.createElement("div");
    if (dark) overlay.classList.add("zm-dark");
    overlay.style.cssText = "position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:100000;display:flex;align-items:center;justify-content:center;";
    overlay.innerHTML = `<div style="position:relative;width:${w}px;height:${h}px;background:${dark ? "#1c1c1e" : "#fff"};border-radius:12px;overflow:hidden;box-shadow:0 8px 32px rgba(0,0,0,0.3);"><button style="position:absolute;top:8px;right:8px;z-index:1001;background:rgba(0,0,0,0.6);border:none;border-radius:50%;width:32px;height:32px;cursor:pointer;font-size:16px;display:flex;align-items:center;justify-content:center;color:#fff;">✕</button><div id="vmap" style="width:${w}px;height:${h}px;background:${dark ? "#1c1c1e" : "#fff"};"></div><div id="vmap-status" class="zm-map-status">${escapeHtml(t("map_refresh"))}</div></div>`;
    document.body.appendChild(overlay);
    const closeMap = () => { if (this.mapCtx) this.mapCtx.destroy(); };
    overlay.querySelector("button").onclick = closeMap;
    overlay.onclick = (e) => { if (e.target === overlay) closeMap(); };

    const container = overlay.querySelector("#vmap");

    if (!document.getElementById("ztm-map-style")) {
      const s = document.createElement("style");
      s.id = "ztm-map-style";
      s.textContent = `.zm-arrow{position:relative;display:inline-block;transition:transform 0.8s ease}.zm-arrow svg{display:block}.zm-map-status{position:absolute;bottom:6px;left:10px;z-index:1001;font-size:10px;color:#999;background:rgba(255,255,255,0.8);padding:2px 6px;border-radius:4px}.zm-popup{font-family:system-ui,sans-serif;font-size:11px;line-height:1.25;min-width:0;max-width:180px}.zm-popup-route{font-size:17px;font-weight:800;line-height:1}.zm-popup-headsign{font-size:12px;color:#555;margin-top:2px}.zm-popup-meta{font-size:10px;color:#999;margin-top:1px}.zm-popup-delay-row{margin-top:3px;font-size:12px;font-weight:600}.zm-popup-delay{color:#e53935}.zm-popup-delay.ontime{color:#43a047}.zm-popup-delay.early{color:#1e88e5}.zm-dark .zm-map-status{background:rgba(0,0,0,0.62);color:#ddd}.zm-dark-map .leaflet-tile-pane{filter:invert(1) hue-rotate(180deg) brightness(0.9) contrast(0.9)}.zm-dark-map .leaflet-popup-content-wrapper,.zm-dark-map .leaflet-popup-tip{background:#1c1c1e;color:#eee}.zm-dark-map .leaflet-popup-close-button{color:#eee}.zm-dark-map .leaflet-control-zoom a{background:#1c1c1e;color:#eee;border-color:#333}.zm-dark-map .leaflet-control-zoom a:hover{background:#2a2a2e}.zm-dark-map .leaflet-control-attribution{background:rgba(0,0,0,0.6);color:#bbb}.zm-dark-map .leaflet-control-attribution a{color:#8ab4f8}.zm-dark-map .zm-popup-headsign{color:#bbb}.zm-dark-map .zm-popup-meta{color:#888}`;
      document.head.appendChild(s);
    }

    const ctx = {
      destroyed: false,
      map: null,
      interval: null,
      ro: null,
      markers: [],
      overlay: overlay,
      onKeyDown: null,
      destroy: () => {
        ctx.destroyed = true;
        if (ctx.interval) clearInterval(ctx.interval);
        if (ctx.ro) ctx.ro.disconnect();
        if (ctx.map) { ctx.map.remove(); ctx.map = null; }
        if (ctx.onKeyDown) { document.removeEventListener("keydown", ctx.onKeyDown); ctx.onKeyDown = null; }
        if (ctx.overlay && ctx.overlay.parentNode) ctx.overlay.parentNode.removeChild(ctx.overlay);
        if (this.mapCtx === ctx) this.mapCtx = null;
      },
      entityId: info.entityId,
      vehicleCode: info.code,
    };
    this.mapCtx = ctx;

    // Wire Escape after ctx exists; referencing ctx before its declaration throws
    // a temporal-dead-zone ReferenceError and leaves the overlay unclosable.
    ctx.onKeyDown = (e) => { if (e.key === "Escape") closeMap(); };
    document.addEventListener("keydown", ctx.onKeyDown);

    const color = routeColor(info.route, info.provider || "", info.route_color);

    const createMap = () => {
      requestAnimationFrame(() => {
        if (ctx.destroyed) return;
        const map = window.L.map(container, { zoomControl: true }).setView([lat, lng], 16);
        if (this._isDarkTheme()) container.classList.add("zm-dark-map");
        this.addTileLayer(map, ctx);
        const attributionPrefix = map.attributionControl.options.prefix;
        if (attributionPrefix) map.attributionControl.setPrefix(attributionPrefix.replace(/<a /g, '<a target="_blank" rel="noopener" '));
        ctx.map = map;

        // Stop location marker
        window.L.circleMarker([lat, lng], { radius: 5, fillColor: color, fillOpacity: 0.5, color: "#fff", weight: 2 }).addTo(map);

        // Show all vehicles with GPS from this entity
        this.renderAllVehicleMarkers(ctx, info, isMobile);
        // Keep the selected vehicle centred at a readable zoom. The old
        // fitBounds call zoomed out and pushed the selected marker off-centre.
        const focus = ctx.marker?.getLatLng();
        map.setView(focus || [lat, lng], 16, { animate: false });

        // Fetch polyline shape for ZTM Gdańsk
        if (info.provider === "ztm_gdansk" && info.route_id_int && info.trip_id) {
          const today = new Date().toISOString().split("T")[0];
          const shapeUrl = `https://ckan2.multimediagdansk.pl/shapes?date=${today}&routeId=${info.route_id_int}&tripId=${info.trip_id}`;
          fetch(shapeUrl)
            .then(r => r.json())
            .then(data => {
              if (ctx.destroyed || !ctx.map) return;
              if (data && data.coordinates && Array.isArray(data.coordinates)) {
                const latlngs = data.coordinates.map(c => [c[1], c[0]]);
                const shapeColor = routeColor(info.route, info.provider) || "#e53935";
                window.L.polyline(latlngs, {color: shapeColor, weight: 4, opacity: 0.8}).addTo(ctx.map);
                
                // Add tiny markers for each stop in the shape (optional, let's keep it simple and just draw the line)
              }
            }).catch(e => console.warn("Failed to load shape for Gdańsk:", e));
        }

        ctx.ro = new window.ResizeObserver(() => { if (ctx.map) ctx.map.invalidateSize(); });
        ctx.ro.observe(container);
        ctx.interval = setInterval(() => this.updateAllVehiclePositions(ctx), 30000);

      });
    };

    // Always go through preloadLeaflet: it also guarantees the Leaflet CSS is
    // loaded, even when HA already provided the global `L` object.
    this.preloadLeaflet().then(createMap).catch(() => ctx.destroy());
  }

  async addTileLayer(map, ctx) {
    // CARTO's raster basemaps now require an API key. Use OpenStreetMap, proxied
    // through HA's map_tiles integration on 2026.9+ (otherwise direct with Referer).
    const fetchToken = () => this.card.hass.callWS({ type: "map_tiles/access_token" }).then(r => r?.token || null, () => null);
    let token;
    try { token = await fetchToken(); } catch { token = null; }
    if (ctx.destroyed) return;
    const origin = (this.card.hass.auth?.data?.hassUrl || location.origin).replace(/\/+$/, "");
    const proxyUrl = (t) => `${origin}/api/map_tiles/raster/{z}/{x}/{y}.png?token=${encodeURIComponent(t)}`;
    const layer = window.L.tileLayer(token ? proxyUrl(token) : "https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors',
      referrerPolicy: token ? undefined : "strict-origin-when-cross-origin",
    }).addTo(map);
    if (!token) return;
    let lastRefresh = 0;
    layer.on("tileerror", async () => {
      if (Date.now() - lastRefresh < 30000) return;
      lastRefresh = Date.now();
      const fresh = await fetchToken();
      if (fresh && !ctx.destroyed) layer.setUrl(proxyUrl(fresh));
    });
  }

  _isDarkTheme() {
    const probe = document.createElement("div");
    probe.style.color = "var(--card-background-color, #fff)";
    document.body.appendChild(probe);
    const color = getComputedStyle(probe).color;
    probe.remove();
    const parts = color.match(/\d+/g);
    if (!parts) return false;
    const [r, g, b] = parts.map(Number);
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) < 128;
  }

  _spreadPosition(pos, groups) {
    const key = `${pos[0].toFixed(4)}|${pos[1].toFixed(4)}`;
    const index = groups[key] || 0;
    groups[key] = index + 1;
    if (index === 0) return pos;
    const angle = (index * 137.5) * Math.PI / 180;
    const radius = 0.00013 * Math.ceil(index / 4);
    return [pos[0] + Math.sin(angle) * radius, pos[1] + Math.cos(angle) * radius];
  }

  _createVehicleMarker(ctx, d, pos, isMobile) {
    const isMain = Boolean(d.vehicle_code && d.vehicle_code === ctx.vehicleCode);
    const color = routeColor(d.route, d._provider || d.provider || "", d.route_color);
    const bearing = d.vehicle_direction || d.direction || 0;
    const mk = this.buildVehicleMarker(bearing, color, d.route || "?", d.vehicle_type || "bus", d, isMobile);
    const mkHtml = `<div class="zm-arrow" style="opacity:${isMain ? 1 : 0.72}">${mk.svg}</div>`;
    const icon = window.L.divIcon({
      className: "",
      html: mkHtml,
      iconSize: [mk.size, mk.size],
      iconAnchor: [mk.size / 2, mk.size / 2],
    });
    const marker = window.L.marker(pos, {
      icon,
      title: `${d.route || "?"} ${d.headsign || ""}`.trim(),
      zIndexOffset: isMain ? 1000 : 0,
    }).addTo(ctx.map);
    marker.bindPopup(this.buildPopupContent(d), { closeButton: true, autoPan: true, maxWidth: 200 });
    // Leaflet's default click toggles the popup off, which used to leave only
    // the tiny hover tooltip. Rebind the click so it always opens the same
    // compact popup, and drop the separate tooltip entirely.
    marker.off("click");
    marker.on("click", (e) => {
      if (e.originalEvent) window.L.DomEvent.stopPropagation(e.originalEvent);
      marker.openPopup();
    });
    if (isMain) {
      ctx.marker = marker;
    }
    return marker;
  }

  _addAllMarkers(ctx, isMobile) {
    const state = this.card.hass?.states[ctx.entityId];
    if (!state?.attributes?.departures) return;
    const allDeps = state.attributes.departures || [];
    const groups = {};
    const main = allDeps.find(
      d => d.vehicle_code && d.vehicle_code === ctx.vehicleCode && parseVehiclePosition(d.vehicle_lat, d.vehicle_lng)
    );
    if (main) {
      const mainPos = parseVehiclePosition(main.vehicle_lat, main.vehicle_lng);
      groups[`${mainPos[0].toFixed(4)}|${mainPos[1].toFixed(4)}`] = 1;
      ctx.markers.push(this._createVehicleMarker(ctx, main, mainPos, isMobile));
    }
    for (const d of allDeps) {
      if (d === main) continue;
      const pos = parseVehiclePosition(d.vehicle_lat, d.vehicle_lng);
      if (!pos) continue;
      const spread = this._spreadPosition(pos, groups);
      ctx.markers.push(this._createVehicleMarker(ctx, d, spread, isMobile));
    }
    ctx.marker?.bringToFront?.();
  }

  renderAllVehicleMarkers(ctx, info, isMobile) {
    if (!this.card.hass) return;
    ctx.markers.forEach(m => ctx.map.removeLayer(m));
    ctx.markers = [];
    ctx.marker = null;
    this._addAllMarkers(ctx, isMobile);
  }

  updateAllVehiclePositions(ctx) {
    if (ctx.destroyed || !ctx.entityId || !ctx.map || !this.card.hass) return;
    const wasOpen = Boolean(ctx.marker?.isPopupOpen?.());
    ctx.markers.forEach(m => ctx.map.removeLayer(m));
    ctx.markers = [];
    ctx.marker = null;
    this._addAllMarkers(ctx, window.innerWidth < 480);
    if (wasOpen && ctx.marker) ctx.marker.openPopup();
  }

  updateVehiclePosition(ctx) {
    if (ctx.destroyed || !ctx.entityId || !ctx.marker || !this.card.hass) return;
    const state = this.card.hass.states[ctx.entityId];
    if (!state?.attributes?.departures) return;
    for (const d of state.attributes.departures) {
      if (d.vehicle_code && d.vehicle_code === ctx.vehicleCode) {
        const position = parseVehiclePosition(d.vehicle_lat, d.vehicle_lng);
        if (!position) continue;
        const [newLat, newLng] = position;
        const curPos = ctx.marker.getLatLng();
        if (Math.abs(curPos.lat - newLat) < 0.00001 && Math.abs(curPos.lng - newLng) < 0.00001) {
          return;
        }
        ctx.marker.setLatLng([newLat, newLng]);
        
        const bearing = d.vehicle_direction || d.direction || 0;
        const color = routeColor(d.route, d._provider || d.provider || "", d.route_color);
        const vt = d.vehicle_type || "bus";
        const isMobile = window.innerWidth < 480;
        const mk = this.buildVehicleMarker(bearing, color, d.route, vt, d, isMobile);
        const mkHtml = `<div class="zm-arrow">${mk.svg}</div>`;
        ctx.marker.setIcon(window.L.divIcon({
          className: "",
          html: mkHtml,
          iconSize: [mk.size, mk.size],
          iconAnchor: [mk.size / 2, mk.size / 2],
        }));
        ctx.map.setView([newLat, newLng], ctx.map.getZoom(), { animate: true });
        break;
      }
    }
  }

}
