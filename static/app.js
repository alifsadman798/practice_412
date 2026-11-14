const $ = (selector) => document.querySelector(selector);
const results = $("#results");
const statusLine = $("#status");

let currentUser = null;

function showStatus(message = "", type = "info") {
  if (!message) {
    statusLine.textContent = "";
    statusLine.className = "status";
    return;
  }
  statusLine.textContent = message;
  statusLine.className = `status ${type}`;
}

async function api(url, options = {}) {
  const token = localStorage.getItem("token");
  const headers = { "Content-Type": "application/json", ...options.headers };
  if (token && !headers["Authorization"]) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const response = await fetch(url, { ...options, headers });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    let msg = `Request failed with status ${response.status}`;
    if (typeof payload.detail === "string") {
      msg = payload.detail;
    } else if (Array.isArray(payload.detail)) {
      msg = payload.detail
        .map((d) => (d.msg ? d.msg.replace(/^Value error,\s*/i, "") : JSON.stringify(d)))
        .join("; ");
    } else if (payload.detail && typeof payload.detail === "object") {
      msg = payload.detail.msg || JSON.stringify(payload.detail);
    }
    throw new Error(msg);
  }
  return payload;
}

function localDate() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

function localTime() {
  const now = new Date();
  return `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
}

function getModeBadge(mode, size = 13, interactive = true) {
  const m = String(mode || "").toLowerCase().trim();
  const interactiveCls = interactive ? " interactive" : "";
  if (m === "bus" || m.includes("bus")) {
    return `<span class="mode-icon-badge bus${interactiveCls}" title="Inter-District Bus"><svg class="mode-svg" viewBox="0 0 24 24" width="${size}" height="${size}" fill="currentColor" aria-hidden="true"><path d="M4 16c0 .88.39 1.67 1 2.22V20a1 1 0 0 0 1 1h1a1 1 0 0 0 1-1v-1h8v1a1 1 0 0 0 1 1h1a1 1 0 0 0 1-1v-1.78c.61-.55 1-1.34 1-2.22V6c0-3.5-3.58-4-8-4s-8 .5-8 4v10zm3.5 1a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3zm9 0a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3zm-9.5-6V6h10v5h-10z"/></svg></span>`;
  }
  if (m === "train" || m.includes("train") || m.includes("rail")) {
    return `<span class="mode-icon-badge train${interactiveCls}" title="Bangladesh Railway"><svg class="mode-svg" viewBox="0 0 24 24" width="${size}" height="${size}" fill="currentColor" aria-hidden="true"><path d="M12 2c-4 0-8 .5-8 4v9.5C4 17.43 5.57 19 7.5 19L6 20.5v.5h12v-.5L16.5 19c1.93 0 3.5-1.57 3.5-3.5V6c0-3.5-4-4-8-4zM7.5 17c-.83 0-1.5-.67-1.5-1.5S6.67 14 7.5 14s1.5.67 1.5 1.5S8.33 17 7.5 17zm4.5-5H6V6h6v6zm4.5 5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zm1.5-5h-5V6h5v6z"/></svg></span>`;
  }
  if (m === "local" || m === "road") {
    return `<span class="mode-icon-badge local${interactiveCls}" title="Local Transport"><svg class="mode-svg" viewBox="0 0 24 24" width="${size}" height="${size}" fill="currentColor" aria-hidden="true"><path d="M18.92 6.01C18.72 5.42 18.16 5 17.5 5h-11c-.66 0-1.22.42-1.42 1.01L3 12v8c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1h12v1c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-8l-2.08-5.99zM6.85 7h10.29l1.04 3H5.81l1.04-3zM19 17H5v-4.66l.12-.34h13.77l.11.34V17z"/><circle cx="7.5" cy="14.5" r="1.5"/><circle cx="16.5" cy="14.5" r="1.5"/></svg></span>`;
  }
  if (m === "multimodal") {
    return `<span class="mode-icon-badge multimodal${interactiveCls}" title="Multimodal Journey"><span style="display:inline-flex;align-items:center;gap:3px;"><svg class="mode-svg" viewBox="0 0 24 24" width="11" height="11" fill="currentColor"><path d="M4 16c0 .88.39 1.67 1 2.22V20a1 1 0 0 0 1 1h1a1 1 0 0 0 1-1v-1h8v1a1 1 0 0 0 1 1h1a1 1 0 0 0 1-1v-1.78c.61-.55 1-1.34 1-2.22V6c0-3.5-3.58-4-8-4s-8 .5-8 4v10zm3.5 1a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3zm9 0a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3zm-9.5-6V6h10v5h-10z"/></svg>+<svg class="mode-svg" viewBox="0 0 24 24" width="11" height="11" fill="currentColor"><path d="M12 2c-4 0-8 .5-8 4v9.5C4 17.43 5.57 19 7.5 19L6 20.5v.5h12v-.5L16.5 19c1.93 0 3.5-1.57 3.5-3.5V6c0-3.5-4-4-8-4zM7.5 17c-.83 0-1.5-.67-1.5-1.5S6.67 14 7.5 14s1.5.67 1.5 1.5S8.33 17 7.5 17zm4.5-5H6V6h6v6zm4.5 5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zm1.5-5h-5V6h5v6z"/></svg></span></span>`;
  }
  return "";
}

function formatMinutesRange(minMins, maxMins) {
  const min = Math.round(minMins || 0);
  const max = Math.round(maxMins || min);
  const minH = Math.floor(min / 60);
  const minM = min % 60;
  const maxH = Math.floor(max / 60);
  const maxM = max % 60;

  if (minH === 0 && maxH === 0) {
    return `${min}–${max} mins`;
  }
  const minStr = minH > 0 ? `${minH}h ${minM > 0 ? minM + 'm' : ''}`.trim() : `${minM}m`;
  const maxStr = maxH > 0 ? `${maxH}h ${maxM > 0 ? maxM + 'm' : ''}`.trim() : `${maxM}m`;
  return `${minStr} – ${maxStr}`;
}

function formatWaitTime(minutes) {
  const m = Number(minutes) || 0;
  if (m <= 0) return "0 mins (Immediate Boarding)";
  if (m < 60) return `${m} min${m === 1 ? '' : 's'}`;
  const h = Math.floor(m / 60);
  const rem = m % 60;
  return `${h}h${rem > 0 ? ' ' + rem + 'm' : ''} (${m} mins wait)`;
}

function calculateArrivalWindow(depStr, travelMinutes) {
  const expected = Number(travelMinutes) || 0;
  const minMins = Math.max(1, Math.round(expected * 0.9));
  const maxMins = Math.round(expected * 1.15);

  if (!depStr || depStr === "Estimated" || depStr === "--:--") {
    return `~${minMins}–${maxMins} mins (Est. Range)`;
  }
  const parts = String(depStr).split(":");
  if (parts.length < 2) {
    return `~${minMins}–${maxMins} mins (Est. Range)`;
  }
  const h = parseInt(parts[0], 10);
  const m = parseInt(parts[1], 10);
  if (isNaN(h) || isNaN(m)) {
    return `~${minMins}–${maxMins} mins (Est. Range)`;
  }

  const depTotal = h * 60 + m;
  const arrMinTotal = (depTotal + minMins) % (24 * 60);
  const arrMaxTotal = (depTotal + maxMins) % (24 * 60);

  const arrMinH = String(Math.floor(arrMinTotal / 60)).padStart(2, "0");
  const arrMinM = String(arrMinTotal % 60).padStart(2, "0");
  const arrMaxH = String(Math.floor(arrMaxTotal / 60)).padStart(2, "0");
  const arrMaxM = String(arrMaxTotal % 60).padStart(2, "0");

  return `~${arrMinH}:${arrMinM} – ${arrMaxH}:${arrMaxM}`;
}

function formatStopTimes(s, idx, totalStops) {
  const rawArr = String(s.arrival_time || s.arrival || "").slice(0, 5);
  const rawDep = String(s.departure_time || s.departure || "").slice(0, 5);
  const baseTime = rawDep || rawArr;

  let arrDisplay = "";
  let depDisplay = "";
  let haltBadge = "";

  if (idx === 0) {
    const time = rawDep || baseTime || "--:--";
    arrDisplay = `<span class="stop-role origin">Origin</span> <b>${time}</b>`;
    depDisplay = `<b>${time}</b>`;
    haltBadge = '<span class="halt-badge origin">Origin / Starts</span>';
  } else if (idx === totalStops - 1) {
    const time = rawArr || baseTime || "--:--";
    arrDisplay = `<b>~${time} (Est.)</b>`;
    depDisplay = `<span class="stop-role dest">Terminus</span> <b>${time}</b>`;
    haltBadge = '<span class="halt-badge dest">Terminating Station</span>';
  } else {
    const arrTime = rawArr || baseTime || "--:--";
    const depTime = rawDep || baseTime || "--:--";
    arrDisplay = `<b>~${arrTime}</b>`;
    depDisplay = `<b>${depTime}</b>`;
    const m = s.halt_minutes ?? 0;
    haltBadge = m > 0
      ? `<span class="halt-badge mid">${m} min${m === 1 ? '' : 's'} halt</span>`
      : '<span class="halt-badge mid">Scheduled Halt</span>';
  }

  return { arrDisplay, depDisplay, haltBadge };
}

function renderStoppages(stops) {
  if (!stops || stops.length === 0) return "";
  const rows = stops.map((s, idx) => {
    const { arrDisplay, depDisplay, haltBadge } = formatStopTimes(s, idx, stops.length);
    const distText = s.district_name && s.district_name !== s.station ? ` <span class="station-dist">(${escapeHtml(s.district_name)})</span>` : "";

    return `
      <tr>
        <td>${idx + 1}</td>
        <td><strong>${escapeHtml(s.station)}</strong>${distText}</td>
        <td>${arrDisplay}</td>
        <td>${depDisplay}</td>
        <td>${haltBadge}</td>
      </tr>
    `;
  }).join("");

  return `
    <div class="stoppages-wrapper">
      <button type="button" class="stoppages-toggle-btn" onclick="const t = this.nextElementSibling; t.classList.toggle('hidden'); const isExpanded = !t.classList.contains('hidden'); this.querySelector('.stoppage-arrow').textContent = isExpanded ? '▲' : '▼';">
        <span style="display:inline-flex; align-items:center; gap:6px;">${getModeBadge("train", 14)} View Stoppages &amp; Schedule (${stops.length} Stations)</span>
        <span class="stoppage-arrow">▼</span>
      </button>
      <div class="stoppages-table-box hidden">
        <table class="stoppage-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Station</th>
              <th>Arrival</th>
              <th>Departure</th>
              <th>Halt Duration</th>
            </tr>
          </thead>
          <tbody>
            ${rows}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function cleanDistrictName(str) {
  if (!str) return "";
  let s = String(str).trim();
  const match = s.match(/\(([^)]+)\)/);
  if (match && match[1]) {
    s = match[1].trim();
  }
  s = s.replace(/\s+(?:Bus\s+Terminal|Railway\s+Station|Train\s+Station|Bus\s+Stand|Counter|Junction|Halt|Bypass|Terminal|Station)\b/gi, "").trim();
  return s;
}

function getTimelineSegmentModes(districts, legs, fallbackMode = "bus") {
  if (!districts || districts.length < 2) return [];
  const numSegments = districts.length - 1;
  if (!legs || legs.length === 0) {
    return Array(numSegments).fill(fallbackMode);
  }
  if (legs.length === 1) {
    return Array(numSegments).fill(legs[0].mode || fallbackMode);
  }

  const cleanLegs = legs.map((l) => ({
    mode: l.mode || fallbackMode,
    originDist: cleanDistrictName(l.origin).toLowerCase(),
    destDist: cleanDistrictName(l.destination).toLowerCase(),
  }));

  const modes = [];
  let legIdx = 0;

  for (let s = 0; s < numSegments; s++) {
    const fromCity = cleanDistrictName(districts[s]).toLowerCase();
    const toCity = cleanDistrictName(districts[s + 1]).toLowerCase();

    if (legIdx < cleanLegs.length - 1) {
      if (fromCity === cleanLegs[legIdx + 1].originDist || fromCity === cleanLegs[legIdx].destDist) {
        legIdx++;
      }
    }

    modes.push(cleanLegs[legIdx].mode);

    if (legIdx < cleanLegs.length - 1 && toCity === cleanLegs[legIdx].destDist) {
      legIdx++;
    }
  }

  return modes;
}

function buildContinuousMultimodalPath(legs, defaultPath = []) {
  if (!legs || legs.length === 0) {
    const p = defaultPath || [];
    return {
      stops: p.map((name, idx, arr) => ({
        name,
        role: idx === 0 ? "Origin" : (idx === arr.length - 1 ? "Destination" : ""),
        roleClass: idx === 0 ? "origin" : (idx === arr.length - 1 ? "dest" : "intermediate")
      })),
      segmentModes: Array(Math.max(0, p.length - 1)).fill("bus")
    };
  }

  const stops = [];
  const segmentModes = [];

  for (let legIdx = 0; legIdx < legs.length; legIdx++) {
    const leg = legs[legIdx];
    const legMode = (leg.mode || "bus").toLowerCase();

    // Retrieve all stops for this leg
    let legStopNames = [];
    if (leg.path && leg.path.length >= 2) {
      legStopNames = [...leg.path];
    } else if (leg.stops && leg.stops.length >= 2) {
      legStopNames = leg.stops.map(s => {
        const st = s.station.trim();
        const dist = (s.district_name || "").trim();
        return (dist && dist.toLowerCase() !== st.toLowerCase()) ? `${st} (${dist})` : st;
      });
    } else {
      legStopNames = [leg.origin, leg.destination];
    }

    if (legIdx === 0) {
      // First leg: add all stops
      for (let i = 0; i < legStopNames.length; i++) {
        const isFirst = i === 0;
        const isLastOfLeg = i === legStopNames.length - 1;
        const isTransfer = isLastOfLeg && legs.length > 1;

        stops.push({
          name: legStopNames[i],
          role: isFirst ? "Origin" : (isTransfer ? "Transfer Point" : ""),
          roleClass: isFirst ? "origin" : (isTransfer ? "transfer-point" : "intermediate")
        });

        if (!isLastOfLeg) {
          segmentModes.push(legMode);
        }
      }
    } else {
      // Connecting leg: join with previous leg
      const prevLastStop = stops[stops.length - 1];
      const curFirstStopName = legStopNames[0];

      const prevClean = cleanDistrictName(prevLastStop.name).toLowerCase();
      const curClean = cleanDistrictName(curFirstStopName).toLowerCase();
      const isExactMatch = prevLastStop.name.trim().toLowerCase() === curFirstStopName.trim().toLowerCase();
      const isDistrictMatch = prevClean === curClean;

      let startIdx = 1;
      if (isExactMatch || isDistrictMatch) {
        // Reuse transfer point stop
        prevLastStop.role = "Transfer Point";
        prevLastStop.roleClass = "transfer-point";
        segmentModes.push(legMode);
        startIdx = 1;
      } else {
        // Different stop name, e.g. terminal to station
        prevLastStop.role = "Transfer Point";
        prevLastStop.roleClass = "transfer-point";
        segmentModes.push(legMode);

        stops.push({
          name: curFirstStopName,
          role: "",
          roleClass: "intermediate"
        });
        startIdx = 1;
      }

      for (let i = startIdx; i < legStopNames.length; i++) {
        const isLastOfLeg = i === legStopNames.length - 1;
        const isLastOfAll = isLastOfLeg && legIdx === legs.length - 1;
        const isTransfer = isLastOfLeg && legIdx < legs.length - 1;

        stops.push({
          name: legStopNames[i],
          role: isLastOfAll ? "Destination" : (isTransfer ? "Transfer Point" : ""),
          roleClass: isLastOfAll ? "dest" : (isTransfer ? "transfer-point" : "intermediate")
        });

        if (!isLastOfLeg) {
          segmentModes.push(legMode);
        }
      }
    }
  }

  if (stops.length > 0) {
    stops[stops.length - 1].role = "Destination";
    stops[stops.length - 1].roleClass = "dest";
  }

  return { stops, segmentModes };
}

function renderContinuousMultimodalTimeline(route) {
  const { stops, segmentModes } = buildContinuousMultimodalPath(route.legs || [], route.path || []);
  if (!stops || stops.length < 2) return "";

  const stepsHtml = [];
  for (let i = 0; i < stops.length; i++) {
    const s = stops[i];
    stepsHtml.push(`
      <div class="timeline-stop ${s.roleClass}">
        <div class="timeline-dot"></div>
        <div class="timeline-stop-info">
          <span class="timeline-city">${escapeHtml(s.name)}</span>
          ${s.role ? `<span class="timeline-role">${escapeHtml(s.role)}</span>` : ""}
        </div>
      </div>
    `);

    if (i < segmentModes.length) {
      const legMode = segmentModes[i] || "bus";
      stepsHtml.push(`
        <div class="timeline-segment">
          <div class="timeline-track"></div>
          <div class="timeline-mode-pill ${escapeHtml(legMode)}">
            ${getModeBadge(legMode, 11)}
            <span class="timeline-mode-text">${escapeHtml(legMode.toUpperCase())}</span>
          </div>
          <div class="timeline-track"></div>
        </div>
      `);
    }
  }

  return `
    <div class="route-timeline-wrap">
      <div class="route-timeline">
        ${stepsHtml.join("")}
      </div>
    </div>
  `;
}

function renderRouteTimeline(route) {
  const rawPath = route.path || [];
  const legs = route.legs || [];
  const isMultimodal = (route.kind && route.kind.toLowerCase() === "multimodal") || (legs && legs.length > 1);

  if (isMultimodal && legs.length > 1) {
    return renderContinuousMultimodalTimeline(route);
  }

  if (!rawPath || rawPath.length < 2) return "";

  const displayPath = [...rawPath];
  const segmentModes = getTimelineSegmentModes(displayPath, legs, route.kind || "bus");

  const stepsHtml = [];
  for (let i = 0; i < displayPath.length; i++) {
    const city = displayPath[i];
    const isFirst = i === 0;
    const isLast = i === displayPath.length - 1;
    const role = isFirst ? "Origin" : (isLast ? "Destination" : "");
    const roleClass = isFirst ? "origin" : (isLast ? "dest" : "intermediate");

    stepsHtml.push(`
      <div class="timeline-stop ${roleClass}">
        <div class="timeline-dot"></div>
        <div class="timeline-stop-info">
          <span class="timeline-city">${escapeHtml(city)}</span>
          ${role ? `<span class="timeline-role">${role}</span>` : ""}
        </div>
      </div>
    `);

    if (!isLast) {
      const legMode = segmentModes[i] || (legs[0] && legs[0].mode) || route.kind || "bus";

      stepsHtml.push(`
        <div class="timeline-segment">
          <div class="timeline-track"></div>
          <div class="timeline-mode-pill ${escapeHtml(legMode)}">
            ${getModeBadge(legMode, 11)}
            <span class="timeline-mode-text">${escapeHtml(legMode.toUpperCase())}</span>
          </div>
          <div class="timeline-track"></div>
        </div>
      `);
    }
  }

  return `
    <div class="route-timeline-wrap">
      <div class="route-timeline">
        ${stepsHtml.join("")}
      </div>
    </div>
  `;
}

function formatTerminalName(name, mode) {
  if (!name) return "";
  const n = String(name).trim();
  const nl = n.toLowerCase();
  const m = String(mode || "").toLowerCase();
  if (m === "train") {
    if (!nl.includes("station") && !nl.includes("junction") && !nl.includes("halt") && !nl.includes("bypass") && !nl.includes("railway")) {
      return `${n} Railway Station`;
    }
    return n;
  }
  if (m === "bus") {
    if (!nl.includes("bus") && !nl.includes("terminal") && !nl.includes("stand")) {
      return `${n} Bus Terminal`;
    }
    return n;
  }
  return n;
}

function parseTimeToMinutes(t) {
  if (!t || typeof t !== "string") return null;
  const match = t.trim().match(/^(\d{1,2}):(\d{2})/);
  if (!match) return null;
  const h = parseInt(match[1], 10);
  const m = parseInt(match[2], 10);
  if (isNaN(h) || isNaN(m)) return null;
  return h * 60 + m;
}

function formatMinutesToTime(mins) {
  if (mins == null) return null;
  const normalized = ((mins % 1440) + 1440) % 1440;
  const h = Math.floor(normalized / 60);
  const m = normalized % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

function formatTimeAMPM(timeStr) {
  if (!timeStr || typeof timeStr !== "string") return timeStr || "Estimated";
  const trimmed = timeStr.trim();
  const match = trimmed.match(/^(\d{1,2}):(\d{2})/);
  if (!match) return trimmed;
  let h = parseInt(match[1], 10);
  const m = match[2];
  if (isNaN(h)) return trimmed;
  const ampm = h >= 12 ? "PM" : "AM";
  h = h % 12;
  if (h === 0) h = 12;
  return `${String(h).padStart(2, "0")}:${m} ${ampm}`;
}

function formatMinutesToHours(mins) {
  if (mins == null || isNaN(mins)) return "";
  const total = Math.round(Number(mins));
  const h = Math.floor(total / 60);
  const m = total % 60;
  if (h === 0) return `${m} mins`;
  if (m === 0) return `${h} hr${h > 1 ? "s" : ""}`;
  return `${h}h ${String(m).padStart(2, "0")}m`;
}

function renderConnectionAlert(transfer, currentLeg, nextLeg) {
  const transferFrom = transfer?.from_location || formatTerminalName(currentLeg.destination, currentLeg.mode);
  const transferTo = transfer?.to_location || formatTerminalName(nextLeg.origin, nextLeg.mode);
  const mins = transfer?.travel_minutes ?? (transfer?.distance_km ? Math.round(transfer.distance_km / 30 * 60) : 15);
  const prevMode = (currentLeg.mode || "transport").toLowerCase();
  const nextMode = (nextLeg.mode || "transport").toLowerCase();

  const rawDep = nextLeg.departure || nextLeg.departure_time;
  const nextDepTime = (rawDep && String(rawDep).trim() && String(rawDep).slice(0, 5) !== "00:00")
    ? String(rawDep).slice(0, 5)
    : (transfer?.target_arrival_time || transfer?.next_departure_time || null);

  const rawArr = currentLeg.arrival || currentLeg.arrival_time;
  const prevArrTime = (rawArr && String(rawArr).trim())
    ? String(rawArr).slice(0, 5)
    : (transfer?.prev_arrival_time || null);

  const nextDepMins = parseTimeToMinutes(nextDepTime);
  const prevArrMins = parseTimeToMinutes(prevArrTime);

  let recLeaveDisplay = "Depart immediately upon arrival";
  if (nextDepMins != null) {
    const recMins = nextDepMins - mins;
    recLeaveDisplay = `${formatTimeAMPM(formatMinutesToTime(recMins))} or earlier`;
  } else if (transfer?.recommended_leave_time) {
    recLeaveDisplay = `${formatTimeAMPM(transfer.recommended_leave_time)} or earlier`;
  }

  let bufferMins = null;
  if (nextDepMins != null && prevArrMins != null) {
    let rawDiff = nextDepMins - prevArrMins;
    if (rawDiff < 0) rawDiff += 1440;
    bufferMins = rawDiff - mins;
  } else if (transfer?.buffer_minutes != null) {
    bufferMins = transfer.buffer_minutes;
  }

  let alertSeverityClass = "buffer-info";
  let alertBadgeClass = "badge-info";
  let statusBadge = "Comfortable";
  let statusText = "Comfortable";
  let statusClass = "status-comfortable";
  let bufferDisplay = "Subject to timetable schedule";
  let warningHtml = "";

  if (bufferMins !== null) {
    if (bufferMins >= 25) {
      statusText = "Comfortable";
      statusClass = "status-comfortable";
      alertSeverityClass = "buffer-comfortable";
      alertBadgeClass = "badge-comfortable";
      statusBadge = "Comfortable Window (~" + bufferMins + "m buffer)";
      bufferDisplay = `🟢 ~${bufferMins} mins remaining (Comfortable)`;
    } else if (bufferMins >= 0) {
      statusText = "Tight";
      statusClass = "status-tight";
      alertSeverityClass = "buffer-tight";
      alertBadgeClass = "badge-tight";
      statusBadge = "Tight Connection (~" + bufferMins + "m buffer)";
      bufferDisplay = `🟠 ~${bufferMins} mins remaining (Tight buffer)`;
      warningHtml = `
        <div class="alert-warning-pill warning">
          ⚠️ <strong>Notice:</strong> Connection window is tight (~${bufferMins} minutes remaining). Head straight to local transport upon arrival to avoid missing your connecting departure.
        </div>
      `;
    } else {
      statusText = "Risky";
      statusClass = "status-risky";
      alertSeverityClass = "buffer-critical";
      alertBadgeClass = "badge-critical";
      statusBadge = "Risky / Insufficient Buffer";
      bufferDisplay = `🔴 ${Math.abs(bufferMins)} mins short (Cannot reasonably be made on time)`;
      warningHtml = `
        <div class="alert-warning-pill critical">
          🚨 <strong>Prominent Warning:</strong> Scheduled arrival plus local transfer (~${mins} mins) exceeds the next departure time. This connection cannot reasonably be made on time. Please choose an earlier transport or later connecting service.
        </div>
      `;
    }
  } else {
    statusText = "Estimated";
    statusClass = "status-info";
    alertSeverityClass = "buffer-info";
    alertBadgeClass = "badge-info";
    statusBadge = "Local Connection";
    bufferDisplay = nextDepTime ? `Reach terminal before ${formatTimeAMPM(nextDepTime)}` : "Schedule estimate unavailable";
  }

  const prevArrDisplay = prevArrTime ? formatTimeAMPM(prevArrTime) : "Estimated arrival";
  const nextDepDisplay = nextDepTime ? formatTimeAMPM(nextDepTime) : "Schedule estimate unavailable";

  return `
    <div class="connection-alert-box ${alertSeverityClass}">
      <div class="alert-box-header">
        <span class="alert-title-wrap">
          <span class="alert-icon">⚠️</span>
          <strong class="alert-title">CONNECTION ALERT &mdash; TIME-SENSITIVE TRANSFER</strong>
        </span>
        <span class="alert-status-badge ${alertBadgeClass}">${statusBadge}</span>
      </div>
      <p class="alert-message">
        &ldquo;You need to reach <b>${escapeHtml(transferTo)}</b> before your next ${escapeHtml(nextMode)} departure. Allow approximately <b>${mins} minutes</b> for local transportation from ${escapeHtml(transferFrom)}.&rdquo;
      </p>
      <div class="alert-metrics-grid">
        <div class="alert-metric-item">
          <span class="metric-label">Previous ${escapeHtml(prevMode)} Arrival</span>
          <span class="metric-val">🏁 <b>${escapeHtml(prevArrDisplay)}</b></span>
        </div>
        <div class="alert-metric-item">
          <span class="metric-label">Next ${escapeHtml(nextMode)} Departure</span>
          <span class="metric-val">🕒 <b>${escapeHtml(nextDepDisplay)}</b></span>
        </div>
        <div class="alert-metric-item">
          <span class="metric-label">Estimated Local Duration</span>
          <span class="metric-val">⏱️ <b>~${mins} mins</b></span>
        </div>
        <div class="alert-metric-item">
          <span class="metric-label">Recommended Departure</span>
          <span class="metric-val">🚪 <b>${escapeHtml(recLeaveDisplay)}</b></span>
        </div>
        <div class="alert-metric-item">
          <span class="metric-label">Available Connection Buffer</span>
          <span class="metric-val"><b>${bufferDisplay}</b></span>
        </div>
        <div class="alert-metric-item">
          <span class="metric-label">Connection Status</span>
          <span class="metric-val"><b class="${statusClass}">${statusText}</b></span>
        </div>
      </div>
      ${warningHtml}
      <div class="transfer-passenger-tip">
        💡 <strong>Passenger Guide:</strong> Take an auto-rickshaw, CNG, or local shuttle from <b>${escapeHtml(transferFrom)}</b> to reach <b>${escapeHtml(transferTo)}</b>. Allow at least ${mins} minutes for transit plus terminal buffer before departure.
      </div>
    </div>
  `;
}

function checkPhysicalTransferRequired(curLeg, nextLeg) {
  if (!curLeg || !nextLeg) return false;
  const curDest = cleanDistrictName(curLeg.destination).toLowerCase();
  const nextOrig = cleanDistrictName(nextLeg.origin).toLowerCase();
  const curMode = (curLeg.mode || "").trim().toLowerCase();
  const nextMode = (nextLeg.mode || "").trim().toLowerCase();

  // If destination district differs from next origin district (e.g. Kasba vs Brahmanbaria)
  if (curDest !== nextOrig) return true;

  // If different transport modes in the same district (e.g. Bus Terminal vs Railway Station)
  // They are physically separate terminals requiring local transit
  if (curMode !== nextMode) return true;

  // If same mode and same district (e.g. train-to-train platform transfer at Dhaka)
  // No physical terminal transfer is required
  return false;
}

function getLegPath(routePath, leg) {
  // If leg has train stops, derive path from stops with district names
  if (leg.stops && leg.stops.length >= 2) {
    return leg.stops.map((s) => s.station + (s.district_name && s.district_name !== s.station ? ` (${s.district_name})` : ""));
  }

  if (routePath && routePath.length >= 2) {
    const origClean = cleanDistrictName(leg.origin).toLowerCase();
    const destClean = cleanDistrictName(leg.destination).toLowerCase();

    let startIdx = -1;
    let endIdx = -1;

    for (let i = 0; i < routePath.length; i++) {
      const d = cleanDistrictName(routePath[i]).toLowerCase();
      if (startIdx === -1 && (d === origClean || d.includes(origClean) || origClean.includes(d))) {
        startIdx = i;
      }
      if (startIdx !== -1 && (d === destClean || d.includes(destClean) || destClean.includes(d))) {
        endIdx = i;
        break;
      }
    }

    if (startIdx !== -1 && endIdx !== -1 && endIdx >= startIdx) {
      const sub = routePath.slice(startIdx, endIdx + 1);
      if (sub.length >= 2) return sub;
    }
  }

  return [leg.origin, leg.destination];
}

function renderIndividualTransportLegCard(leg, legIdx, totalLegs, routePath, route) {
  const rawDep = leg.departure || leg.departure_time;
  const dep = rawDep ? (rawDep.length > 5 ? rawDep.slice(0, 5) : rawDep) : "Estimated";
  const rawArr = leg.arrival || leg.arrival_time;
  const arr = rawArr ? (rawArr.length > 5 ? rawArr.slice(0, 5) : rawArr) : "Estimated";
  const estArrivalWindow = calculateArrivalWindow(dep, leg.travel_minutes);

  const fromDistrict = cleanDistrictName(leg.origin);
  const toDistrict = cleanDistrictName(leg.destination);
  const fromTerminal = formatTerminalName(leg.origin, leg.mode);
  const toTerminal = formatTerminalName(leg.destination, leg.mode);
  const stoppageHtml = (leg.stops && leg.stops.length > 0) ? renderStoppages(leg.stops) : "";

  // Sliced route path for this individual leg
  const legPath = getLegPath(routePath, leg);
  const legTimelineHtml = renderRouteTimeline({ path: legPath, kind: leg.mode, legs: [leg] });

  const durationHoursText = formatMinutesToHours(leg.travel_minutes);

  let legDisruptionHtml = "";
  if (leg.is_affected && leg.disruption_alerts && leg.disruption_alerts.length) {
    legDisruptionHtml = leg.disruption_alerts.map((alert) => `
      <div class="leg-disruption-alert severity-${escapeHtml((alert.severity || "moderate").toLowerCase())}">
        <span class="leg-disruption-icon">⚠️</span>
        <div class="leg-disruption-text">
          <strong>${escapeHtml(alert.severity)} Incident: ${escapeHtml(alert.title)}</strong>
          <p>${escapeHtml(alert.message)}</p>
        </div>
      </div>
    `).join("");
  }

  return `
    <div class="transport-service-card mode-${escapeHtml(leg.mode)}">
      <!-- Service Header with Leg Tag, Operator/Train Info & Fare -->
      <div class="service-card-topbar">
        <div class="service-topbar-left">
          <span class="service-leg-pill ${escapeHtml(leg.mode)}">
            ${getModeBadge(leg.mode, 13)} LEG ${legIdx + 1} &mdash; ${escapeHtml(leg.mode.toUpperCase())}
          </span>
          <span class="service-name-text">
            <strong>${escapeHtml(leg.service)}</strong>
          </span>
        </div>
        <div class="service-topbar-right">
          <span class="service-fare-chip">BDT ${leg.fare_bdt}</span>
        </div>
      </div>
      ${legDisruptionHtml}

      <!-- Starting District and Destination District Heading -->
      <div class="service-route-heading">
        <div class="service-endpoint-group">
          <span class="endpoint-dot origin">●</span>
          <span class="endpoint-name"><strong>${escapeHtml(fromDistrict)}</strong></span>
          <span class="endpoint-arrow">➔</span>
          <span class="endpoint-dot dest">🏁</span>
          <span class="endpoint-name"><strong>${escapeHtml(toDistrict)}</strong></span>
        </div>
        <span class="service-type-badge ${escapeHtml(leg.mode)}">${escapeHtml(leg.mode.toUpperCase())} JOURNEY</span>
      </div>

      <!-- Route Overview Timeline for this transport leg (exact existing timeline component) -->
      ${legTimelineHtml}

      <!-- Departure & Arrival Box (exact existing departure-arrival-row) -->
      <div class="departure-arrival-row">
        <div class="time-block departure">
          <span class="time-label">Departure</span>
          <span class="time-value">🕒 <b>${escapeHtml(formatTimeAMPM(dep))}</b></span>
          <span class="time-station">${escapeHtml(fromTerminal)}</span>
        </div>
        <div class="time-divider">➔</div>
        <div class="time-block arrival">
          <span class="time-label">Estimated Arrival Window</span>
          <span class="time-value">🏁 <b>${escapeHtml(formatTimeAMPM(estArrivalWindow))}</b></span>
          <span class="time-station">${escapeHtml(toTerminal)}</span>
        </div>
      </div>

      <!-- Leg Details & Journey Metrics Grid -->
      <div class="service-metrics-grid">
        <div class="service-metric-item">
          <span class="service-metric-label">Leg Distance</span>
          <span class="service-metric-val">📍 <b>${leg.distance_km.toFixed(1)} km</b></span>
        </div>
        <div class="service-metric-item">
          <span class="service-metric-label">Travel Duration</span>
          <span class="service-metric-val">⏱️ <b>~${leg.travel_minutes} mins</b> ${durationHoursText ? `<small style="color:var(--text-muted);font-weight:normal;">(~${durationHoursText})</small>` : ""}</span>
        </div>
        <div class="service-metric-item">
          <span class="service-metric-label">Schedule Buffer / Wait</span>
          <span class="service-metric-val">⏳ <b>~${leg.waiting_minutes || 15} mins</b></span>
        </div>
        <div class="service-metric-item">
          <span class="service-metric-label">Leg Fare</span>
          <span class="service-metric-val">💵 <b>BDT ${leg.fare_bdt}</b></span>
        </div>
      </div>

      <!-- Train Stoppage List & Halts Table (if Train) or Stoppages (if Bus) -->
      ${stoppageHtml}
    </div>
  `;
}

// -------------------------------------------------------------
// Reorganized Multimodal Journey Presentation Functions
// Nested, Independently Expandable Details System
// -------------------------------------------------------------

function formatWaitHoursAndMinutes(minutes) {
  if (minutes == null || isNaN(minutes) || minutes < 0) return "0 mins";
  const mins = Math.round(minutes);
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  if (h > 0 && m > 0) {
    return `${h}h ${m}m (${mins} minutes)`;
  } else if (h > 0) {
    return `${h}h (${mins} minutes)`;
  } else {
    return `${m}m (${mins} minutes)`;
  }
}

// Toggle Functions with Independent State Management
window.toggleTimelineSection = function(routeIdx) {
  const body = document.getElementById(`timeline-details-${routeIdx}`);
  const btn = document.getElementById(`timeline-toggle-btn-${routeIdx}`);
  if (!body || !btn) return;

  const isHidden = body.style.display === "none" || body.classList.contains("hidden");
  if (isHidden) {
    body.style.display = "block";
    body.classList.remove("hidden");
    btn.setAttribute("aria-expanded", "true");
    const txt = btn.querySelector(".toggle-text");
    if (txt) txt.textContent = "Hide Timeline Details";
    const icon = btn.querySelector(".toggle-icon");
    if (icon) icon.textContent = "▲";
  } else {
    body.style.display = "none";
    body.classList.add("hidden");
    btn.setAttribute("aria-expanded", "false");
    const txt = btn.querySelector(".toggle-text");
    if (txt) txt.textContent = "View Timeline Details";
    const icon = btn.querySelector(".toggle-icon");
    if (icon) icon.textContent = "▼";
  }
};

window.toggleLegSection = function(routeIdx, legIdx, mode) {
  const uniqueId = `${routeIdx}-${legIdx}`;
  const body = document.getElementById(`leg-details-${uniqueId}`);
  const btn = document.getElementById(`leg-toggle-btn-${uniqueId}`);
  if (!body || !btn) return;

  const modeLower = (mode || "transport").toLowerCase();
  const modeCapital = modeLower === "bus" ? "Bus" : modeLower === "train" ? "Train" : (modeLower.charAt(0).toUpperCase() + modeLower.slice(1));

  const isHidden = body.style.display === "none" || body.classList.contains("hidden");
  if (isHidden) {
    body.style.display = "block";
    body.classList.remove("hidden");
    btn.setAttribute("aria-expanded", "true");
    const txt = btn.querySelector(".toggle-text");
    if (txt) txt.textContent = `Hide ${modeCapital} Details`;
    const icon = btn.querySelector(".toggle-icon");
    if (icon) icon.textContent = "▲";
  } else {
    body.style.display = "none";
    body.classList.add("hidden");
    btn.setAttribute("aria-expanded", "false");
    const txt = btn.querySelector(".toggle-text");
    if (txt) txt.textContent = `View ${modeCapital} Details`;
    const icon = btn.querySelector(".toggle-icon");
    if (icon) icon.textContent = "▼";
  }
};

window.toggleTransferSection = function(routeIdx, transferIdx) {
  const uniqueId = `${routeIdx}-${transferIdx}`;
  const body = document.getElementById(`transfer-details-${uniqueId}`);
  const btn = document.getElementById(`transfer-toggle-btn-${uniqueId}`);
  if (!body || !btn) return;

  const isHidden = body.style.display === "none" || body.classList.contains("hidden");
  if (isHidden) {
    body.style.display = "block";
    body.classList.remove("hidden");
    btn.setAttribute("aria-expanded", "true");
    const txt = btn.querySelector(".toggle-text");
    if (txt) txt.textContent = "Hide Transfer Details";
    const icon = btn.querySelector(".toggle-icon");
    if (icon) icon.textContent = "▲";
  } else {
    body.style.display = "none";
    body.classList.add("hidden");
    btn.setAttribute("aria-expanded", "false");
    const txt = btn.querySelector(".toggle-text");
    if (txt) txt.textContent = "View Transfer Details";
    const icon = btn.querySelector(".toggle-icon");
    if (icon) icon.textContent = "▼";
  }
};

window.toggleStatsSection = function(routeIdx) {
  const body = document.getElementById(`stats-details-${routeIdx}`);
  const btn = document.getElementById(`stats-toggle-btn-${routeIdx}`);
  if (!body || !btn) return;

  const isHidden = body.style.display === "none" || body.classList.contains("hidden");
  if (isHidden) {
    body.style.display = "block";
    body.classList.remove("hidden");
    btn.setAttribute("aria-expanded", "true");
    const txt = btn.querySelector(".toggle-text");
    if (txt) txt.textContent = "Hide Journey Statistics";
    const icon = btn.querySelector(".toggle-icon");
    if (icon) icon.textContent = "▲";
  } else {
    body.style.display = "none";
    body.classList.add("hidden");
    btn.setAttribute("aria-expanded", "false");
    const txt = btn.querySelector(".toggle-text");
    if (txt) txt.textContent = "View Journey Statistics";
    const icon = btn.querySelector(".toggle-icon");
    if (icon) icon.textContent = "▼";
  }
};

window.toggleWaitingSection = function(routeIdx) {
  const body = document.getElementById(`waiting-details-${routeIdx}`);
  const btn = document.getElementById(`waiting-toggle-btn-${routeIdx}`);
  if (!body || !btn) return;

  const isHidden = body.style.display === "none" || body.classList.contains("hidden");
  if (isHidden) {
    body.style.display = "block";
    body.classList.remove("hidden");
    btn.setAttribute("aria-expanded", "true");
    const txt = btn.querySelector(".toggle-text");
    if (txt) txt.textContent = "Hide Waiting Time & Notices";
    const icon = btn.querySelector(".toggle-icon");
    if (icon) icon.textContent = "▲";
  } else {
    body.style.display = "none";
    body.classList.add("hidden");
    btn.setAttribute("aria-expanded", "false");
    const txt = btn.querySelector(".toggle-text");
    if (txt) txt.textContent = "View Waiting Time & Notices";
    const icon = btn.querySelector(".toggle-icon");
    if (icon) icon.textContent = "▼";
  }
};

window.toggleDisclaimersSection = function(routeIdx) {
  const body = document.getElementById(`disclaimers-details-${routeIdx}`);
  const btn = document.getElementById(`disclaimers-toggle-btn-${routeIdx}`);
  if (!body || !btn) return;

  const isHidden = body.style.display === "none" || body.classList.contains("hidden");
  if (isHidden) {
    body.style.display = "block";
    body.classList.remove("hidden");
    btn.setAttribute("aria-expanded", "true");
    const txt = btn.querySelector(".toggle-text");
    if (txt) txt.textContent = "Hide Route Disclaimers";
    const icon = btn.querySelector(".toggle-icon");
    if (icon) icon.textContent = "▲";
  } else {
    body.style.display = "none";
    body.classList.add("hidden");
    btn.setAttribute("aria-expanded", "false");
    const txt = btn.querySelector(".toggle-text");
    if (txt) txt.textContent = "View Route Disclaimers";
    const icon = btn.querySelector(".toggle-icon");
    if (icon) icon.textContent = "▼";
  }
};

// Backwards compatibility for inline transfer toggle
window.toggleTransferDetails = function(btn) {
  const body = btn.nextElementSibling;
  if (!body) return;
  const isHidden = body.classList.contains("hidden");
  body.classList.toggle("hidden", !isHidden);
  const icon = btn.querySelector(".transfer-toggle-icon");
  if (icon) icon.textContent = isHidden ? "▲" : "▼";
  const span = btn.querySelector("span:first-child");
  if (span) span.textContent = isHidden ? "ℹ️ Hide Transfer Details & Guidance" : "ℹ️ View Transfer Details & Connection Guidance";
};

// Generate compact chronological flow sequence for timeline collapsed state
function generateCompactTimelineSequence(route) {
  const legs = route.legs || [];
  if (!legs.length) return "";
  const originDist = cleanDistrictName(route.path[0]) || route.path[0];
  const destDist = cleanDistrictName(route.path[route.path.length - 1]) || route.path[route.path.length - 1];

  const steps = [];
  steps.push(`<span class="compact-flow-step origin">📍 <b>${escapeHtml(originDist)}</b></span>`);

  for (let i = 0; i < legs.length; i++) {
    const leg = legs[i];
    const modeLabel = leg.mode.toUpperCase();
    steps.push(`<span class="compact-flow-sep">➔</span>`);
    steps.push(`<span class="compact-flow-step leg ${escapeHtml(leg.mode)}">${getModeBadge(leg.mode, 12)} ${escapeHtml(modeLabel)} <span class="flow-svc">(${escapeHtml(leg.service)})</span></span>`);

    if (i < legs.length - 1) {
      const nextLeg = legs[i + 1];
      const needsPhysical = checkPhysicalTransferRequired(leg, nextLeg);
      steps.push(`<span class="compact-flow-sep">➔</span>`);
      steps.push(`<span class="compact-flow-step transfer">${needsPhysical ? "🛺 Transfer" : "🔄 Interchange"} <span class="flow-loc">(${escapeHtml(cleanDistrictName(leg.destination))})</span></span>`);
    }
  }

  steps.push(`<span class="compact-flow-sep">➔</span>`);
  steps.push(`<span class="compact-flow-step dest">🏁 <b>${escapeHtml(destDist)}</b></span>`);

  return `<div class="mm-compact-flow-row">${steps.join("")}</div>`;
}

// 1. Visual Journey Timeline (Independently Expandable)
function renderMultimodalTimeline(route, routeIdx = 0) {
  const legs = route.legs || [];
  if (legs.length === 0) return "";

  const items = [];

  for (let i = 0; i < legs.length; i++) {
    const leg = legs[i];
    const isFirstLeg = i === 0;
    const isLastLeg = i === legs.length - 1;
    const nextLeg = isLastLeg ? null : legs[i + 1];

    const rawDep = leg.departure || leg.departure_time;
    const depTime = rawDep ? (rawDep.length > 5 ? rawDep.slice(0, 5) : rawDep) : "";
    const rawArr = leg.arrival || leg.arrival_time;
    const arrTime = rawArr ? (rawArr.length > 5 ? rawArr.slice(0, 5) : rawArr) : "";

    const fromLoc = formatTerminalName(leg.origin, leg.mode);
    const toLoc = formatTerminalName(leg.destination, leg.mode);

    // 1. Origin Node (only for the first leg)
    if (isFirstLeg) {
      items.push(`
        <div class="mm-tl-node start">
          <div class="mm-tl-icon-wrap start">
            <span class="mm-tl-dot start">●</span>
          </div>
          <div class="mm-tl-info">
            <span class="mm-tl-role">STARTING LOCATION</span>
            <strong class="mm-tl-name">${escapeHtml(cleanDistrictName(leg.origin))}</strong>
            <span class="mm-tl-station">${escapeHtml(fromLoc)}</span>
          </div>
        </div>
      `);
    }

    // 2. Transport Service Leg Step
    const modeCls = (leg.mode || "bus").toLowerCase();
    items.push(`
      <div class="mm-tl-service ${modeCls}">
        <div class="mm-tl-line"></div>
        <div class="mm-tl-service-pill ${modeCls}">
          <span class="mm-tl-service-badge">${getModeBadge(leg.mode, 12)} ${escapeHtml(leg.mode.toUpperCase())}</span>
          <strong class="mm-tl-service-name">${escapeHtml(leg.service)}</strong>
          <span class="mm-tl-service-meta">
            ${depTime ? `🕒 ${formatTimeAMPM(depTime)}` : ""} ${depTime && arrTime ? "➔" : ""} ${arrTime ? `🏁 ${formatTimeAMPM(arrTime)}` : ""}
            &bull; ~${leg.travel_minutes} mins (${leg.distance_km.toFixed(1)} km)
          </span>
        </div>
        <div class="mm-tl-line"></div>
      </div>
    `);

    // 3. Intermediate Station / Transfer Point / Final Destination
    if (!isLastLeg && nextLeg) {
      const needsPhysicalTransfer = checkPhysicalTransferRequired(leg, nextLeg);
      const tr = leg.transfer_to_next;

      if (needsPhysicalTransfer) {
        const transferFrom = tr?.from_location || toLoc;
        const transferTo = tr?.to_location || formatTerminalName(nextLeg.origin, nextLeg.mode);
        const mins = tr?.travel_minutes ?? 15;
        const distKm = tr?.distance_km ?? 5.0;

        items.push(`
          <div class="mm-tl-node intermediate">
            <div class="mm-tl-icon-wrap intermediate">
              <span class="mm-tl-dot intermediate">●</span>
            </div>
            <div class="mm-tl-info">
              <span class="mm-tl-role">ARRIVAL STATION</span>
              <strong class="mm-tl-name">${escapeHtml(cleanDistrictName(leg.destination))}</strong>
              <span class="mm-tl-station">${escapeHtml(transferFrom)}</span>
            </div>
          </div>
        `);

        items.push(`
          <div class="mm-tl-service transfer">
            <div class="mm-tl-line dashed"></div>
            <div class="mm-tl-service-pill transfer">
              <span class="mm-tl-service-badge">🛺 LOCAL TRANSFER</span>
              <strong class="mm-tl-service-name">Auto-rickshaw / CNG / Shuttle</strong>
              <span class="mm-tl-service-meta">⏱️ ~${mins} mins &bull; 📍 ${distKm.toFixed(1)} km</span>
            </div>
            <div class="mm-tl-line dashed"></div>
          </div>
        `);

        items.push(`
          <div class="mm-tl-node intermediate">
            <div class="mm-tl-icon-wrap intermediate">
              <span class="mm-tl-dot intermediate">●</span>
            </div>
            <div class="mm-tl-info">
              <span class="mm-tl-role">CONNECTING DEPARTURE STATION</span>
              <strong class="mm-tl-name">${escapeHtml(cleanDistrictName(nextLeg.origin))}</strong>
              <span class="mm-tl-station">${escapeHtml(transferTo)}</span>
            </div>
          </div>
        `);
      } else {
        items.push(`
          <div class="mm-tl-node interchange">
            <div class="mm-tl-icon-wrap interchange">
              <span class="mm-tl-dot interchange">🔄</span>
            </div>
            <div class="mm-tl-info">
              <span class="mm-tl-role">TRANSFER POINT (SAME STATION)</span>
              <strong class="mm-tl-name">${escapeHtml(cleanDistrictName(leg.destination))}</strong>
              <span class="mm-tl-station">${escapeHtml(toLoc)}</span>
            </div>
          </div>
        `);
      }
    } else {
      items.push(`
        <div class="mm-tl-node end">
          <div class="mm-tl-icon-wrap end">
            <span class="mm-tl-dot end">🏁</span>
          </div>
          <div class="mm-tl-info">
            <span class="mm-tl-role">FINAL DESTINATION</span>
            <strong class="mm-tl-name">${escapeHtml(cleanDistrictName(leg.destination))}</strong>
            <span class="mm-tl-station">${escapeHtml(toLoc)}</span>
          </div>
        </div>
      `);
    }
  }

  return `
    <div class="mm-subcard mm-timeline-card" id="timeline-card-${routeIdx}">
      <div class="mm-subcard-header" id="timeline-header-${routeIdx}">
        <div class="mm-subcard-header-left">
          <div class="mm-subcard-title-line">
            <span class="section-num-pill transport">01</span>
            <span class="mm-subcard-title">Visual Journey Timeline</span>
          </div>
          <div class="mm-timeline-compact-flow" id="timeline-flow-${routeIdx}">
            ${generateCompactTimelineSequence(route)}
          </div>
        </div>
        <div class="mm-subcard-header-right">
          <button type="button" class="mm-section-toggle-btn timeline" id="timeline-toggle-btn-${routeIdx}" onclick="toggleTimelineSection('${routeIdx}')" aria-expanded="false">
            <span class="toggle-text">View Timeline Details</span>
            <span class="toggle-icon">▼</span>
          </button>
        </div>
      </div>
      <div id="timeline-details-${routeIdx}" class="mm-nested-details-body hidden" style="display: none;">
        <div class="mm-timeline-stream">
          ${items.join("")}
        </div>
      </div>
    </div>
  `;
}

// 2. Individual Transport Leg Details Card (Independently Expandable per Leg)
// Render Single Mode Leg Full Departure, Arrival & Stoppage Details (reused by Multimodal)
function renderSingleModeLegDetails(leg, legIdx, routeIdx) {
  const rawDep = leg.departure || leg.departure_time;
  const dep = rawDep ? (rawDep.length > 5 ? rawDep.slice(0, 5) : rawDep) : "Estimated";
  const rawArr = leg.arrival || leg.arrival_time;
  const arr = rawArr ? (rawArr.length > 5 ? rawArr.slice(0, 5) : rawArr) : "Estimated";
  const stoppageHtml = (leg.stops && leg.stops.length > 0) ? renderStoppages(leg.stops) : "";
  const estArrivalWindow = calculateArrivalWindow(dep, leg.travel_minutes);

  let legDisruptionHtml = "";
  if (leg.is_affected && leg.disruption_alerts && leg.disruption_alerts.length) {
    legDisruptionHtml = leg.disruption_alerts.map((alert) => `
      <div class="leg-disruption-alert severity-${escapeHtml((alert.severity || "moderate").toLowerCase())}">
        <span class="leg-disruption-icon">⚠️</span>
        <div class="leg-disruption-text">
          <strong>${escapeHtml(alert.severity)} Incident: ${escapeHtml(alert.title)}</strong>
          <p>${escapeHtml(alert.message)}</p>
        </div>
      </div>
    `).join("");
  }

  const durationHoursText = formatMinutesToHours(leg.travel_minutes);

  return `
    <div class="route-section-block section-departure-arrival" style="margin-top: 10px; border-top: 1px dashed var(--border);">
      <div class="section-badge-row">
        <span class="section-num-pill transport">02</span>
        <span class="section-title-label">${escapeHtml(leg.mode.toUpperCase())} Departure, Arrival &amp; Stoppage Details</span>
      </div>

      <div class="operator-leg-card">
        <div class="operator-header">
          <div class="operator-info">
            <span class="pill ${escapeHtml(leg.mode)}">${getModeBadge(leg.mode, 12)} ${escapeHtml(leg.mode.toUpperCase())}</span>
            <span class="operator-name"><strong>${escapeHtml(leg.service)}</strong></span>
          </div>
          <div class="operator-meta-right">
            <span class="leg-fare-tag">BDT ${leg.fare_bdt}</span>
          </div>
        </div>
        ${legDisruptionHtml}

        <div class="departure-arrival-row">
          <div class="time-block departure">
            <span class="time-label">Scheduled Departure</span>
            <span class="time-value">🕒 <b>${escapeHtml(formatTimeAMPM(dep))}</b></span>
            <span class="time-station">${escapeHtml(formatTerminalName(leg.origin, leg.mode))}</span>
          </div>
          <div class="time-divider">➔</div>
          <div class="time-block arrival">
            <span class="time-label">Estimated Arrival Window</span>
            <span class="time-value">🏁 <b>${escapeHtml(estArrivalWindow)}</b></span>
            <span class="time-station">${escapeHtml(formatTerminalName(leg.destination, leg.mode))}</span>
          </div>
        </div>

        <div class="service-metrics-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 8px; margin-top: 12px; padding: 10px; background: #f8fafc; border-radius: 8px; border: 1px solid var(--border);">
          <div class="service-metric-item">
            <span class="service-metric-label" style="font-size:0.75rem; color:var(--text-muted); display:block;">Travel Duration</span>
            <span class="service-metric-val">⏱️ <b>~${leg.travel_minutes} mins</b> ${durationHoursText ? `<small style="color:var(--text-muted);">(~${durationHoursText})</small>` : ""}</span>
          </div>
          <div class="service-metric-item">
            <span class="service-metric-label" style="font-size:0.75rem; color:var(--text-muted); display:block;">Distance</span>
            <span class="service-metric-val">📍 <b>${leg.distance_km.toFixed(1)} km</b></span>
          </div>
          <div class="service-metric-item">
            <span class="service-metric-label" style="font-size:0.75rem; color:var(--text-muted); display:block;">Leg Fare</span>
            <span class="service-metric-val">💵 <b>BDT ${leg.fare_bdt}</b></span>
          </div>
          <div class="service-metric-item">
            <span class="service-metric-label" style="font-size:0.75rem; color:var(--text-muted); display:block;">Timetable Wait</span>
            <span class="service-metric-val">⏳ <b>~${leg.waiting_minutes || 0} mins</b></span>
          </div>
        </div>

        <!-- Intermediate Stoppages Table (for trains or buses with stops) -->
        ${stoppageHtml}
      </div>
    </div>
  `;
}

// 2. Complete Single-Mode Leg Route Component for Multimodal
function renderMultimodalLegComponent(leg, legIdx, totalLegs, routeIdx) {
  const originName = cleanDistrictName(leg.origin) || leg.origin;
  const destName = cleanDistrictName(leg.destination) || leg.destination;
  const legNum = legIdx + 1;

  let legPath = (leg.path && leg.path.length >= 2) ? [...leg.path] : [];
  if (legPath.length < 2 && leg.stops && leg.stops.length >= 2) {
    legPath = leg.stops.map(s => {
      const st = s.station.trim();
      const dist = (s.district_name || "").trim();
      return (dist && dist.toLowerCase() !== st.toLowerCase()) ? `${st} (${dist})` : st;
    });
  }
  if (legPath.length < 2) {
    legPath = [leg.origin, leg.destination];
  }

  // Exact single-mode route timeline
  const legRouteObj = {
    path: legPath,
    kind: leg.mode,
    legs: [leg]
  };
  const legTimelineHtml = renderRouteTimeline(legRouteObj);
  const legDetailsHtml = renderSingleModeLegDetails(leg, legIdx, routeIdx);

  const rawDep = leg.departure || leg.departure_time;
  const dep = rawDep ? (rawDep.length > 5 ? rawDep.slice(0, 5) : rawDep) : "Estimated";

  return `
    <div class="mm-leg-block mode-${escapeHtml(leg.mode)}" id="mm-leg-block-${routeIdx}-${legIdx}">
      <!-- Leg Header -->
      <div class="mm-leg-header">
        <div class="mm-leg-header-left">
          <span class="mm-leg-num-badge ${escapeHtml(leg.mode)}">LEG ${legNum} OF ${totalLegs}</span>
          <span class="pill ${escapeHtml(leg.mode)}">${getModeBadge(leg.mode, 12)} ${escapeHtml(leg.mode.toUpperCase())}</span>
          <h4 class="mm-leg-title">${escapeHtml(originName)} ➔ ${escapeHtml(destName)}</h4>
          <span class="mm-leg-operator">&bull; ${escapeHtml(leg.service)}</span>
        </div>
        <div class="mm-leg-header-right">
          <span class="leg-fare-tag">BDT ${leg.fare_bdt}</span>
        </div>
      </div>

      <!-- Exact Single-Mode Route Timeline showing EVERY intermediate stop -->
      <div class="mm-leg-timeline-container">
        ${legTimelineHtml}
      </div>

      <!-- Single-Mode Route Overview Meta -->
      <div class="route-overview-meta mm-leg-meta">
        <span>📍 <strong>Distance:</strong> ${leg.distance_km.toFixed(1)} km</span>
        <span class="meta-dot">&bull;</span>
        <span>⏱️ <strong>Travel Duration:</strong> ~${leg.travel_minutes} mins</span>
        <span class="meta-dot">&bull;</span>
        <span>💵 <strong>Fare:</strong> BDT ${leg.fare_bdt}</span>
        <span class="meta-dot">&bull;</span>
        <span>🕒 <strong>Departure:</strong> ${escapeHtml(formatTimeAMPM(dep))}</span>
      </div>

      <!-- Expandable Button for this Leg -->
      <div class="mm-leg-toggle-bar">
        <button type="button" class="mm-section-toggle-btn mm-accordion-toggle-btn ${escapeHtml(leg.mode)}" id="mm-accordion-btn-${routeIdx}-leg-${legIdx}" data-section-id="leg-${legIdx}" data-default-label="View Leg ${legNum} Details" data-active-label="Hide Leg ${legNum} Details" onclick="toggleMultimodalAccordion('${routeIdx}', 'leg-${legIdx}')" aria-expanded="false">
          <span class="toggle-text">View Leg ${legNum} Details</span>
          <span class="toggle-icon">▼</span>
        </button>
      </div>

      <!-- Expandable Details Container for this Leg (Collapsed initially) -->
      <div id="mm-accordion-content-${routeIdx}-leg-${legIdx}" class="mm-accordion-content mm-nested-details-body hidden" style="display: none;">
        <div class="mm-leg-details-container">
          ${legDetailsHtml}
        </div>
      </div>
    </div>
  `;
}

function toggleMultimodalLegDetails(routeIdx, legIdx) {
  window.toggleMultimodalAccordion(routeIdx, `leg-${legIdx}`);
}
const toggleLegSection = toggleMultimodalLegDetails;
const renderIndependentLegCard = renderMultimodalLegComponent;
const renderCompactMultimodalLegCard = renderMultimodalLegComponent;

// 3. Independent Transfer Details Card (Independently Expandable per Transfer)
function renderIndependentTransferCard(currentLeg, nextLeg, transferIdx, routeIdx) {
  const tr = currentLeg.transfer_to_next;
  const needsPhysicalTransfer = checkPhysicalTransferRequired(currentLeg, nextLeg);
  const transferDistrict = cleanDistrictName(currentLeg.destination);
  const uniqueTransferId = `${routeIdx}-${transferIdx}`;

  if (!needsPhysicalTransfer) {
    const rawDep = nextLeg.departure || nextLeg.departure_time;
    const nextDepTime = (rawDep && String(rawDep).trim() && String(rawDep).slice(0, 5) !== "00:00")
      ? String(rawDep).slice(0, 5)
      : (tr?.target_arrival_time || tr?.next_departure_time || null);
    const rawArr = currentLeg.arrival || currentLeg.arrival_time;
    const prevArrTime = (rawArr && String(rawArr).trim())
      ? String(rawArr).slice(0, 5)
      : (tr?.prev_arrival_time || null);
    const nextDepMins = parseTimeToMinutes(nextDepTime);
    const prevArrMins = parseTimeToMinutes(prevArrTime);
    let readyDisplay = "Ready upon platform arrival";
    let bufferMins = null;
    if (nextDepMins != null && prevArrMins != null) {
      let rawDiff = nextDepMins - prevArrMins;
      if (rawDiff < 0) rawDiff += 1440;
      bufferMins = rawDiff - 15;
      const readyMins = (prevArrMins + 15) % 1440;
      readyDisplay = formatTimeAMPM(formatMinutesToTime(readyMins));
    }
    const prevArrDisplay = prevArrTime ? formatTimeAMPM(prevArrTime) : "Scheduled arrival";
    const nextDepDisplay = nextDepTime ? formatTimeAMPM(nextDepTime) : "Scheduled departure";
    const stationWaitDisplay = bufferMins !== null && bufferMins >= 0 ? formatWaitHoursAndMinutes(bufferMins) : "Direct interchange buffer";

    return `
      <div class="mm-compact-transfer-card buffer-comfortable" id="transfer-card-${uniqueTransferId}">
        <div class="mm-transfer-header">
          <div class="mm-transfer-title-wrap">
            <span class="mm-transfer-badge">🔄 DIRECT INTERCHANGE &mdash; ${escapeHtml(transferDistrict.toUpperCase())}</span>
            <div class="mm-transfer-path">
              <span class="mm-transfer-path-from">Same Station Platform Transfer at ${escapeHtml(transferDistrict)}</span>
            </div>
          </div>
          <span class="transfer-status-badge status-comfortable">Comfortable</span>
        </div>

        <div class="transfer-breakdown-grid">
          <div class="mm-transfer-metric">
            <span class="mm-tmetric-label">1. Previous Arrival</span>
            <span class="mm-tmetric-val">🏁 <b>${escapeHtml(prevArrDisplay)}</b></span>
            <span class="mm-tmetric-sub">${escapeHtml(transferDistrict)} Station</span>
          </div>
          <div class="mm-transfer-metric">
            <span class="mm-tmetric-label">2. Platform Walk Time</span>
            <span class="mm-tmetric-val">🚶 <b>~15 mins</b></span>
            <span class="mm-tmetric-sub">Same terminal (0.0 km)</span>
          </div>
          <div class="mm-transfer-metric">
            <span class="mm-tmetric-label">3. Ready-to-Board Time</span>
            <span class="mm-tmetric-val">🚪 <b>${escapeHtml(readyDisplay)}</b></span>
            <span class="mm-tmetric-sub">Platform ready</span>
          </div>
          <div class="mm-transfer-metric">
            <span class="mm-tmetric-label">4. Next Departure</span>
            <span class="mm-tmetric-val">🕒 <b>${escapeHtml(nextDepDisplay)}</b></span>
            <span class="mm-tmetric-sub">${escapeHtml(nextLeg.service)}</span>
          </div>
          <div class="mm-transfer-metric highlight-wait">
            <span class="mm-tmetric-label">5. Platform Waiting Time</span>
            <span class="mm-tmetric-val">⏳ <b class="highlight-wait-text">${escapeHtml(stationWaitDisplay)}</b></span>
            <span class="mm-tmetric-sub"><span class="transfer-status-chip status-comfortable">🛡️ Comfortable connection</span></span>
          </div>
        </div>

        <div class="mm-transfer-toggle-row">
          <button type="button" class="mm-section-toggle-btn mm-accordion-toggle-btn transfer" id="mm-accordion-btn-${routeIdx}-transfer-${transferIdx}" data-section-id="transfer-${transferIdx}" data-default-label="View Transfer Details" data-active-label="Hide Transfer Details" onclick="toggleMultimodalAccordion('${routeIdx}', 'transfer-${transferIdx}')" aria-expanded="false">
            <span class="toggle-text">View Transfer Details</span>
            <span class="toggle-icon">▼</span>
          </button>
        </div>

        <div id="mm-accordion-content-${routeIdx}-transfer-${transferIdx}" class="mm-accordion-content mm-nested-details-body hidden" style="display: none;">
          <div class="transfer-details-inner">
            <div class="transfer-timing-steps">
              <div>🏁 <strong>1. Previous Service Arrival:</strong> <b>${escapeHtml(prevArrDisplay)}</b> at ${escapeHtml(transferDistrict)} Station</div>
              <div>🚶 <strong>2. Platform Interchange Walk:</strong> <b>~15 minutes</b> (Direct same-station transfer)</div>
              <div>🚪 <strong>3. Ready-to-Board Time:</strong> <b>${escapeHtml(readyDisplay)}</b></div>
              <div>🕒 <strong>4. Connecting Service Departure:</strong> <b>${escapeHtml(nextDepDisplay)}</b> (${escapeHtml(nextLeg.service)})</div>
              <div>⏳ <strong>5. Platform Waiting Buffer:</strong> <b class="highlight-wait-text">${escapeHtml(stationWaitDisplay)}</b></div>
            </div>
            <div class="transfer-passenger-tip">
              💡 <strong>Direct Interchange Guidance:</strong> Switch connecting services directly at the terminal or platform at <b>${escapeHtml(transferDistrict)}</b>. No city road transit is required. Follow terminal signage to your connecting platform.
            </div>
          </div>
        </div>
      </div>
    `;
  }

  const transferFrom = tr?.from_location || formatTerminalName(currentLeg.destination, currentLeg.mode);
  const transferTo = tr?.to_location || formatTerminalName(nextLeg.origin, nextLeg.mode);
  const distKm = tr?.distance_km ?? 5.0;
  const mins = tr?.travel_minutes ?? (distKm <= 5 ? 15 : Math.round(distKm / 30 * 60));
  const fareBdt = tr?.fare_bdt ?? (distKm <= 5 ? 50 : Math.round(50 + 1.5 * (distKm - 10)));

  const rawDep = nextLeg.departure || nextLeg.departure_time;
  const nextDepTime = (rawDep && String(rawDep).trim() && String(rawDep).slice(0, 5) !== "00:00")
    ? String(rawDep).slice(0, 5)
    : (tr?.target_arrival_time || tr?.next_departure_time || null);

  const rawArr = currentLeg.arrival || currentLeg.arrival_time;
  const prevArrTime = (rawArr && String(rawArr).trim())
    ? String(rawArr).slice(0, 5)
    : (tr?.prev_arrival_time || null);

  const nextDepMins = parseTimeToMinutes(nextDepTime);
  const prevArrMins = parseTimeToMinutes(prevArrTime);

  let recLeaveDisplay = "Depart immediately upon arrival";
  if (nextDepMins != null) {
    const recMins = nextDepMins - mins;
    recLeaveDisplay = `${formatTimeAMPM(formatMinutesToTime(recMins))} or earlier`;
  } else if (tr?.recommended_leave_time) {
    recLeaveDisplay = `${formatTimeAMPM(tr.recommended_leave_time)} or earlier`;
  }

  let readyDisplay = "Ready after local transit";
  if (tr?.ready_to_board_time) {
    readyDisplay = formatTimeAMPM(tr.ready_to_board_time);
  } else if (prevArrMins != null) {
    const readyMins = (prevArrMins + mins) % 1440;
    readyDisplay = formatTimeAMPM(formatMinutesToTime(readyMins));
  }

  let bufferMins = null;
  if (nextDepMins != null && prevArrMins != null) {
    let rawDiff = nextDepMins - prevArrMins;
    if (rawDiff < 0) rawDiff += 1440;
    bufferMins = rawDiff - mins;
  } else if (tr?.buffer_minutes != null) {
    bufferMins = tr.buffer_minutes;
  }

  let statusText = "Comfortable Connection";
  let statusClass = "status-comfortable";
  let alertSeverityClass = "buffer-comfortable";
  let bufferDisplay = "Subject to timetable schedule";
  let stationWaitDisplay = "Schedule estimate unavailable";
  let warningPillHtml = "";

  if (bufferMins !== null) {
    if (bufferMins >= 25) {
      statusText = "Comfortable Connection";
      statusClass = "status-comfortable";
      alertSeverityClass = "buffer-comfortable";
      bufferDisplay = `~${bufferMins} mins buffer`;
      stationWaitDisplay = formatWaitHoursAndMinutes(bufferMins);
    } else if (bufferMins >= 0) {
      statusText = "Tight Connection";
      statusClass = "status-tight";
      alertSeverityClass = "buffer-tight";
      bufferDisplay = `~${bufferMins} mins remaining`;
      stationWaitDisplay = formatWaitHoursAndMinutes(bufferMins);
      warningPillHtml = `
        <div class="mm-transfer-warning-pill warning">
          ⚠️ <strong>Connection Warning:</strong> Connection window is tight (~${bufferMins} minutes remaining). Head straight to local transport upon arrival to avoid missing your connecting departure.
        </div>
      `;
    } else {
      statusText = bufferMins < -30 ? "Missed Connection" : "Risky Connection";
      statusClass = "status-risky";
      alertSeverityClass = "buffer-critical";
      bufferDisplay = `${Math.abs(bufferMins)} mins short`;
      stationWaitDisplay = `${Math.abs(bufferMins)}m short (infeasible)`;
      warningPillHtml = `
        <div class="mm-transfer-warning-pill critical">
          🚨 <strong>Critical Warning:</strong> Scheduled transit time exceeds next departure. This connection cannot reasonably be made on time. Please choose an earlier transport or later connecting service.
        </div>
      `;
    }
  } else if (tr?.station_waiting_minutes != null) {
    stationWaitDisplay = formatWaitHoursAndMinutes(tr.station_waiting_minutes);
    statusText = "Local Connection";
    statusClass = "status-info";
    alertSeverityClass = "buffer-info";
    bufferDisplay = nextDepTime ? `Reach terminal before ${formatTimeAMPM(nextDepTime)}` : "Schedule estimate unavailable";
  } else {
    statusText = "Local Connection";
    statusClass = "status-info";
    alertSeverityClass = "buffer-info";
    bufferDisplay = nextDepTime ? `Reach terminal before ${formatTimeAMPM(nextDepTime)}` : "Schedule estimate unavailable";
  }

  const prevArrDisplay = prevArrTime ? formatTimeAMPM(prevArrTime) : "Estimated arrival";
  const nextDepDisplay = nextDepTime ? formatTimeAMPM(nextDepTime) : "Schedule estimate unavailable";

  return `
    <div class="mm-compact-transfer-card ${alertSeverityClass}" id="transfer-card-${uniqueTransferId}">
      <!-- Always-Visible Compact Header & Path -->
      <div class="mm-transfer-header">
        <div class="mm-transfer-title-wrap">
          <span class="mm-transfer-badge">🛺 TRANSFER &mdash; ${escapeHtml(transferDistrict.toUpperCase())}</span>
          <div class="mm-transfer-path">
            <span class="mm-transfer-path-from">${escapeHtml(transferFrom)}</span>
            <span class="mm-transfer-path-arrow">➔</span>
            <span class="mm-transfer-path-to">${escapeHtml(transferTo)}</span>
          </div>
        </div>
        <span class="transfer-status-badge ${statusClass}">${statusText}</span>
      </div>

      <!-- Always-Visible 5-Metric Breakdown Grid -->
      <div class="transfer-breakdown-grid">
        <div class="mm-transfer-metric">
          <span class="mm-tmetric-label">1. Previous Arrival</span>
          <span class="mm-tmetric-val">🏁 <b>${escapeHtml(prevArrDisplay)}</b></span>
          <span class="mm-tmetric-sub">${escapeHtml(transferDistrict)} Arrival</span>
        </div>
        <div class="mm-transfer-metric">
          <span class="mm-tmetric-label">2. Local Transfer Time</span>
          <span class="mm-tmetric-val">🛺 <b>~${mins} mins</b></span>
          <span class="mm-tmetric-sub">${distKm.toFixed(1)} km road transit</span>
        </div>
        <div class="mm-transfer-metric">
          <span class="mm-tmetric-label">3. Ready-to-Board Time</span>
          <span class="mm-tmetric-val">🚪 <b>${escapeHtml(readyDisplay)}</b></span>
          <span class="mm-tmetric-sub">At connecting terminal</span>
        </div>
        <div class="mm-transfer-metric">
          <span class="mm-tmetric-label">4. Next Departure</span>
          <span class="mm-tmetric-val">🕒 <b>${escapeHtml(nextDepDisplay)}</b></span>
          <span class="mm-tmetric-sub">${escapeHtml(nextLeg.service)}</span>
        </div>
        <div class="mm-transfer-metric highlight-wait">
          <span class="mm-tmetric-label">5. Station Waiting Time</span>
          <span class="mm-tmetric-val">⏳ <b class="highlight-wait-text">${escapeHtml(stationWaitDisplay)}</b></span>
          <span class="mm-tmetric-sub"><span class="transfer-status-chip ${statusClass}">${statusText}</span></span>
        </div>
      </div>

      <!-- Independent Transfer View Details Control -->
      <div class="mm-transfer-toggle-row">
        <button type="button" class="mm-section-toggle-btn mm-accordion-toggle-btn transfer" id="mm-accordion-btn-${routeIdx}-transfer-${transferIdx}" data-section-id="transfer-${transferIdx}" data-default-label="View Transfer Details" data-active-label="Hide Transfer Details" onclick="toggleMultimodalAccordion('${routeIdx}', 'transfer-${transferIdx}')" aria-expanded="false">
          <span class="toggle-text">View Transfer Details</span>
          <span class="toggle-icon">▼</span>
        </button>
      </div>

      <!-- Expandable Details Body (Collapsed by Default) -->
      <div id="mm-accordion-content-${routeIdx}-transfer-${transferIdx}" class="mm-accordion-content mm-nested-details-body hidden" style="display: none;">
        ${warningPillHtml}

        <div class="transfer-details-inner">
          <div class="transfer-timing-steps">
            <div>🏁 <strong>1. Previous Service Arrival (${escapeHtml(transferFrom)}):</strong> <b>${escapeHtml(prevArrDisplay)}</b></div>
            <div>🛺 <strong>2. Local Transfer Transit:</strong> <b>~${mins} minutes</b> (${distKm.toFixed(1)} km) &bull; Suggested: Auto-rickshaw / CNG / Local shuttle (~BDT ${fareBdt})</div>
            <div>🚪 <strong>3. Passenger Ready-to-Board Time (${escapeHtml(transferTo)}):</strong> <b>${escapeHtml(readyDisplay)}</b></div>
            <div>🕒 <strong>4. Connecting Service Departure (${escapeHtml(transferTo)}):</strong> <b>${escapeHtml(nextDepDisplay)}</b> (${escapeHtml(nextLeg.service)})</div>
            <div>⏳ <strong>5. Actual Station Waiting Time:</strong> <b class="highlight-wait-text">${escapeHtml(stationWaitDisplay)}</b></div>
            <div>🚪 <strong>Recommended Local Departure Time:</strong> <b>${escapeHtml(recLeaveDisplay)}</b></div>
          </div>
          <div class="transfer-passenger-tip">
            💡 <strong>Connection Breakdown:</strong> Your arriving transport reaches <b>${escapeHtml(transferFrom)}</b> at <b>${escapeHtml(prevArrDisplay)}</b>. Allow <b>${mins} minutes</b> for transit between terminals, making you ready to board at <b>${escapeHtml(transferTo)}</b> by <b>${escapeHtml(readyDisplay)}</b>. You will then have <b>${escapeHtml(stationWaitDisplay)}</b> of station waiting time before the <b>${escapeHtml(nextDepDisplay)}</b> departure.
          </div>
        </div>
      </div>
    </div>
  `;
}

// 4. Overall Journey Statistics Section (Independently Expandable)
function renderIndependentStatsSection(route, routeIdx) {
  const expectedMins = route.in_journey_minutes || route.travel_time?.expected_minutes || Math.round(((route.travel_time?.minimum_minutes || 0) + (route.travel_time?.maximum_minutes || 0)) / 2) || 0;
  const minMins = route.travel_time?.minimum_minutes || expectedMins;
  const maxMins = route.travel_time?.maximum_minutes || expectedMins;
  const firstLeg = (route.legs && route.legs.length > 0) ? route.legs[0] : null;
  const initialWaitMins = route.initial_waiting_minutes ?? firstLeg?.waiting_minutes ?? route.waiting_minutes ?? 0;
  const totalDoorMins = route.total_journey_minutes ?? (expectedMins + initialWaitMins);

  return `
    <div class="mm-subcard mm-stats-card" id="stats-card-${routeIdx}">
      <div class="mm-subcard-header" id="stats-header-${routeIdx}">
        <div class="mm-subcard-header-left">
          <div class="mm-subcard-title-line">
            <span class="section-num-pill info">03</span>
            <span class="mm-subcard-title">Overall Journey Statistics</span>
          </div>
          <div class="mm-subcard-preview">
            <span>📍 ${route.distance_km.toFixed(1)} km &bull; ⏱️ In-Journey: ~${formatMinutesRange(minMins, maxMins)} &bull; ⏳ Wait: ${formatWaitHoursAndMinutes(initialWaitMins)}</span>
          </div>
        </div>
        <div class="mm-subcard-header-right">
          <button type="button" class="mm-section-toggle-btn info" id="stats-toggle-btn-${routeIdx}" onclick="toggleStatsSection('${routeIdx}')" aria-expanded="false">
            <span class="toggle-text">View Journey Statistics</span>
            <span class="toggle-icon">▼</span>
          </button>
        </div>
      </div>
      <div id="stats-details-${routeIdx}" class="mm-nested-details-body hidden" style="display: none;">
        <div class="journey-stats-grid">
          <div class="stat-card">
            <span class="stat-icon">📍</span>
            <div class="stat-data">
              <span class="stat-label">Total Distance</span>
              <span class="stat-value">${route.distance_km.toFixed(1)} km</span>
            </div>
          </div>
          <div class="stat-card highlight-duration">
            <span class="stat-icon">⏱️</span>
            <div class="stat-data">
              <span class="stat-label">In-Journey Transit</span>
              <span class="stat-value">${minMins}–${maxMins} mins</span>
              <span class="stat-sub">(~${formatMinutesRange(minMins, maxMins)})</span>
            </div>
          </div>
          <div class="stat-card">
            <span class="stat-icon">⏳</span>
            <div class="stat-data">
              <span class="stat-label">Initial Waiting Time</span>
              <span class="stat-value highlight-wait-text">${formatWaitHoursAndMinutes(initialWaitMins)}</span>
            </div>
          </div>
          <div class="stat-card">
            <span class="stat-icon">🏁</span>
            <div class="stat-data">
              <span class="stat-label">Total Door-to-Door</span>
              <span class="stat-value" style="color: #0f766e;">~${formatMinutesToHours(totalDoorMins)}</span>
            </div>
          </div>
          <div class="stat-card">
            <span class="stat-icon">🔄</span>
            <div class="stat-data">
              <span class="stat-label">Transfers</span>
              <span class="stat-value">${route.transfers === 0 ? "Direct (0)" : `${route.transfers} Transfer${route.transfers > 1 ? "s" : ""}`}</span>
            </div>
          </div>
          <div class="stat-card">
            <span class="stat-icon">🛡️</span>
            <div class="stat-data">
              <span class="stat-label">Confidence</span>
              <span class="stat-value">${escapeHtml(route.confidence || "medium").toUpperCase()}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
}

// 5. Waiting Time & Timetable Notices Section (Independently Expandable)
function renderIndependentWaitingSection(route, routeIdx, originDist) {
  const firstLeg = (route.legs && route.legs.length > 0) ? route.legs[0] : null;
  const initialWaitMins = route.initial_waiting_minutes ?? firstLeg?.waiting_minutes ?? route.waiting_minutes ?? 0;
  const initialWaitFormatted = formatWaitHoursAndMinutes(initialWaitMins);

  const rawDep = route.next_departure_time || firstLeg?.departure || firstLeg?.departure_time;
  const nextDepTime = (rawDep && String(rawDep).trim() && String(rawDep).slice(0, 5) !== "00:00")
    ? String(rawDep).slice(0, 5)
    : null;
  const depDisplay = nextDepTime ? formatTimeAMPM(nextDepTime) : "Next scheduled departure";

  const modeName = route.next_departure_mode || firstLeg?.mode || "Transport";
  const serviceName = route.next_departure_service || firstLeg?.service || "Scheduled Transport";
  const boardingLoc = route.next_departure_location || (firstLeg ? formatTerminalName(firstLeg.origin, firstLeg.mode) : originDist);

  // Calculate total station waiting across transfers
  let totalStationWaitMins = 0;
  let hasTransfers = false;
  if (route.legs && route.legs.length > 1) {
    hasTransfers = true;
    for (let i = 0; i < route.legs.length - 1; i++) {
      const curLeg = route.legs[i];
      const nxtLeg = route.legs[i + 1];
      const tr = curLeg.transfer_to_next;
      const mins = tr?.travel_minutes ?? 15;
      const nxtD = nxtLeg.departure || nxtLeg.departure_time;
      const curA = curLeg.arrival || curLeg.arrival_time;
      const nMins = parseTimeToMinutes(nxtD ? String(nxtD).slice(0, 5) : null);
      const aMins = parseTimeToMinutes(curA ? String(curA).slice(0, 5) : null);
      if (nMins != null && aMins != null) {
        let diff = nMins - aMins;
        if (diff < 0) diff += 1440;
        const bMins = diff - mins;
        if (bMins > 0) totalStationWaitMins += bMins;
      } else if (tr?.station_waiting_minutes != null && tr.station_waiting_minutes > 0) {
        totalStationWaitMins += tr.station_waiting_minutes;
      } else if (tr?.buffer_minutes != null && tr.buffer_minutes > 0) {
        totalStationWaitMins += tr.buffer_minutes;
      }
    }
  }

  const inJourneyMins = route.in_journey_minutes ?? route.travel_time?.expected_minutes ?? 0;
  const totalDoorToDoorMins = route.total_journey_minutes ?? (inJourneyMins + initialWaitMins);

  return `
    <div class="mm-subcard mm-waiting-card" id="waiting-card-${routeIdx}">
      <div class="mm-subcard-header" id="waiting-header-${routeIdx}">
        <div class="mm-subcard-header-left">
          <div class="mm-subcard-title-line">
            <span class="section-num-pill warning">04</span>
            <span class="mm-subcard-title">Waiting Time &amp; Timetable Notices</span>
          </div>
          <div class="mm-subcard-preview">
            <span>⏳ Next scheduled departure wait: <b class="highlight-wait-text">${escapeHtml(initialWaitFormatted)}</b> &bull; Departs ${escapeHtml(depDisplay)} from ${escapeHtml(originDist)}</span>
          </div>
        </div>
        <div class="mm-subcard-header-right">
          <button type="button" class="mm-section-toggle-btn warning" id="waiting-toggle-btn-${routeIdx}" onclick="toggleWaitingSection('${routeIdx}')" aria-expanded="false">
            <span class="toggle-text">View Waiting Time &amp; Notices</span>
            <span class="toggle-icon">▼</span>
          </button>
        </div>
      </div>
      <div id="waiting-details-${routeIdx}" class="mm-nested-details-body hidden" style="display: none;">
        <div class="waiting-dedicated-card initial-wait-card">
          <div class="waiting-icon-wrap">⏳</div>
          <div class="waiting-content">
            <div class="waiting-head">
              <span class="waiting-label">Waiting Time for Next Transport</span>
              <span class="waiting-time-val highlight">${escapeHtml(initialWaitFormatted)}</span>
            </div>
            <p class="waiting-subtext">
              Next departure: <strong>${escapeHtml(depDisplay)}</strong> from <strong>${escapeHtml(boardingLoc)}</strong>.
              This waiting time represents the elapsed time before the passenger can begin the journey from the origin.
            </p>

            <div class="waiting-next-service-meta">
              <div class="meta-item">
                <span class="meta-label">Transport Mode</span>
                <span class="meta-val">${getModeBadge(modeName, 13)} <b>${escapeHtml(String(modeName).toUpperCase())}</b></span>
              </div>
              <div class="meta-item">
                <span class="meta-label">Service / Train Number</span>
                <span class="meta-val"><b>${escapeHtml(serviceName)}</b></span>
              </div>
              <div class="meta-item">
                <span class="meta-label">Scheduled Departure</span>
                <span class="meta-val">🕒 <b>${escapeHtml(depDisplay)}</b></span>
              </div>
              <div class="meta-item">
                <span class="meta-label">Boarding Station</span>
                <span class="meta-val">📍 <b>${escapeHtml(boardingLoc)}</b></span>
              </div>
            </div>
          </div>
        </div>

        ${hasTransfers ? `
        <div class="waiting-time-breakdown-card" style="margin-top: 12px; padding: 12px 14px; background: #ffffff; border: 1px solid var(--border); border-radius: 8px;">
          <div style="font-weight: 700; font-size: 0.86rem; color: var(--primary-text); margin-bottom: 8px;">
            ⏱️ Complete Journey Time Breakdown (Door-to-Door)
          </div>
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px;">
            <div class="meta-item">
              <span class="meta-label">1. Pre-Departure Wait (Origin)</span>
              <span class="meta-val highlight-wait-text">⏳ <b>${escapeHtml(initialWaitFormatted)}</b></span>
            </div>
            <div class="meta-item">
              <span class="meta-label">2. Active In-Journey Transit</span>
              <span class="meta-val">🛺 <b>~${formatWaitHoursAndMinutes(inJourneyMins)}</b></span>
            </div>
            <div class="meta-item">
              <span class="meta-label">3. Station Waiting (Interchanges)</span>
              <span class="meta-val">⏳ <b>~${formatWaitHoursAndMinutes(totalStationWaitMins)}</b></span>
            </div>
            <div class="meta-item">
              <span class="meta-label">Total Door-to-Door Time</span>
              <span class="meta-val" style="font-weight: 800; color: #0f766e;">🏁 <b>~${formatWaitHoursAndMinutes(totalDoorToDoorMins)}</b></span>
            </div>
          </div>
        </div>
        ` : ""}
      </div>
    </div>
  `;
}

// 6. Journey Information & Route Disclaimers Section (Independently Expandable)
function renderIndependentDisclaimersSection(route, routeIdx) {
  const warningsList = (route.warnings || []).map((warning) =>
    `<div class="disclaimer-item warning-bullet"><span class="bullet-dot">⚠️</span> <span>${escapeHtml(warning)}</span></div>`
  ).join("");

  return `
    <div class="mm-subcard mm-disclaimers-card" id="disclaimers-card-${routeIdx}">
      <div class="mm-subcard-header" id="disclaimers-header-${routeIdx}">
        <div class="mm-subcard-header-left">
          <div class="mm-subcard-title-line">
            <span class="section-num-pill info">05</span>
            <span class="mm-subcard-title">Journey Information &amp; Route Disclaimers</span>
          </div>
          <div class="mm-subcard-preview">
            <span>ℹ️ ${(route.warnings || []).length} Advisory Notice${(route.warnings || []).length === 1 ? '' : 's'} &bull; Operational Transit Policies</span>
          </div>
        </div>
        <div class="mm-subcard-header-right">
          <button type="button" class="mm-section-toggle-btn info" id="disclaimers-toggle-btn-${routeIdx}" onclick="toggleDisclaimersSection('${routeIdx}')" aria-expanded="false">
            <span class="toggle-text">View Route Disclaimers</span>
            <span class="toggle-icon">▼</span>
          </button>
        </div>
      </div>
      <div id="disclaimers-details-${routeIdx}" class="mm-nested-details-body hidden" style="display: none;">
        <div class="combined-disclaimer-card">
          <div class="disclaimer-header">
            <span class="disclaimer-icon">ℹ️</span>
            <strong>Official Transit Disclaimers &amp; Operating Policies</strong>
          </div>
          <div class="disclaimer-body">
            ${warningsList}
            <div class="disclaimer-item static-note">
              📌 Travel durations and arrival windows are estimates calculated from scheduled timetable intervals and standard highway/railway speeds. Actual journey times may vary due to real-time traffic, weather, or operational transit conditions.
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
}

// Aliases for backwards compatibility
const renderCompactTransferCard = renderIndependentTransferCard;

// 4. View Total Details at Bottom (Mutually Exclusive Accordion Section)
function renderCompleteTotalDetailsSection(route, routeIdx, originDist, destDist) {
  const legs = route.legs || [];
  const firstLeg = legs.length > 0 ? legs[0] : null;

  const initialWaitMins = route.initial_waiting_minutes ?? firstLeg?.waiting_minutes ?? route.waiting_minutes ?? 0;
  const initialWaitFormatted = formatWaitHoursAndMinutes(initialWaitMins);

  const rawFirstDep = route.next_departure_time || firstLeg?.departure || firstLeg?.departure_time;
  const firstDepTime = (rawFirstDep && String(rawFirstDep).trim() && String(rawFirstDep).slice(0, 5) !== "00:00")
    ? String(rawFirstDep).slice(0, 5)
    : null;
  const firstDepDisplay = firstDepTime ? formatTimeAMPM(firstDepTime) : "Scheduled";

  let totalTransferTransitMins = 0;
  let totalStationWaitMins = 0;
  let totalTransferFareBdt = 0;
  const transferItems = [];

  for (let i = 0; i < legs.length - 1; i++) {
    const curLeg = legs[i];
    const nxtLeg = legs[i + 1];
    const tr = curLeg.transfer_to_next;
    const isPhysical = checkPhysicalTransferRequired(curLeg, nxtLeg);
    const distKm = isPhysical ? (tr?.distance_km ?? 5.0) : 0;
    const transitMins = isPhysical ? (tr?.travel_minutes ?? (distKm <= 5 ? 15 : Math.round(distKm / 30 * 60))) : 15;
    const fare = isPhysical ? (tr?.fare_bdt ?? (distKm <= 5 ? 50 : Math.round(50 + 1.5 * (distKm - 10)))) : 0;

    totalTransferTransitMins += transitMins;
    totalTransferFareBdt += fare;

    const nxtD = nxtLeg.departure || nxtLeg.departure_time;
    const curA = curLeg.arrival || curLeg.arrival_time;
    const nMins = parseTimeToMinutes(nxtD ? String(nxtD).slice(0, 5) : null);
    const aMins = parseTimeToMinutes(curA ? String(curA).slice(0, 5) : null);
    let bufMins = null;
    if (nMins != null && aMins != null) {
      let diff = nMins - aMins;
      if (diff < 0) diff += 1440;
      bufMins = diff - transitMins;
      if (bufMins > 0) totalStationWaitMins += bufMins;
    } else if (tr?.station_waiting_minutes != null && tr.station_waiting_minutes > 0) {
      bufMins = tr.station_waiting_minutes;
      totalStationWaitMins += bufMins;
    } else if (tr?.buffer_minutes != null && tr.buffer_minutes > 0) {
      bufMins = tr.buffer_minutes;
      totalStationWaitMins += bufMins;
    }

    transferItems.push({
      idx: i + 1,
      from: isPhysical ? (tr?.from_location || formatTerminalName(curLeg.destination, curLeg.mode)) : `${cleanDistrictName(curLeg.destination)} Station`,
      to: isPhysical ? (tr?.to_location || formatTerminalName(nxtLeg.origin, nxtLeg.mode)) : `${cleanDistrictName(nxtLeg.origin)} Platform`,
      distKm,
      transitMins,
      stationWaitMins: (bufMins !== null && bufMins > 0) ? bufMins : 0,
      fare,
      isPhysical
    });
  }

  const activeTransitMins = legs.reduce((sum, l) => sum + (l.travel_minutes || 0), 0) + totalTransferTransitMins;
  const totalOverallWaitMins = initialWaitMins + totalStationWaitMins;
  const totalDoorMins = route.total_journey_minutes ?? (initialWaitMins + activeTransitMins + totalStationWaitMins);

  const totalDistanceKm = route.distance_km || legs.reduce((sum, l) => sum + (l.distance_km || 0), 0);
  const legFaresTotal = legs.reduce((sum, l) => sum + (l.fare_bdt || 0), 0);
  const totalFareBdt = route.fare_bdt || (legFaresTotal + totalTransferFareBdt);

  // Overall connection status
  let overallConnStatus = "Comfortable Connection";
  let overallConnClass = "status-comfortable";
  let hasPhysicalTransfer = transferItems.some(t => t.isPhysical);
  if (!hasPhysicalTransfer && route.transfers > 0) {
    overallConnStatus = "Direct Interchange";
    overallConnClass = "status-comfortable";
  }

  // Cost breakdown lines
  const costLinesHtml = legs.map((leg, idx) => {
    let transferLine = "";
    if (idx < legs.length - 1) {
      const t = transferItems[idx];
      if (t && t.isPhysical) {
        transferLine = `
          <div class="mm-cost-item-row transfer">
            <span class="cost-item-label">🛺 Transfer ${t.idx}: ${escapeHtml(t.from)} ➔ ${escapeHtml(t.to)} (Local Transit / CNG)</span>
            <span class="cost-item-val">BDT ${t.fare}</span>
          </div>
        `;
      } else if (t) {
        transferLine = `
          <div class="mm-cost-item-row transfer free">
            <span class="cost-item-label">🚶 Transfer ${t.idx}: Same-station platform interchange</span>
            <span class="cost-item-val">BDT 0 (Free)</span>
          </div>
        `;
      }
    }
    return `
      <div class="mm-cost-item-row">
        <span class="cost-item-label">${getModeBadge(leg.mode, 12)} Leg ${idx + 1} (${escapeHtml(leg.mode.toUpperCase())}): <b>${escapeHtml(leg.service)}</b> &mdash; ${escapeHtml(cleanDistrictName(leg.origin))} ➔ ${escapeHtml(cleanDistrictName(leg.destination))}</span>
        <span class="cost-item-val">BDT ${leg.fare_bdt}</span>
      </div>
      ${transferLine}
    `;
  }).join("");

  // Door-to-door timeline steps
  let doorToDoorStepsHtml = `
    <div class="d2d-step-item">
      <div class="d2d-step-num">1</div>
      <div class="d2d-step-content">
        <div class="d2d-step-title">Pre-Departure Wait at Origin (${escapeHtml(originDist)})</div>
        <div class="d2d-step-desc">Time elapsed before the first scheduled service departs (${escapeHtml(firstDepDisplay)})</div>
      </div>
      <div class="d2d-step-time highlight-wait-text">⏳ ${escapeHtml(initialWaitFormatted)}</div>
    </div>
  `;

  let stepCounter = 2;
  legs.forEach((leg, idx) => {
    doorToDoorStepsHtml += `
      <div class="d2d-step-item">
        <div class="d2d-step-num">${stepCounter++}</div>
        <div class="d2d-step-content">
          <div class="d2d-step-title">Leg ${idx + 1} Travel Time: ${escapeHtml(cleanDistrictName(leg.origin))} ➔ ${escapeHtml(cleanDistrictName(leg.destination))}</div>
          <div class="d2d-step-desc">${getModeBadge(leg.mode, 11)} ${escapeHtml(leg.mode.toUpperCase())} &bull; ${escapeHtml(leg.service)} &bull; ${leg.distance_km.toFixed(1)} km</div>
        </div>
        <div class="d2d-step-time">⏱️ ~${leg.travel_minutes} mins</div>
      </div>
    `;

    if (idx < legs.length - 1) {
      const t = transferItems[idx];
      if (t) {
        doorToDoorStepsHtml += `
          <div class="d2d-step-item transfer">
            <div class="d2d-step-num">${stepCounter++}</div>
            <div class="d2d-step-content">
              <div class="d2d-step-title">Transfer Transit Time (${escapeHtml(cleanDistrictName(leg.destination))})</div>
              <div class="d2d-step-desc">${t.isPhysical ? `🛺 ${escapeHtml(t.from)} ➔ ${escapeHtml(t.to)} (${t.distKm.toFixed(1)} km road transit)` : `🚶 Direct same-station platform walk`}</div>
            </div>
            <div class="d2d-step-time">~${t.transitMins} mins</div>
          </div>
          <div class="d2d-step-item wait">
            <div class="d2d-step-num">${stepCounter++}</div>
            <div class="d2d-step-content">
              <div class="d2d-step-title">Station Waiting Buffer (${escapeHtml(cleanDistrictName(leg.destination))})</div>
              <div class="d2d-step-desc">Safety buffer before connecting departure departs</div>
            </div>
            <div class="d2d-step-time highlight-wait-text">⏳ ~${formatWaitHoursAndMinutes(t.stationWaitMins)}</div>
          </div>
        `;
      }
    }
  });

  const warningsList = (route.warnings || []).map((warning) =>
    `<div class="disclaimer-item warning-bullet"><span class="bullet-dot">⚠️</span> <span>${escapeHtml(warning)}</span></div>`
  ).join("");

  return `
    <div class="mm-complete-total-details-container">
      <!-- 1. Overall Journey Summary Cards -->
      <div class="mm-total-summary-header">
        <h4 class="mm-total-summary-title">📊 Complete Overall Journey Summary</h4>
        <span class="mm-total-summary-sub">${escapeHtml(originDist)} ➔ ${escapeHtml(destDist)} &bull; ${legs.length} Transport Legs &bull; ${route.transfers} Transfer${route.transfers === 1 ? '' : 's'}</span>
      </div>

      <div class="journey-stats-grid mm-total-stats-grid">
        <div class="stat-card highlight-duration">
          <span class="stat-icon">🏁</span>
          <div class="stat-data">
            <span class="stat-label">Total Door-to-Door Duration</span>
            <span class="stat-value" style="color: #0f766e;">~${formatMinutesToHours(totalDoorMins)}</span>
            <span class="stat-sub">(${totalDoorMins} mins elapsed)</span>
          </div>
        </div>
        <div class="stat-card">
          <span class="stat-icon">💵</span>
          <div class="stat-data">
            <span class="stat-label">Total Journey Fare</span>
            <span class="stat-value" style="color: var(--primary-green);">BDT ${totalFareBdt}</span>
            <span class="stat-sub">All legs &amp; local transfers included</span>
          </div>
        </div>
        <div class="stat-card">
          <span class="stat-icon">📍</span>
          <div class="stat-data">
            <span class="stat-label">Total Distance</span>
            <span class="stat-value">${totalDistanceKm.toFixed(1)} km</span>
            <span class="stat-sub">${legs.length} transport legs</span>
          </div>
        </div>
        <div class="stat-card">
          <span class="stat-icon">⏳</span>
          <div class="stat-data">
            <span class="stat-label">Total Waiting Time</span>
            <span class="stat-value highlight-wait-text">${formatWaitHoursAndMinutes(totalOverallWaitMins)}</span>
            <span class="stat-sub">Origin (${initialWaitFormatted}) + Interchanges</span>
          </div>
        </div>
        <div class="stat-card">
          <span class="stat-icon">🔄</span>
          <div class="stat-data">
            <span class="stat-label">Total Legs &amp; Transfers</span>
            <span class="stat-value">${legs.length} Legs / ${route.transfers} Transfer${route.transfers === 1 ? '' : 's'}</span>
            <span class="stat-sub"><span class="${overallConnClass}">${overallConnStatus}</span></span>
          </div>
        </div>
        <div class="stat-card">
          <span class="stat-icon">⏱️</span>
          <div class="stat-data">
            <span class="stat-label">Active In-Journey Transit</span>
            <span class="stat-value">~${formatMinutesToHours(activeTransitMins)}</span>
            <span class="stat-sub">${activeTransitMins} mins on vehicles</span>
          </div>
        </div>
      </div>

      <!-- 2. Breakdown of Leg Fares + Transfer Costs -->
      <div class="mm-cost-breakdown-card" style="margin-top: 14px; background: #ffffff; border: 1px solid var(--border); border-radius: 8px; padding: 14px 16px;">
        <div style="font-weight: 700; font-size: 0.9rem; color: var(--primary-text); margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between;">
          <span>💵 Breakdown of Leg Fares &amp; Transfer Costs</span>
          <span style="font-size: 0.82rem; color: var(--text-muted);">Sum of all journey segments</span>
        </div>
        <div class="mm-cost-table" style="display: flex; flex-direction: column; gap: 8px;">
          ${costLinesHtml}
          <div class="mm-cost-item-row total" style="display: flex; justify-content: space-between; padding-top: 10px; border-top: 2px solid var(--border); font-weight: 800; font-size: 0.95rem; color: var(--primary-text);">
            <span>Total Estimated Expenditure:</span>
            <span style="color: var(--primary-green);">BDT ${totalFareBdt}</span>
          </div>
        </div>
      </div>

      <!-- 3. Door-to-Door Time Breakdown -->
      <div class="mm-timeline-breakdown-card" style="margin-top: 14px; background: #ffffff; border: 1px solid var(--border); border-radius: 8px; padding: 14px 16px;">
        <div style="font-weight: 700; font-size: 0.9rem; color: var(--primary-text); margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between;">
          <span>⏱️ Door-to-Door Journey Time Breakdown</span>
          <span style="font-size: 0.82rem; color: var(--text-muted);">From requested departure to final destination</span>
        </div>
        <div class="d2d-steps-list" style="display: flex; flex-direction: column; gap: 8px;">
          ${doorToDoorStepsHtml}
          <div class="d2d-step-item total" style="display: flex; justify-content: space-between; align-items: center; padding: 10px 12px; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; font-weight: 800;">
            <span style="color: #166534;">Total Door-to-Door Journey Duration:</span>
            <span style="color: #166534; font-size: 1.05rem;">~${formatMinutesToHours(totalDoorMins)} (${totalDoorMins} mins)</span>
          </div>
        </div>
      </div>

      <!-- 4. Route Disclaimers & Operating Policies -->
      <div class="combined-disclaimer-card" style="margin-top: 14px;">
        <div class="disclaimer-header">
          <span class="disclaimer-icon">ℹ️</span>
          <strong>Official Transit Disclaimers &amp; Operating Policies</strong>
        </div>
        <div class="disclaimer-body">
          ${warningsList}
          <div class="disclaimer-item static-note">
            📌 Travel durations and arrival windows are estimates calculated from scheduled timetable intervals and standard highway/railway speeds. Actual journey times may vary due to real-time traffic, weather, or operational transit conditions.
          </div>
          <div class="disclaimer-item static-note">
            🛡️ Local transfer times between terminals include estimated city road traffic. Passengers are advised to proceed directly to the transfer connection upon arrival.
          </div>
        </div>
      </div>
    </div>
  `;
}

function renderMultimodalRouteCard(route, routeIdx = 0) {
  const originDist = cleanDistrictName(route.path[0]) || route.path[0];
  const destDist = cleanDistrictName(route.path[route.path.length - 1]) || route.path[route.path.length - 1];
  const legs = route.legs || [];

  let disruptionAlertsHtml = "";
  if (route.is_affected && route.disruption_alerts && route.disruption_alerts.length) {
    disruptionAlertsHtml = route.disruption_alerts.map((alert) => `
      <div class="disruption-alert-card severity-${escapeHtml((alert.severity || "moderate").toLowerCase())}">
        <div class="disruption-header">
          <span class="disruption-badge">${escapeHtml(alert.severity || "ALERT")}</span>
          <span class="disruption-mode-tag">⚠️ ${escapeHtml((alert.transport_mode || 'TRANSPORT').toUpperCase())} DISRUPTION &mdash; ${escapeHtml((alert.location || '').toUpperCase())}</span>
          <span class="disruption-title"><strong>${escapeHtml(alert.title)}</strong></span>
        </div>
        <div class="disruption-body">
          <p class="disruption-msg">${escapeHtml(alert.message)}</p>
          <div class="disruption-meta">
            <span>📍 <b>Affected Section:</b> ${escapeHtml(alert.affected_segment || alert.location)}</span>
            <span>⚡ <b>Incident:</b> ${escapeHtml(alert.cause)}</span>
            <span>🛡️ <b>Status:</b> ${escapeHtml(alert.status)}</span>
            ${alert.estimated_end_time ? `<span>⏱️ <b>Est. Clearance:</b> ${escapeHtml(alert.estimated_end_time.replace("T", " ").slice(0, 16))}</span>` : ""}
          </div>
        </div>
      </div>
    `).join("");
  }

  // Generate Vertical Sequence of Complete Single-Mode Legs and Transfers
  const legsAndTransfersHtml = [];
  for (let i = 0; i < legs.length; i++) {
    legsAndTransfersHtml.push(renderMultimodalLegComponent(legs[i], i, legs.length, routeIdx));
    if (i < legs.length - 1) {
      legsAndTransfersHtml.push(renderIndependentTransferCard(legs[i], legs[i + 1], i, routeIdx));
    }
  }

  return `
    <article class="route-card mm-route-card" id="route-card-${routeIdx}">
      <!-- Multimodal Card Header -->
      <div class="route-section-block section-route-overview mm-journey-summary-block" style="border-bottom: none; padding-bottom: 8px;">
        <div class="route-overview-header">
          <div class="route-heading-group">
            <span class="pill multimodal">${getModeBadge("multimodal", 13)} Multimodal</span>
            <h3 class="route-main-heading">${escapeHtml(originDist)} ➔ ${escapeHtml(destDist)}</h3>
          </div>
          <div class="route-header-actions">
            <button type="button" class="save-fav-btn" onclick="saveFavouriteRoute('${escapeHtml(originDist)}', '${escapeHtml(destDist)}')">
              ⭐ Save Route
            </button>
            <button type="button" class="save-fav-btn" onclick="openReportForRoute('${escapeHtml(originDist)}', '${escapeHtml(destDist)}', 'multimodal')">
              🚩 Report Issue
            </button>
            <div class="fare-summary-chip">
              <span class="fare-summary-label">Total Fare</span>
              <span class="fare-summary-val">BDT ${route.fare_bdt}</span>
            </div>
          </div>
        </div>
        ${disruptionAlertsHtml}
      </div>

      <!-- Chronological Vertical Sequence of Complete Single-Mode Legs and Transfers -->
      <div class="mm-vertical-legs-sequence" style="padding: 0 16px 12px; background: transparent; border-bottom: none;">
        ${legsAndTransfersHtml.join("")}
      </div>

      <!-- Bottom Section: View Total Details ▼ Button & Collapsed Container -->
      <div class="mm-bottom-total-section" style="padding: 6px 16px 18px;">
        <div class="mm-total-details-toggle-bar" style="display: flex; justify-content: center; padding: 10px 0;">
          <button type="button" class="mm-section-toggle-btn mm-accordion-toggle-btn total" id="mm-accordion-btn-${routeIdx}-total" data-section-id="total" data-default-label="View Total Details" data-active-label="Hide Total Details" onclick="toggleMultimodalAccordion('${routeIdx}', 'total')" aria-expanded="false" style="padding: 8px 24px; font-size: 0.88rem; font-weight: 700;">
            <span class="toggle-text">View Total Details</span>
            <span class="toggle-icon">▼</span>
          </button>
        </div>

        <div id="mm-accordion-content-${routeIdx}-total" class="mm-accordion-content mm-nested-details-body hidden" style="display: none; border: 1px solid var(--border); border-radius: 8px; margin-top: 10px;">
          ${renderCompleteTotalDetailsSection(route, routeIdx, originDist, destDist)}
        </div>
      </div>
    </article>
  `;
}

// Backwards compatibility aliases
const renderMultimodalLegsSection = renderMultimodalRouteCard;
const renderMultimodalOverview = renderMultimodalRouteCard;

// 5. Shared Mutually Exclusive Multimodal Accordion State & Handler
window.multimodalActiveSections = window.multimodalActiveSections || {};

window.toggleMultimodalAccordion = function(routeIdx, targetSectionId) {
  const card = document.getElementById(`route-card-${routeIdx}`);
  if (!card) return;

  const currentActive = window.multimodalActiveSections[routeIdx] || null;

  // Find all accordion toggle buttons and content panels within this route card
  const allContents = card.querySelectorAll(".mm-accordion-content");
  const allButtons = card.querySelectorAll(".mm-accordion-toggle-btn");

  // If user clicked the currently active section, collapse it (close all sections)
  if (currentActive === targetSectionId) {
    allContents.forEach(el => {
      el.style.display = "none";
      el.classList.add("hidden");
    });
    allButtons.forEach(btn => {
      btn.setAttribute("aria-expanded", "false");
      btn.classList.remove("active");
      const defLabel = btn.getAttribute("data-default-label") || "View Details";
      const textEl = btn.querySelector(".toggle-text");
      if (textEl) textEl.textContent = defLabel;
      const iconEl = btn.querySelector(".toggle-icon");
      if (iconEl) iconEl.textContent = "▼";
    });
    window.multimodalActiveSections[routeIdx] = null;
    return;
  }

  // Otherwise, collapse all sections first
  allContents.forEach(el => {
    el.style.display = "none";
    el.classList.add("hidden");
  });
  allButtons.forEach(btn => {
    btn.setAttribute("aria-expanded", "false");
    btn.classList.remove("active");
    const defLabel = btn.getAttribute("data-default-label") || "View Details";
    const textEl = btn.querySelector(".toggle-text");
    if (textEl) textEl.textContent = defLabel;
    const iconEl = btn.querySelector(".toggle-icon");
    if (iconEl) iconEl.textContent = "▼";
  });

  // Now expand the single targeted section
  const targetContent = document.getElementById(`mm-accordion-content-${routeIdx}-${targetSectionId}`);
  const targetBtn = document.getElementById(`mm-accordion-btn-${routeIdx}-${targetSectionId}`);

  if (targetContent) {
    targetContent.style.display = "block";
    targetContent.classList.remove("hidden");
  }

  if (targetBtn) {
    targetBtn.setAttribute("aria-expanded", "true");
    targetBtn.classList.add("active");
    const activeLabel = targetBtn.getAttribute("data-active-label") || "Hide Details";
    const textEl = targetBtn.querySelector(".toggle-text");
    if (textEl) textEl.textContent = activeLabel;
    const iconEl = targetBtn.querySelector(".toggle-icon");
    if (iconEl) iconEl.textContent = "▲";
  }

  window.multimodalActiveSections[routeIdx] = targetSectionId;
};

function renderRouteCard(route, routeIdx = 0) {
  const originDist = cleanDistrictName(route.path[0]) || route.path[0];
  const destDist = cleanDistrictName(route.path[route.path.length - 1]) || route.path[route.path.length - 1];
  const isMultimodal = (route.kind && route.kind.toLowerCase() === "multimodal") || (route.legs && route.legs.length > 1);

  if (isMultimodal) {
    return renderMultimodalRouteCard(route, routeIdx);
  }

  // Section 02 Legs (Departure & Arrival per leg/operator)
  const legs = (route.legs || []).map((leg, legIdx) => {
    const rawDep = leg.departure || leg.departure_time;
    const dep = rawDep ? (rawDep.length > 5 ? rawDep.slice(0, 5) : rawDep) : "Estimated";
    const rawArr = leg.arrival || leg.arrival_time;
    const arr = rawArr ? (rawArr.length > 5 ? rawArr.slice(0, 5) : rawArr) : "Estimated";
    const stoppageHtml = (leg.stops && leg.stops.length > 0) ? renderStoppages(leg.stops) : "";
    const estArrivalWindow = calculateArrivalWindow(dep, leg.travel_minutes);

    let transferHtml = "";
    const tr = leg.transfer_to_next;
    const nextLeg = (legIdx < route.legs.length - 1) ? route.legs[legIdx + 1] : null;

    if (nextLeg) {
      const needsPhysicalTransfer = checkPhysicalTransferRequired(leg, nextLeg);
      if (needsPhysicalTransfer) {
        const fromLoc = tr?.from_location || formatTerminalName(leg.destination, leg.mode);
        const toLoc = tr?.to_location || formatTerminalName(nextLeg.origin, nextLeg.mode);
        const dist = tr?.distance_km ?? 5.0;
        const mins = tr?.travel_minutes ?? (dist <= 5 ? 15 : Math.round(dist / 30 * 60));
        const alertHtml = renderConnectionAlert(tr, leg, nextLeg);

        transferHtml = `
          <div class="leg-transfer-connector">
            <div class="transfer-connector-top">
              <span class="mode-icon-badge local interactive" title="Station Transfer">
                <svg class="mode-svg" viewBox="0 0 24 24" width="13" height="13" fill="currentColor">
                  <path d="M18.92 6.01C18.72 5.42 18.16 5 17.5 5h-11c-.66 0-1.22.42-1.42 1.01L3 12v8c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1h12v1c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-8l-2.08-5.99zM6.85 7h10.29l1.04 3H5.81l1.04-3zM19 17H5v-4.66l.12-.34h13.77l.11.34V17z"/>
                  <circle cx="7.5" cy="14.5" r="1.5"/>
                  <circle cx="16.5" cy="14.5" r="1.5"/>
                </svg>
              </span>
              <div class="transfer-connector-heading">
                <strong>Transfer Required: ${escapeHtml(fromLoc)} ➔ ${escapeHtml(toLoc)}</strong>
                <span class="transfer-pill">Use Local Transport</span>
              </div>
            </div>
            <div class="transfer-connector-meta">
              <span>📍 <strong>Distance:</strong> ${dist.toFixed(1)} km</span>
              <span>⏱️ <strong>Est. Transfer Time:</strong> ~${mins} mins</span>
              <span>🚕 <strong>Transport:</strong> Auto-rickshaw / CNG / Local shuttle</span>
            </div>
            ${alertHtml}
          </div>
        `;
      }
    }

    let legDisruptionHtml = "";
    if (leg.is_affected && leg.disruption_alerts && leg.disruption_alerts.length) {
      legDisruptionHtml = leg.disruption_alerts.map((alert) => `
        <div class="leg-disruption-alert severity-${escapeHtml((alert.severity || "moderate").toLowerCase())}">
          <span class="leg-disruption-icon">⚠️</span>
          <div class="leg-disruption-text">
            <strong>${escapeHtml(alert.severity)} Incident: ${escapeHtml(alert.title)}</strong>
            <p>${escapeHtml(alert.message)}</p>
          </div>
        </div>
      `).join("");
    }

    return `
      <div class="operator-leg-card">
        <div class="operator-header">
          <div class="operator-info">
            <span class="pill ${escapeHtml(leg.mode)}">${getModeBadge(leg.mode, 12)} ${escapeHtml(leg.mode)}</span>
            <span class="operator-name"><strong>${escapeHtml(leg.service)}</strong></span>
          </div>
          <div class="operator-meta-right">
            <span class="leg-fare-tag">BDT ${leg.fare_bdt}</span>
          </div>
        </div>
        ${legDisruptionHtml}

        <div class="departure-arrival-row">
          <div class="time-block departure">
            <span class="time-label">Departure</span>
            <span class="time-value">🕒 <b>${escapeHtml(dep)}</b></span>
            <span class="time-station">${escapeHtml(formatTerminalName(leg.origin, leg.mode))}</span>
          </div>
          <div class="time-divider">➔</div>
          <div class="time-block arrival">
            <span class="time-label">Estimated Arrival Window</span>
            <span class="time-value">🏁 <b>${escapeHtml(estArrivalWindow)}</b></span>
            <span class="time-station">${escapeHtml(formatTerminalName(leg.destination, leg.mode))}</span>
          </div>
        </div>
        ${stoppageHtml}
      </div>
      ${transferHtml}
    `;
  }).join("");

  // Section 04 Warnings / Disclaimers
  const warningsList = (route.warnings || []).map((warning) =>
    `<div class="disclaimer-item warning-bullet"><span class="bullet-dot">⚠️</span> <span>${escapeHtml(warning)}</span></div>`
  ).join("");

  let disruptionAlertsHtml = "";
  if (route.is_affected && route.disruption_alerts && route.disruption_alerts.length) {
    disruptionAlertsHtml = route.disruption_alerts.map((alert) => `
      <div class="disruption-alert-card severity-${escapeHtml((alert.severity || "moderate").toLowerCase())}">
        <div class="disruption-header">
          <span class="disruption-badge">${escapeHtml(alert.severity || "ALERT")}</span>
          <span class="disruption-mode-tag">⚠️ ${escapeHtml((alert.transport_mode || 'TRANSPORT').toUpperCase())} DISRUPTION &mdash; ${escapeHtml((alert.location || '').toUpperCase())}</span>
          <span class="disruption-title"><strong>${escapeHtml(alert.title)}</strong></span>
        </div>
        <div class="disruption-body">
          <p class="disruption-msg">${escapeHtml(alert.message)}</p>
          <div class="disruption-meta">
            <span>📍 <b>Affected Section:</b> ${escapeHtml(alert.affected_segment || alert.location)}</span>
            <span>⚡ <b>Incident:</b> ${escapeHtml(alert.cause)}</span>
            <span>🛡️ <b>Status:</b> ${escapeHtml(alert.status)}</span>
            ${alert.estimated_end_time ? `<span>⏱️ <b>Est. Clearance:</b> ${escapeHtml(alert.estimated_end_time.replace("T", " ").slice(0, 16))}</span>` : ""}
            ${alert.source_name ? `<span>📰 <b>Source:</b> ${escapeHtml(alert.source_name)}</span>` : ""}
          </div>
        </div>
      </div>
    `).join("");
  }

  return `
    <article class="route-card" id="route-card-${routeIdx}">
      <!-- 01 Route Overview -->
      <div class="route-section-block section-route-overview">
        <div class="section-badge-row">
          <span class="section-num-pill">01</span>
          <span class="section-title-label">Route Overview</span>
        </div>

        <div class="route-overview-header">
          <div class="route-heading-group">
            <span class="pill ${escapeHtml(route.kind)}">${getModeBadge(route.kind, 13)} ${escapeHtml(route.kind)}</span>
            <h3 class="route-main-heading">${escapeHtml(originDist)} ➔ ${escapeHtml(destDist)}</h3>
          </div>
          <div class="route-header-actions">
            <button type="button" class="save-fav-btn" onclick="saveFavouriteRoute('${escapeHtml(originDist)}', '${escapeHtml(destDist)}')">
              ⭐ Save Route
            </button>
            <button type="button" class="save-fav-btn" onclick="openReportForRoute('${escapeHtml(originDist)}', '${escapeHtml(destDist)}', '${escapeHtml(route.kind)}')">
              🚩 Report Issue
            </button>
            <div class="fare-summary-chip">
              <span class="fare-summary-label">Total Fare</span>
              <span class="fare-summary-val">BDT ${route.fare_bdt}</span>
            </div>
          </div>
        </div>
        ${disruptionAlertsHtml}

        <!-- Visual Route Timeline (District-based for all routes) -->
        ${renderRouteTimeline(route)}

        <div class="route-overview-meta">
          <span>📍 <strong>Total Distance:</strong> ${route.distance_km.toFixed(1)} km</span>
          <span class="meta-dot">&bull;</span>
          <span>🔄 <strong>Transfers:</strong> ${route.transfers === 0 ? "Direct (0 transfers)" : `${route.transfers} transfer${route.transfers > 1 ? "s" : ""}`}</span>
          <span class="meta-dot">&bull;</span>
          <span>🛡️ <strong>Confidence:</strong> ${escapeHtml(route.confidence).toUpperCase()}</span>
        </div>

        <!-- Separate Multimodal Transport Legs & Connection Guidance (Rendered ONLY when isMultimodal is true) -->
        ${isMultimodal ? renderMultimodalLegsSection(route) : ""}
      </div>

      <!-- Dropdown / Collapsible Details Bar -->
      <div class="route-dropdown-bar" id="route-toggle-bar-${routeIdx}" onclick="toggleRouteDetails(${routeIdx})" role="button" tabindex="0" aria-expanded="false" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();toggleRouteDetails(${routeIdx});}">
        <div class="route-dropdown-bar-left">
          <span class="route-dropdown-bar-icon">📋</span>
          <div class="route-dropdown-bar-text">
            <span class="route-dropdown-bar-title">${isMultimodal ? "View Overall Journey Statistics &amp; Notices" : "View Departure, Statistics &amp; Waiting Info"}</span>
            <span class="route-dropdown-bar-subtitle">${route.legs.length} Leg${route.legs.length > 1 ? "s" : ""} &bull; ${route.transfers > 0 ? `${route.transfers} Transfer${route.transfers > 1 ? "s" : ""}` : "Direct"} &bull; Total ${route.distance_km.toFixed(1)} km</span>
          </div>
        </div>
        <div class="route-dropdown-bar-right">
          <span class="route-dropdown-label">View Details</span>
          <span class="route-dropdown-chevron">▼</span>
        </div>
      </div>

      <!-- Collapsible Sections: 02 (for single-mode), 03, 04 -->
      <div id="route-details-${routeIdx}" class="route-details-collapsible collapsed" style="display: none;">
        ${!isMultimodal ? `
        <!-- 02 Departure & Arrival -->
        <div class="route-section-block section-departure-arrival">
          <div class="section-badge-row">
            <span class="section-num-pill transport">02</span>
            <span class="section-title-label">Departure &amp; Arrival</span>
          </div>
          <div class="departure-arrival-list">
            ${legs}
          </div>
        </div>
        ` : ""}

        <!-- 03 Journey Statistics -->
        <div class="route-section-block section-journey-stats">
          <div class="section-badge-row">
            <span class="section-num-pill info">${isMultimodal ? "02" : "03"}</span>
            <span class="section-title-label">${isMultimodal ? "Overall Journey Statistics" : "Journey Statistics"}</span>
          </div>
          <div class="journey-stats-grid">
            <div class="stat-card">
              <span class="stat-icon">📍</span>
              <div class="stat-data">
                <span class="stat-label">Total Distance</span>
                <span class="stat-value">${route.distance_km.toFixed(1)} km</span>
              </div>
            </div>
            <div class="stat-card highlight-duration">
              <span class="stat-icon">⏱️</span>
              <div class="stat-data">
                <span class="stat-label">Travel Duration</span>
                <span class="stat-value">${route.travel_time.minimum_minutes}–${route.travel_time.maximum_minutes} mins</span>
                <span class="stat-sub">(~${formatMinutesRange(route.travel_time.minimum_minutes, route.travel_time.maximum_minutes)})</span>
              </div>
            </div>
            <div class="stat-card">
              <span class="stat-icon">🔄</span>
              <div class="stat-data">
                <span class="stat-label">Transfers</span>
                <span class="stat-value">${route.transfers === 0 ? "Direct (0)" : `${route.transfers} Transfer${route.transfers > 1 ? "s" : ""}`}</span>
              </div>
            </div>
            <div class="stat-card">
              <span class="stat-icon">🛡️</span>
              <div class="stat-data">
                <span class="stat-label">Confidence</span>
                <span class="stat-value">${escapeHtml(route.confidence).toUpperCase()}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 04 Waiting Time & Notices -->
        <div class="route-section-block section-waiting-notices">
          <div class="section-badge-row">
            <span class="section-num-pill warning">${isMultimodal ? "03" : "04"}</span>
            <span class="section-title-label">Waiting Time &amp; Notices</span>
          </div>
          <div class="waiting-notices-container">
            <div class="waiting-dedicated-card">
              <div class="waiting-icon-wrap">⏳</div>
              <div class="waiting-content">
                <div class="waiting-head">
                  <span class="waiting-label">Waiting Time for Next Transport</span>
                  <span class="waiting-time-val">${formatWaitTime(route.waiting_minutes)}</span>
                </div>
                <p class="waiting-subtext">Estimated wait until the next scheduled departure from <strong>${escapeHtml(originDist)}</strong> based on current timetable frequency.</p>
              </div>
            </div>

            <div class="combined-disclaimer-card">
              <div class="disclaimer-header">
                <span class="disclaimer-icon">ℹ️</span>
                <strong>Journey Information &amp; Route Disclaimers</strong>
              </div>
              <div class="disclaimer-body">
                ${warningsList}
                <div class="disclaimer-item static-note">
                  📌 Travel durations and arrival windows are estimates calculated from scheduled timetable intervals and standard highway/railway speeds. Actual journey times may vary due to real-time traffic, weather, or operational transit conditions.
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </article>
  `;
}

window.toggleRouteDetails = function(idx) {
  const mmTotalBtn = document.getElementById(`mm-accordion-btn-${idx}-total`);
  if (mmTotalBtn) {
    window.toggleMultimodalAccordion(idx, "total");
    return;
  }

  const detailsEl = document.getElementById(`route-details-${idx}`);
  const toggleBar = document.getElementById(`route-toggle-bar-${idx}`);
  const card = document.getElementById(`route-card-${idx}`);
  if (!detailsEl || !toggleBar) return;

  const isCollapsed = detailsEl.style.display === "none" || detailsEl.classList.contains("collapsed");
  const isMultimodal = toggleBar.classList.contains("mm-complete-details-bar") || toggleBar.classList.contains("mm-notices-bar");

  if (isCollapsed) {
    detailsEl.style.display = "block";
    detailsEl.classList.remove("collapsed");
    detailsEl.classList.add("expanded");
    toggleBar.classList.add("active");
    toggleBar.setAttribute("aria-expanded", "true");
    if (card) card.classList.add("route-expanded");
    const label = toggleBar.querySelector(".route-dropdown-label");
    if (label) label.textContent = isMultimodal ? "Hide Full Journey Details" : "Hide Details";
    const title = toggleBar.querySelector(".mm-complete-details-title") || toggleBar.querySelector(".route-dropdown-bar-title");
    if (title && isMultimodal) title.textContent = "Hide Full Journey Details";
    const chevron = toggleBar.querySelector(".route-dropdown-chevron");
    if (chevron) chevron.textContent = "▲";
  } else {
    detailsEl.style.display = "none";
    detailsEl.classList.remove("expanded");
    detailsEl.classList.add("collapsed");
    toggleBar.classList.remove("active");
    toggleBar.setAttribute("aria-expanded", "false");
    if (card) card.classList.remove("route-expanded");
    const label = toggleBar.querySelector(".route-dropdown-label");
    if (label) label.textContent = isMultimodal ? "View Full Journey Details" : "View Details";
    const title = toggleBar.querySelector(".mm-complete-details-title") || toggleBar.querySelector(".route-dropdown-bar-title");
    if (title && isMultimodal) title.textContent = "View Full Journey Details";
    const chevron = toggleBar.querySelector(".route-dropdown-chevron");
    if (chevron) chevron.textContent = "▼";
  }
};

const OFFICIAL_64_DISTRICTS = [
  "Bagerhat", "Bandarban", "Barguna", "Barishal", "Bhola", "Bogura", "Brahmanbaria", "Chandpur",
  "Chapainawabganj", "Chattogram", "Chuadanga", "Cox's Bazar", "Cumilla", "Dhaka", "Dinajpur",
  "Faridpur", "Feni", "Gaibandha", "Gazipur", "Gopalganj", "Habiganj", "Jamalpur", "Jashore",
  "Jhalokathi", "Jhenaidah", "Joypurhat", "Khagrachhari", "Khulna", "Kishoreganj", "Kurigram",
  "Kushtia", "Lakshmipur", "Lalmonirhat", "Madaripur", "Magura", "Manikganj", "Meherpur",
  "Moulvibazar", "Munshiganj", "Mymensingh", "Naogaon", "Narail", "Narayanganj", "Narsingdi",
  "Natore", "Netrokona", "Nilphamari", "Noakhali", "Pabna", "Panchagarh", "Patuakhali",
  "Pirojpur", "Rajbari", "Rajshahi", "Rangamati", "Rangpur", "Satkhira", "Shariatpur",
  "Sherpur", "Sirajganj", "Sunamganj", "Sylhet", "Tangail", "Thakurgaon"
];

const DISTRICT_ALIASES = {
  "chapai": "Chapainawabganj",
  "chapai nawabganj": "Chapainawabganj",
  "nawabganj": "Chapainawabganj",
  "coxs": "Cox's Bazar",
  "cox's": "Cox's Bazar",
  "coxs bazar": "Cox's Bazar",
  "cox bazar": "Cox's Bazar",
  "chittagong": "Chattogram",
  "comilla": "Cumilla",
  "jessore": "Jashore",
  "barisal": "Barishal",
  "bogra": "Bogura",
  "dacca": "Dhaka",
  "mymensing": "Mymensingh",
  "b.baria": "Brahmanbaria",
  "b baria": "Brahmanbaria",
  "baria": "Brahmanbaria",
  "brahmanbaria": "Brahmanbaria",
  "netrokona": "Netrokona",
  "netrakona": "Netrokona"
};

let allDistricts = [...OFFICIAL_64_DISTRICTS];

function resolveDistrictName(inputStr) {
  const clean = (inputStr || "").trim();
  if (!clean) return null;
  const lower = clean.toLowerCase();

  // 1. Direct case-insensitive match against 64 official districts
  const exact = allDistricts.find((d) => d.toLowerCase() === lower);
  if (exact) return exact;

  // 2. Direct match in alias dictionary
  if (DISTRICT_ALIASES[lower]) {
    return DISTRICT_ALIASES[lower];
  }

  // 3. Word-boundary or prefix alias match (e.g. "chittagong city" -> "Chattogram")
  for (const [alias, canonical] of Object.entries(DISTRICT_ALIASES)) {
    if (lower === alias || lower.startsWith(alias + " ") || lower.startsWith(alias + ",")) {
      return canonical;
    }
  }

  // 4. Unique starts-with match in canonical list (e.g. "Brah" -> "Brahmanbaria")
  const starts = allDistricts.filter((d) => d.toLowerCase().startsWith(lower));
  if (starts.length === 1) {
    return starts[0];
  }

  return null;
}

function highlightMatch(text, query) {
  if (!query) return escapeHtml(text);
  const q = query.toLowerCase();
  const lowerText = text.toLowerCase();
  const idx = lowerText.indexOf(q);
  if (idx === -1) return escapeHtml(text);
  const before = text.substring(0, idx);
  const matched = text.substring(idx, idx + query.length);
  const after = text.substring(idx + query.length);
  return `${escapeHtml(before)}<span class="sugg-highlight">${escapeHtml(matched)}</span>${escapeHtml(after)}`;
}

function populateDistrictsDatalist(districts) {
  const list = $("#districts-list");
  if (!list) return;
  list.replaceChildren();
  for (const name of districts) {
    const option = document.createElement("option");
    option.value = name;
    list.append(option);
  }
}
populateDistrictsDatalist(allDistricts);

function setupDistrictDropdown(input) {
  if (!input) return;

  const parent = input.parentElement;
  if (!parent) return;

  // Clean up any previously attached dropdown
  parent.querySelectorAll(".district-suggestions-dropdown").forEach((el) => el.remove());
  parent.style.position = "relative";
  input.setAttribute("autocomplete", "off");
  // Remove native browser datalist association so both don't pop up simultaneously
  input.removeAttribute("list");

  // Create custom dropdown element
  const dropdown = document.createElement("div");
  dropdown.className = "district-suggestions-dropdown hidden";
  dropdown.setAttribute("role", "listbox");
  dropdown.setAttribute("aria-label", "Bangladesh Districts Suggestions");
  parent.appendChild(dropdown);

  let activeIndex = -1;
  let currentMatches = [];

  function closeDropdown() {
    dropdown.classList.add("hidden");
    activeIndex = -1;
  }

  function selectItem(name) {
    input.value = name;
    input.classList.remove("input-invalid");
    closeDropdown();
    input.dispatchEvent(new Event("change", { bubbles: true }));

    // Auto-focus next field if selecting origin
    if (input.id === "origin") {
      const dest = $("#destination");
      if (dest && !dest.value) {
        dest.focus();
      }
    } else if (input.id === "bus-origin") {
      const dest = $("#bus-destination");
      if (dest && !dest.value) dest.focus();
    } else if (input.id === "train-origin") {
      const dest = $("#train-destination");
      if (dest && !dest.value) dest.focus();
    }
  }

  function render(query = "") {
    const q = (query || "").trim().toLowerCase();
    activeIndex = -1;

    let matches = [];
    const aliasNotes = {};

    if (!q) {
      // If query is empty, show all 64 districts alphabetically
      matches = [...allDistricts].sort((a, b) => a.localeCompare(b));
    } else {
      // Check alias matches
      const aliasDistricts = [];
      for (const [alias, canonical] of Object.entries(DISTRICT_ALIASES)) {
        if (alias.startsWith(q) || q.startsWith(alias)) {
          if (allDistricts.includes(canonical) && !aliasDistricts.includes(canonical)) {
            aliasDistricts.push(canonical);
            aliasNotes[canonical] = `Matched alias: "${alias}"`;
          }
        }
      }

      // Starts with
      const starts = allDistricts
        .filter((d) => d.toLowerCase().startsWith(q) && !aliasDistricts.includes(d))
        .sort((a, b) => a.localeCompare(b));

      // Contains
      const contains = allDistricts
        .filter((d) => d.toLowerCase().includes(q) && !d.toLowerCase().startsWith(q) && !aliasDistricts.includes(d))
        .sort((a, b) => a.localeCompare(b));

      // Deduplicate suggestions
      const seen = new Set();
      const unique = [];
      for (const item of [...aliasDistricts, ...starts, ...contains]) {
        if (!seen.has(item)) {
          seen.add(item);
          unique.push(item);
        }
      }
      matches = unique;
    }

    currentMatches = matches;

    if (matches.length === 0) {
      dropdown.innerHTML = `
        <div class="district-suggestions-header">
          <span>64 Districts of Bangladesh</span>
          <span class="match-count-badge">0 matches</span>
        </div>
        <div class="district-no-match">
          No Bangladesh district matching "<strong>${escapeHtml(query)}</strong>"
        </div>
      `;
      dropdown.classList.remove("hidden");
      return;
    }

    const itemsHtml = matches.map((name, i) => {
      const pill = name.charAt(0).toUpperCase();
      const highlighted = highlightMatch(name, q);
      const noteHtml = aliasNotes[name] ? `<span class="sugg-alias-tag">${escapeHtml(aliasNotes[name])}</span>` : "";
      return `
        <div class="district-suggestion-item" role="option" data-idx="${i}" data-district="${escapeHtml(name)}">
          <span class="sugg-letter-pill">${pill}</span>
          <div class="sugg-name-wrap">
            <span class="sugg-name">${highlighted}</span>
            ${noteHtml}
          </div>
          <span class="sugg-select-arrow">➔</span>
        </div>
      `;
    }).join("");

    dropdown.innerHTML = `
      <div class="district-suggestions-header">
        <span>64 Districts of Bangladesh</span>
        <span class="match-count-badge">${matches.length} district${matches.length === 1 ? '' : 's'}</span>
      </div>
      <div class="district-suggestions-list" style="max-height: 230px; overflow-y: auto;">
        ${itemsHtml}
      </div>
    `;

    dropdown.classList.remove("hidden");
  }

  function updateActiveHighlight() {
    const items = dropdown.querySelectorAll(".district-suggestion-item");
    items.forEach((item, idx) => {
      const isAct = idx === activeIndex;
      item.classList.toggle("active", isAct);
      if (isAct) {
        item.scrollIntoView({ block: "nearest", behavior: "smooth" });
      }
    });
  }

  // Keyboard navigation
  input.addEventListener("keydown", (e) => {
    if (dropdown.classList.contains("hidden")) {
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        render(input.value);
        return;
      }
    }

    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (currentMatches.length > 0) {
        activeIndex = (activeIndex + 1) % currentMatches.length;
        updateActiveHighlight();
      }
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (currentMatches.length > 0) {
        activeIndex = activeIndex <= 0 ? currentMatches.length - 1 : activeIndex - 1;
        updateActiveHighlight();
      }
    } else if (e.key === "Enter") {
      if (!dropdown.classList.contains("hidden") && currentMatches.length > 0) {
        e.preventDefault();
        const selected = activeIndex >= 0 ? currentMatches[activeIndex] : currentMatches[0];
        selectItem(selected);
      }
    } else if (e.key === "Escape") {
      closeDropdown();
    } else if (e.key === "Tab") {
      closeDropdown();
    }
  });

  // Open & filter on focus and input
  input.addEventListener("focus", () => {
    render(input.value);
  });

  input.addEventListener("input", () => {
    input.classList.remove("input-invalid");
    render(input.value);
  });

  // Mouse hover highlight
  dropdown.addEventListener("mouseover", (e) => {
    const item = e.target.closest(".district-suggestion-item");
    if (item && item.dataset.idx !== undefined) {
      activeIndex = parseInt(item.dataset.idx, 10);
      updateActiveHighlight();
    }
  });

  // Mouse selection (mousedown fires before input blur)
  dropdown.addEventListener("mousedown", (e) => {
    const item = e.target.closest(".district-suggestion-item");
    if (item && item.dataset.district) {
      e.preventDefault();
      selectItem(item.dataset.district);
    }
  });

  // Blur with auto-standardization
  input.addEventListener("blur", () => {
    setTimeout(() => {
      closeDropdown();
      const val = input.value.trim();
      if (val) {
        const canonical = resolveDistrictName(val);
        if (canonical) {
          input.value = canonical;
          input.classList.remove("input-invalid");
        }
      }
    }, 180);
  });

  // Close dropdown on outside click anywhere on document
  document.addEventListener("click", (e) => {
    if (!parent.contains(e.target)) {
      closeDropdown();
    }
  });
}

function setupDistrictAutocomplete(selector) {
  const input = document.querySelector(selector);
  if (input) {
    setupDistrictDropdown(input);
  }
}

async function loadDistricts() {
  try {
    const items = await api("/api/districts");
    if (items && items.length > 0) {
      allDistricts = items;
      populateDistrictsDatalist(allDistricts);
    }
  } catch (error) {
    console.warn("Could not load supported districts from API, using default list:", error.message);
  }

  // Attach interactive dropdown to all district inputs
  const selectors = [
    "#origin",
    "#destination",
    "#bus-origin",
    "#bus-destination",
    "#train-origin",
    "#train-destination",
    "#local-district",
    "#fav-origin",
    "#fav-dest",
  ];
  selectors.forEach(setupDistrictAutocomplete);
}

function populateDepartureTimes() {
  const timeSelect = $("#departure-time");
  if (!timeSelect) return;
  const travelDateInput = $("#travel-date");
  const isToday = travelDateInput ? travelDateInput.value === localDate() : true;

  const now = new Date();
  const currentMinutes = now.getHours() * 60 + now.getMinutes();
  // If traveling today: hide slots prior to the current 15-minute interval (e.g. at 11:47 PM, hide prior to 11:45 PM)
  const pastThresholdMinutes = Math.floor(currentMinutes / 15) * 15;
  // Automatically round up to the next upcoming 15-minute slot
  const roundedUpMinutes = Math.min(23 * 60 + 45, Math.ceil(currentMinutes / 15) * 15);
  const roundedUpVal = `${String(Math.floor(roundedUpMinutes / 60)).padStart(2, "0")}:${String(roundedUpMinutes % 60).padStart(2, "0")}`;

  const previousVal = timeSelect.value;
  timeSelect.replaceChildren();

  let firstAvailableVal = "";

  for (let mins = 0; mins < 24 * 60; mins += 15) {
    // If traveling today, hide past departure slots
    if (isToday && mins < pastThresholdMinutes) {
      continue;
    }

    const h = Math.floor(mins / 60);
    const m = mins % 60;
    const timeVal = `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;

    const period = h >= 12 ? "PM" : "AM";
    const h12 = h % 12 === 0 ? 12 : h % 12;
    const label = `${String(h12).padStart(2, "0")}:${String(m).padStart(2, "0")} ${period}`;

    const option = document.createElement("option");
    option.value = timeVal;
    option.textContent = `${label} (${timeVal})`;
    timeSelect.append(option);

    if (!firstAvailableVal) {
      firstAvailableVal = timeVal;
    }
  }

  // If traveling today and it's late night (after 11:45 PM), provide last slot so select is not empty
  if (timeSelect.options.length === 0) {
    const option = document.createElement("option");
    option.value = "23:45";
    option.textContent = "11:45 PM (23:45)";
    timeSelect.append(option);
    firstAvailableVal = "23:45";
  }

  if (previousVal && Array.from(timeSelect.options).some((o) => o.value === previousVal)) {
    timeSelect.value = previousVal;
  } else if (Array.from(timeSelect.options).some((o) => o.value === roundedUpVal)) {
    timeSelect.value = roundedUpVal;
  } else {
    timeSelect.value = firstAvailableVal;
  }
}

// Initial dates and departure time slots
const today = localDate();
const travelDateField = $("#travel-date");
if (travelDateField) {
  travelDateField.value = today;
  travelDateField.min = today;
  travelDateField.addEventListener("change", () => {
    travelDateField.classList.remove("input-invalid");
    if (travelDateField.value && travelDateField.value < localDate()) {
      travelDateField.value = localDate();
      showStatus("Past dates are not allowed. Date reset to today.", "info");
    }
    populateDepartureTimes();
  });
  travelDateField.addEventListener("click", function() {
    try {
      if (typeof this.showPicker === "function") this.showPicker();
    } catch (_) {}
  });
}
populateDepartureTimes();

// Active state tracking
let activeJourneyMode = "all";
let lastJourneyData = null;

// -------------------------------------------------------------
// Top Navigation & Main View Routing
// -------------------------------------------------------------
let activePage = "journey";

function getPageFromUrl() {
  const path = (window.location.pathname || "").toLowerCase().replace(/^\/+|\/+$/g, "");
  const hash = (window.location.hash || "").toLowerCase().replace(/^#\/?/, "");

  if (path === "timetables" || hash === "timetables") return "timetables";
  return "journey";
}

function switchMainPage(page, options = {}) {
  if (!["journey", "timetables"].includes(page)) {
    page = "journey";
  }
  activePage = page;

  // Update top navigation link active states and aria attributes
  const navMap = {
    journey: $("#nav-journey-link"),
    timetables: $("#nav-timetables-link"),
  };

  Object.entries(navMap).forEach(([key, link]) => {
    if (link) {
      const isCurrent = (key === page);
      link.classList.toggle("active", isCurrent);
      if (isCurrent) {
        link.setAttribute("aria-current", "page");
      } else {
        link.removeAttribute("aria-current");
      }
    }
  });

  // Toggle main content panes
  if ($("#journey-pane")) $("#journey-pane").classList.toggle("hidden", page !== "journey");
  if ($("#timetables-pane")) $("#timetables-pane").classList.toggle("hidden", page !== "timetables");

  // Reset or re-render results
  if (!options.preserveResults) {
    results.replaceChildren();
    showStatus();
  }

  // Handle specific page activation logic
  if (page === "timetables") {
    const activeCard = document.querySelector(".mode-select-card.active");
    const mode = activeCard ? activeCard.dataset.timetableMode : "bus";
    switchTimetableMode(mode);
  } else if (page === "journey") {
    if (lastJourneyData) {
      renderJourneyResults(lastJourneyData, activeJourneyMode);
    }
  }

  // Synchronize Browser URL with HTML5 History API
  const targetUrl = page === "journey" ? "/" : `/${page}`;
  if (options.pushHistory) {
    if (window.location.pathname !== targetUrl) {
      history.pushState({ page }, "", targetUrl);
    }
  } else if (options.replaceHistory) {
    if (window.location.pathname !== targetUrl) {
      history.replaceState({ page }, "", targetUrl);
    }
  }

  // Smooth scroll to main panel if requested
  if (options.scroll) {
    const panel = $(".panel");
    if (panel) {
      window.scrollTo({ top: panel.offsetTop - 80, behavior: "smooth" });
    }
  }
}
window.switchMainPage = switchMainPage;

// Topbar main navigation click handlers
document.querySelectorAll("[data-nav-page]").forEach((link) => {
  link.addEventListener("click", (e) => {
    e.preventDefault();
    const targetPage = link.dataset.navPage;
    switchMainPage(targetPage, { pushHistory: true, scroll: true });
  });
});

if ($("#nav-journey-link")) {
  $("#nav-journey-link").addEventListener("click", (e) => {
    e.preventDefault();
    switchMainPage("journey", { pushHistory: true, scroll: true });
  });
}

if ($("#nav-timetables-link")) {
  $("#nav-timetables-link").addEventListener("click", (e) => {
    e.preventDefault();
    switchMainPage("timetables", { pushHistory: true, scroll: true });
  });
}

// Handle browser Back / Forward buttons (popstate)
window.addEventListener("popstate", (e) => {
  const page = (e.state && e.state.page) ? e.state.page : getPageFromUrl();
  switchMainPage(page, { pushHistory: false, scroll: false });
});

// Handle hashchange for backwards compatibility
window.addEventListener("hashchange", () => {
  const page = getPageFromUrl();
  switchMainPage(page, { pushHistory: false, scroll: true });
});

// ---------------------------------------------------------------------------
// Plan a Journey: Transport Type Selector (All Modes, Bus, Train, Local)
// ---------------------------------------------------------------------------
document.querySelectorAll("[data-journey-mode]").forEach((btn) => {
  btn.addEventListener("click", () => {
    activeJourneyMode = btn.dataset.journeyMode;
    document.querySelectorAll("[data-journey-mode]").forEach((item) => {
      const isSel = item === btn;
      item.classList.toggle("active", isSel);
      item.setAttribute("aria-checked", isSel ? "true" : "false");
    });
    // Dynamically update results if journey search has been performed
    if (lastJourneyData) {
      renderJourneyResults(lastJourneyData, activeJourneyMode);
    }
  });
});

// ---------------------------------------------------------------------------
// Timetables: Single Transport Selector (Bus, Train, Local Transport)
// ---------------------------------------------------------------------------
function switchTimetableMode(mode) {
  document.querySelectorAll(".mode-select-card").forEach((card) => {
    const isActive = card.dataset.timetableMode === mode;
    card.classList.toggle("active", isActive);
    card.setAttribute("aria-checked", isActive ? "true" : "false");
    const checkPill = card.querySelector(".mode-check-pill");
    if (checkPill) checkPill.classList.toggle("hidden", !isActive);
  });

  if ($("#subpane-bus")) $("#subpane-bus").classList.toggle("hidden", mode !== "bus");
  if ($("#subpane-train")) $("#subpane-train").classList.toggle("hidden", mode !== "train");
  if ($("#subpane-local")) $("#subpane-local").classList.toggle("hidden", mode !== "local");

  results.replaceChildren();
  showStatus();

  // When Local Transport is selected, auto-load or query local feeder network
  if (mode === "local") {
    const dist = $("#local-district") ? $("#local-district").value.trim() : "";
    const q = $("#local-query") ? $("#local-query").value.trim() : "";
    searchLocalTransport(dist, q);
  }
}

document.querySelectorAll("[data-timetable-mode]").forEach((btn) => {
  btn.addEventListener("click", () => {
    switchTimetableMode(btn.dataset.timetableMode);
  });
});

// Swap locations with subtle continuous rotation animation
let swapRotation = 0;
const swapBtn = $("#swap");
if (swapBtn) {
  swapBtn.addEventListener("click", () => {
    const origInput = $("#origin");
    const destInput = $("#destination");
    if (!origInput || !destInput) return;
    swapRotation += 180;
    swapBtn.style.transform = `rotate(${swapRotation}deg)`;
    const temp = origInput.value;
    origInput.value = destInput.value;
    destInput.value = temp;
    origInput.classList.remove("input-invalid");
    destInput.classList.remove("input-invalid");
    origInput.dispatchEvent(new Event("change", { bubbles: true }));
    destInput.dispatchEvent(new Event("change", { bubbles: true }));
    document.querySelectorAll(".district-suggestions-dropdown").forEach((d) => d.classList.add("hidden"));
  });
}

// Journey search form submission with comprehensive validation & loading state
const journeyForm = $("#journey-form");
if (journeyForm) {
  journeyForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const origInput = $("#origin");
    const destInput = $("#destination");
    const dateInput = $("#travel-date");
    const timeInput = $("#departure-time");
    const prefInput = $("#preference");
    const submitBtn = journeyForm.querySelector(".search-submit") || journeyForm.querySelector("button[type='submit']");

    if (!origInput || !destInput || !dateInput) return;

    // Reset previous invalid states
    origInput.classList.remove("input-invalid");
    destInput.classList.remove("input-invalid");
    dateInput.classList.remove("input-invalid");
    if (timeInput) timeInput.classList.remove("input-invalid");
    if (prefInput) prefInput.classList.remove("input-invalid");

    const rawOrigin = (origInput.value || "").trim();
    const rawDest = (destInput.value || "").trim();
    const travelDate = (dateInput.value || "").trim();
    const departureTime = (timeInput ? timeInput.value : "").trim();
    const preference = (prefInput ? prefInput.value : "balanced").trim();

    // 1. Validate Origin Presence
    if (!rawOrigin) {
      origInput.classList.add("input-invalid");
      origInput.focus();
      showStatus("Please enter or select a pickup district in Bangladesh.", "error");
      return;
    }

    // 2. Validate Origin District against 64 official Bangladesh districts
    const canonicalOrigin = resolveDistrictName(rawOrigin);
    if (!canonicalOrigin) {
      origInput.classList.add("input-invalid");
      origInput.focus();
      showStatus(`"${rawOrigin}" is not recognized as one of the 64 districts of Bangladesh. Please select a valid district from the suggestions.`, "error");
      return;
    }
    origInput.value = canonicalOrigin;

    // 3. Validate Destination Presence
    if (!rawDest) {
      destInput.classList.add("input-invalid");
      destInput.focus();
      showStatus("Please enter or select a destination district in Bangladesh.", "error");
      return;
    }

    // 4. Validate Destination District against 64 official Bangladesh districts
    const canonicalDest = resolveDistrictName(rawDest);
    if (!canonicalDest) {
      destInput.classList.add("input-invalid");
      destInput.focus();
      showStatus(`"${rawDest}" is not recognized as one of the 64 districts of Bangladesh. Please select a valid district from the suggestions.`, "error");
      return;
    }
    destInput.value = canonicalDest;

    // 5. Ensure Origin and Destination are distinct
    if (canonicalOrigin.toLowerCase() === canonicalDest.toLowerCase()) {
      origInput.classList.add("input-invalid");
      destInput.classList.add("input-invalid");
      destInput.focus();
      showStatus("Origin and destination districts must be different. Please select distinct pickup and dropoff locations.", "error");
      return;
    }

    // 6. Validate Travel Date
    const todayStr = localDate();
    if (!travelDate) {
      dateInput.classList.add("input-invalid");
      dateInput.focus();
      showStatus("Please select a valid travel date.", "error");
      return;
    }
    if (travelDate < todayStr) {
      dateInput.classList.add("input-invalid");
      dateInput.focus();
      showStatus("Travel date cannot be in the past. Please select today or a future date.", "error");
      return;
    }

    // 7. Validate Departure Time
    if (!departureTime) {
      if (timeInput) timeInput.classList.add("input-invalid");
      showStatus("Please select a scheduled departure time.", "error");
      return;
    }

    // 8. Validate Preference
    const validPreferences = ["balanced", "cheapest", "fastest", "shortest"];
    const safePreference = validPreferences.includes(preference) ? preference : "balanced";

    // Close any open suggestion dropdowns
    document.querySelectorAll(".district-suggestions-dropdown").forEach((d) => d.classList.add("hidden"));

    // Button loading state with spinner
    const originalBtnHtml = submitBtn ? submitBtn.innerHTML : "Search Routes ➔";
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = `<span class="button-spinner" aria-hidden="true"></span> Searching Routes...`;
    }

    results.replaceChildren();
    showStatus("Calculating schedule-aware journeys across Bangladesh...", "info");

    try {
      const data = await api("/api/search", {
        method: "POST",
        body: JSON.stringify({
          origin: canonicalOrigin,
          destination: canonicalDest,
          travel_date: travelDate,
          departure_time: departureTime,
          preference: safePreference,
        }),
      });

      if (!data.routes || !data.routes.length) {
        showStatus();
        lastJourneyData = data;
        renderEmptyJourneyResults(canonicalOrigin, canonicalDest, travelDate, departureTime, data);
        return;
      }

      showStatus();
      lastJourneyData = data;
      renderJourneyResults(data, activeJourneyMode);

      // Smooth scroll to results
      const resultsEl = $("#results");
      if (resultsEl) {
        resultsEl.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    } catch (error) {
      showStatus(`Search failed: ${error.message}`, "error");
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalBtnHtml;
      }
    }
  });
}

function renderEmptyJourneyResults(origin, dest, date, time, data = {}) {
  results.replaceChildren();

  let trainAlert = "";
  if (data.direct_train_available === false) {
    trainAlert = `
      <div class="train-alert-card" style="margin-bottom: 16px;">
        <div class="train-alert-icon">${getModeBadge("train", 24)}</div>
        <div class="train-alert-body">
          <h4>No Direct Railway Connection</h4>
          <p>${escapeHtml(data.direct_train_message || `There is no direct railway service between ${origin} and ${dest}.`)}</p>
        </div>
      </div>
    `;
  }

  const card = document.createElement("div");
  card.className = "empty-route-state";
  card.innerHTML = `
    ${trainAlert}
    <div class="empty-state-card" style="text-align: center; padding: 40px 24px; background: #ffffff; border: 1.5px dashed var(--border); border-radius: 16px; margin: 20px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.03);">
      <div style="font-size: 2.8rem; margin-bottom: 12px; line-height: 1;">🗺️</div>
      <h3 style="font-size: 1.3rem; font-weight: 700; color: var(--primary-text); margin-bottom: 8px;">
        No Scheduled Routes Found
      </h3>
      <p style="color: var(--secondary-text); max-width: 560px; margin: 0 auto 20px; font-size: 0.94rem; line-height: 1.5;">
        We could not generate an active route connecting <strong>${escapeHtml(origin)}</strong> and <strong>${escapeHtml(dest)}</strong> for departure around <strong>${escapeHtml(time)}</strong> on <strong>${escapeHtml(date)}</strong>.
      </p>
      <div style="background: var(--main-bg); border: 1px solid var(--border); border-radius: 12px; padding: 18px 22px; max-width: 520px; margin: 0 auto 20px; text-align: left; font-size: 0.88rem; color: var(--primary-text);">
        <strong style="color: var(--primary-green); display: block; margin-bottom: 8px;">Suggestions to find a route:</strong>
        <ul style="margin: 0; padding-left: 20px; line-height: 1.6; color: var(--secondary-text);">
          <li>Select a different departure time slot (e.g. earlier morning or mid-day).</li>
          <li>Set Route Priority to <strong>Balanced (Optimal)</strong> for broader multimodal combinations.</li>
          <li>Check intermediate divisional railway hubs (e.g. Dhaka, Chattogram, Akhaura).</li>
          <li>Switch to the <strong>Timetables</strong> tab to review specific bus and train schedules.</li>
        </ul>
      </div>
      <button type="button" class="button secondary small" onclick="switchMainPage('timetables', { pushHistory: true, scroll: true });">
        Browse Timetables &amp; Schedules ➔
      </button>
    </div>
  `;
  results.appendChild(card);
}

function renderJourneyResults(data, mode = "all") {
  results.replaceChildren();

  // Filter routes based on mode
  let filteredRoutes = data.routes || [];
  if (mode === "bus") {
    filteredRoutes = filteredRoutes.filter((r) => r.kind.toLowerCase() === "bus");
  } else if (mode === "train") {
    filteredRoutes = filteredRoutes.filter((r) => r.kind.toLowerCase() === "train");
  } else if (mode === "local") {
    filteredRoutes = filteredRoutes.filter((r) => r.kind.toLowerCase() === "multimodal" || (r.legs && r.legs.some((l) => l.mode.toLowerCase() === "local")));
  }

  let directTrainAlert = "";
  if (data.direct_train_available === false && (mode === "all" || mode === "train")) {
    directTrainAlert = `
      <div class="train-alert-card">
        <div class="train-alert-icon">${getModeBadge("train", 24)}</div>
        <div class="train-alert-body">
          <h4>No Direct Train Available on this Route</h4>
          <p>${escapeHtml(data.direct_train_message || "There is no direct train between the selected districts.")}</p>
          <div class="train-alert-sub">💡 Multimodal connections via nearest railway stations and direct bus routes are listed below.</div>
        </div>
      </div>
    `;
  }

  let compareHtml = "";
  const comparison = data.comparison;
  if (comparison && mode === "all") {
    const cards = [
      comparison.cheapest && { key: "cheapest", title: "Cheapest Route", route: comparison.cheapest },
      comparison.fastest && { key: "fastest", title: "Fastest Route", route: comparison.fastest },
      comparison.shortest && { key: "shortest", title: "Shortest Route", route: comparison.shortest },
    ].filter(Boolean).map(({ key, title, route }) => `
      <div class="comparison-card ${key}">
        <span class="comparison-badge">${title}</span>
        <div class="comparison-metric">BDT ${route.fare_bdt}</div>
        <div class="comparison-sub">⏱️ <b>Est. Travel:</b> ${route.travel_time.minimum_minutes}–${route.travel_time.maximum_minutes} mins (${formatMinutesRange(route.travel_time.minimum_minutes, route.travel_time.maximum_minutes)}) • ${route.distance_km.toFixed(1)} km</div>
        <div class="comparison-wait-chip">⏳ <strong>Wait for Next Departure:</strong> ${formatWaitTime(route.waiting_minutes)}</div>
        <div class="comparison-sub" style="margin-top: 6px; display: inline-flex; align-items: center; justify-content: center; gap: 6px;">Via ${getModeBadge(route.kind, 13)} <b>${escapeHtml(route.kind)}</b></div>
      </div>
    `).join("");

    compareHtml = `
      <div class="comparison-container">
        <div class="comparison-grid">${cards}</div>
        <div class="comparison-note">ℹ️ ${escapeHtml(comparison.note || "")}</div>
      </div>
    `;
  }

  const modeLabels = {
    all: "All Available Route Options",
    bus: "Inter-District Bus Options",
    train: "Bangladesh Railway Options",
    local: "Feeder & Local Transfer Connections",
  };

  let routesContent = "";
  if (filteredRoutes.length > 0) {
    routesContent = filteredRoutes.map((route, idx) => renderRouteCard(route, idx)).join("");
  } else {
    routesContent = `
      <div class="empty-mode-box" style="background:#f8fafc; border:1.5px dashed var(--border); border-radius:12px; padding:28px 20px; text-align:center; margin:16px 0;">
        <p style="color:var(--text-muted); font-size:0.95rem; margin-bottom:12px;">No direct <b>${escapeHtml(mode.toUpperCase())}</b> routes found for this journey under current schedules.</p>
        <button type="button" class="button secondary small" onclick="document.querySelector('[data-journey-mode=\\'all\\']').click();">
          Show All Available Transit Options ➔
        </button>
      </div>
    `;
  }

  const prefLabels = {
    balanced: "Balanced (Optimal)",
    cheapest: "Cheapest Fare",
    fastest: "Fastest Travel",
    shortest: "Shortest Distance",
  };
  const currentPref = $("#preference") ? $("#preference").value : "balanced";
  const prefDisplay = prefLabels[currentPref] || currentPref;

  results.innerHTML = `
    ${directTrainAlert}
    ${compareHtml}
    <div class="results-header">
      <h2>${modeLabels[mode] || "Available Route Options"} (${filteredRoutes.length})</h2>
      <span>Ranked by ${escapeHtml(prefDisplay)}</span>
    </div>
    ${routesContent}
  `;
}

// Bus timetable search form
$("#bus-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  results.replaceChildren();
  showStatus("Querying bus schedules from PostgreSQL...", "info");
  try {
    const params = new URLSearchParams();
    if ($("#bus-service").value.trim()) params.set("service", $("#bus-service").value.trim());
    if ($("#bus-origin").value.trim()) params.set("origin", $("#bus-origin").value.trim());
    if ($("#bus-destination").value.trim()) params.set("destination", $("#bus-destination").value.trim());

    const items = await api(`/api/timetables/bus?${params}`);
    if (!items.length) {
      showStatus("No bus timetables found matching your search filters.", "error");
      return;
    }

    showStatus(`Found ${items.length} scheduled bus service(s).`, "success");
    const fareValues = [...new Set(items.map(it => (it.fare_bdt ?? it.fare)).filter(f => f !== null && f !== undefined && f > 0))];
    const fareSummary = fareValues.length === 1
      ? `BDT ${fareValues[0]}`
      : (fareValues.length > 1 ? `BDT ${Math.min(...fareValues)}–${Math.max(...fareValues)}` : null);
    const fareBadgeHtml = fareSummary
      ? `<span class="route-fare-badge" style="padding:4px 12px; border-radius:12px; font-weight:700; color:#065f46; background:#ecfdf5; border:1px solid #a7f3d0; font-size:0.9rem;">💰 Fare: ${fareSummary}</span>`
      : "";

    const rows = items.map((item) => {
      const fareDisplay = (item.fare_bdt !== undefined && item.fare_bdt !== null && item.fare_bdt > 0)
        ? `BDT ${item.fare_bdt}`
        : ((item.fare !== undefined && item.fare !== null && item.fare > 0) ? `BDT ${item.fare}` : "--");
      return `
      <tr>
        <td><div style="display:inline-flex; align-items:center; gap:6px;">${getModeBadge("bus", 13)} <strong>${escapeHtml(item.route_id)}</strong></div></td>
        <td><b>${escapeHtml(item.transport_name)}</b></td>
        <td>${escapeHtml(item.origin)}</td>
        <td>${escapeHtml(item.destination)}</td>
        <td><b>${escapeHtml(item.departure || item.departure_time ? String(item.departure || item.departure_time).slice(0, 5) : "--:--")}</b></td>
        <td><b>${escapeHtml(item.arrival || item.arrival_time ? String(item.arrival || item.arrival_time).slice(0, 5) : "--:--")}</b></td>
        <td><b>${fareDisplay}</b></td>
        <td>
          <button type="button" class="save-fav-btn" onclick="saveFavouriteService('bus', '${escapeHtml(item.route_id)}', '${escapeHtml(item.transport_name)}')">
            ⭐ Bookmark
          </button>
        </td>
      </tr>
    `;
    }).join("");

    results.innerHTML = `
      <div class="table-card">
        <div class="table-card-header">
          <h3 style="display:inline-flex; align-items:center; gap:8px;">${getModeBadge("bus", 16)} Daily Bus Timetable</h3>
          <div style="display:inline-flex; align-items:center; gap:12px;">
            ${fareBadgeHtml}
            <span>${items.length} scheduled service(s)</span>
          </div>
        </div>
        <table>
          <thead>
            <tr>
              <th>Route ID</th>
              <th>Transport Company</th>
              <th>Origin District</th>
              <th>Destination District</th>
              <th>Departure Time</th>
              <th>Arrival Time</th>
              <th>Fare</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
  } catch (error) {
    showStatus(`Failed to load bus timetables: ${error.message}`, "error");
  }
});

// Train timetable search form
$("#train-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  results.replaceChildren();
  showStatus("Querying train timetable from PostgreSQL...", "info");
  try {
    const params = new URLSearchParams();
    const query = $("#train-search").value.trim();
    if (query) {
      if (/^\d+$/.test(query)) {
        params.set("train_no", query);
      } else {
        params.set("train_name", query);
      }
    }
    if ($("#train-origin").value.trim()) params.set("origin", $("#train-origin").value.trim());
    if ($("#train-destination").value.trim()) params.set("destination", $("#train-destination").value.trim());

    const items = await api(`/api/timetables/train?${params}`);
    if (!items.length) {
      showStatus("No train services found matching your criteria.", "error");
      return;
    }

    showStatus(`Found ${items.length} train schedule(s).`, "success");
    const rows = items.map((item, idx) => {
      const stopList = (item.stop_details && item.stop_details.length > 0)
        ? item.stop_details
        : (item.stops || []).map((s, i) => ({ station: s, stop_order: i + 1 }));

      const stoppageRows = stopList.map((s, sIdx) => {
        const { arrDisplay, depDisplay, haltBadge } = formatStopTimes(s, sIdx, stopList.length);
        const dist = s.district_name && s.district_name !== s.station ? ` <span class="station-dist">(${escapeHtml(s.district_name)})</span>` : "";
        return `
          <tr>
            <td>${sIdx + 1}</td>
            <td><strong>${escapeHtml(s.station)}</strong>${dist}</td>
            <td>${arrDisplay}</td>
            <td>${depDisplay}</td>
            <td>${haltBadge}</td>
          </tr>
        `;
      }).join("");

      const dep = item.departure || item.departure_time ? String(item.departure || item.departure_time).slice(0, 5) : "--:--";
      const arr = item.arrival || item.arrival_time ? String(item.arrival || item.arrival_time).slice(0, 5) : "--:--";

      return `
        <tr class="train-summary-row">
          <td><span class="pill train">${getModeBadge("train", 12)} ${escapeHtml(item.train_no)}</span></td>
          <td><b>${escapeHtml(item.train_name)}</b></td>
          <td>${escapeHtml(item.origin)}</td>
          <td>${escapeHtml(item.destination)}</td>
          <td><b>${escapeHtml(dep)}</b></td>
          <td><b>${escapeHtml(arr)}${item.day_offset ? ` (+${item.day_offset}d)` : ""}</b></td>
          <td><span class="off-day-badge">${escapeHtml(item.off_day || "None")}</span></td>
          <td style="display: flex; gap: 6px; align-items: center;">
            <button type="button" class="view-stoppages-btn" onclick="const box = document.getElementById('train-stops-${idx}'); box.classList.toggle('hidden'); const isHidden = box.classList.contains('hidden'); this.textContent = isHidden ? 'View Stoppages ▾ (${stopList.length})' : 'Hide Stoppages ▴';">
              View Stoppages ▾ (${stopList.length})
            </button>
            <button type="button" class="save-fav-btn" onclick="saveFavouriteService('train', '${escapeHtml(item.train_no)}', '${escapeHtml(item.train_name)}')">
              ⭐ Bookmark
            </button>
          </td>
        </tr>
        <tr id="train-stops-${idx}" class="train-details-row hidden">
          <td colspan="8">
            <div class="train-stoppage-box">
              <div class="stoppage-box-header">
                <strong style="display:inline-flex; align-items:center; gap:6px;">${getModeBadge("train", 14)} Complete Stoppage List & Scheduled Halts for ${escapeHtml(item.train_name)} (${escapeHtml(item.train_no)})</strong>
                <span>Route: ${escapeHtml(item.origin)} ➔ ${escapeHtml(item.destination)}</span>
              </div>
              <table class="stoppage-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Station</th>
                    <th>Scheduled Arrival</th>
                    <th>Scheduled Departure</th>
                    <th>Halt Duration</th>
                  </tr>
                </thead>
                <tbody>${stoppageRows}</tbody>
              </table>
            </div>
          </td>
        </tr>
      `;
    }).join("");

    results.innerHTML = `
      <div class="table-card">
        <div class="table-card-header">
          <h3 style="display:inline-flex; align-items:center; gap:8px;">${getModeBadge("train", 16)} Daily Train Timetable</h3>
          <span>${items.length} trains found</span>
        </div>
        <table>
          <thead>
            <tr>
              <th>Train No</th>
              <th>Train Name</th>
              <th>Origin Station</th>
              <th>Destination Station</th>
              <th>Departure Time</th>
              <th>Arrival Time</th>
              <th>Weekly Off</th>
              <th>Stoppages & Actions</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
  } catch (error) {
    showStatus(`Failed to load train schedules: ${error.message}`, "error");
  }
});

// -------------------------------------------------------------
// Local Transport Feeder Timetable & Connections
// -------------------------------------------------------------

async function searchLocalTransport(district = "", query = "") {
  results.replaceChildren();
  showStatus("Querying local transport feeder routes...", "info");
  try {
    const params = new URLSearchParams();
    if (district) params.set("district", district);
    if (query) params.set("location", query);

    const items = await api(`/api/timetables/local?${params}`);
    if (!items.length) {
      showStatus("No local transport feeder routes found matching your criteria.", "error");
      results.innerHTML = `
        <div class="empty-state" style="text-align: center; padding: 40px; background: white; border-radius: var(--radius); border: 1.5px dashed var(--border);">
          <div style="font-size: 2.5rem; margin-bottom: 10px;">🛺</div>
          <h3>No Local Corridors Found</h3>
          <p style="color: var(--text-muted); margin-top: 6px;">Try searching by another parent district or clearing the upazila filter.</p>
        </div>
      `;
      return;
    }

    showStatus(`Found ${items.length} local transit corridor(s).`, "success");
    renderLocalTransportResults(items);
  } catch (error) {
    showStatus(`Failed to load local transport data: ${error.message}`, "error");
  }
}

function renderLocalTransportResults(items) {
  const rows = items.map((item) => `
    <tr>
      <td>
        <div style="display:inline-flex; align-items:center; gap:6px;">
          ${getModeBadge("local", 13)}
          <strong>${escapeHtml(item.from_location)} ➔ ${escapeHtml(item.to_location)}</strong>
        </div>
      </td>
      <td><span class="pill outline">${escapeHtml(item.parent_district)}</span></td>
      <td>
        <div class="local-chips">
          ${item.vehicle_types.map((v) => `<span class="local-chip">${escapeHtml(v)}</span>`).join("")}
        </div>
      </td>
      <td><b>${item.distance_km} km</b></td>
      <td><b>~${item.est_duration_minutes} mins</b></td>
      <td><span class="fare-badge">BDT ${item.est_fare_min_bdt}–${item.est_fare_max_bdt}</span></td>
      <td><span style="font-size:0.8rem; color:#475569;">${escapeHtml(item.frequency)}</span></td>
    </tr>
  `).join("");

  results.innerHTML = `
    <div class="table-card">
      <div class="table-card-header">
        <h3 style="display:inline-flex; align-items:center; gap:8px;">${getModeBadge("local", 16)} Local Transport & Feeder Shuttles</h3>
        <span>${items.length} verified corridor(s)</span>
      </div>
      <div class="table-card-intro" style="padding: 12px 18px; background: #f8fafc; border-bottom: 1px solid var(--border); font-size: 0.85rem; color: #475569;">
        ℹ️ <strong>Feeder Transport Network:</strong> Continuous local connections (CNG, auto-rickshaw, easy bike, tempo) linking upazilas and neighborhood hubs to district centers and Bangladesh Railway stations.
      </div>
      <table>
        <thead>
          <tr>
            <th>Corridor (From ➔ To)</th>
            <th>Parent District</th>
            <th>Available Vehicles</th>
            <th>Distance</th>
            <th>Est. Duration</th>
            <th>Fare Range</th>
            <th>Service Frequency</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;
}

if ($("#local-form")) {
  $("#local-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const dist = $("#local-district") ? $("#local-district").value.trim() : "";
    const q = $("#local-query") ? $("#local-query").value.trim() : "";
    searchLocalTransport(dist, q);
  });
}

// -------------------------------------------------------------
// Authentication & User State Management
// -------------------------------------------------------------

async function initAuth() {
  const token = localStorage.getItem("token");
  if (!token) {
    updateAuthUI(null);
    return;
  }
  try {
    const user = await api("/api/auth/me");
    currentUser = user;
    updateAuthUI(user);
    applyUserPreferences();
  } catch {
    localStorage.removeItem("token");
    currentUser = null;
    updateAuthUI(null);
  }
}

function updateAuthUI(user) {
  const guestControls = $("#guest-controls");
  const userControls = $("#user-controls");
  const adminNavLink = $("#admin-nav-link");
  const adminUserBtn = $("#admin-user-btn");
  if (!guestControls || !userControls) return;

  const blockedBanner = $("#profile-blocked-banner");
  const blockedReason = $("#profile-blocked-reason");
  const reportAlert = $("#report-blocked-alert");
  const reportBlockedMsg = $("#report-blocked-msg");
  const submitReportBtn = $("#submit-report-btn");

  if (user) {
    guestControls.classList.add("hidden");
    userControls.classList.remove("hidden");
    $("#user-pill-name").textContent = user.full_name.split(" ")[0];
    $("#user-pill-id").textContent = user.user_id;

    // Handle account suspension / blocking
    if (user.is_blocked) {
      if (blockedBanner) blockedBanner.classList.remove("hidden");
      if (blockedReason) blockedReason.textContent = user.blocked_reason || "Your account has been restricted by an administrator. You cannot submit new reports.";
      if (reportAlert) reportAlert.classList.remove("hidden");
      if (reportBlockedMsg) reportBlockedMsg.textContent = user.blocked_reason || "Your account is restricted from submitting new reports.";
      if (submitReportBtn) submitReportBtn.disabled = true;
    } else {
      if (blockedBanner) blockedBanner.classList.add("hidden");
      if (reportAlert) reportAlert.classList.add("hidden");
      if (submitReportBtn) submitReportBtn.disabled = false;
    }

    // Load unread notification count
    loadUnreadNotificationCount();

    // Admin Dashboard and Portal access are restricted to authenticated administrators only
    const isAdmin = user.role === "admin";
    if (adminNavLink) {
      if (isAdmin) {
        adminNavLink.classList.remove("hidden");
      } else {
        adminNavLink.classList.add("hidden");
      }
    }
    if (adminUserBtn) {
      if (isAdmin) {
        adminUserBtn.classList.remove("hidden");
      } else {
        adminUserBtn.classList.add("hidden");
      }
    }
  } else {
    guestControls.classList.remove("hidden");
    userControls.classList.add("hidden");
    if (adminNavLink) adminNavLink.classList.add("hidden");
    if (adminUserBtn) adminUserBtn.classList.add("hidden");

    if (blockedBanner) blockedBanner.classList.add("hidden");
    if (reportAlert) reportAlert.classList.add("hidden");
    if (submitReportBtn) submitReportBtn.disabled = false;

    const notifBadge = $("#notif-count-badge");
    if (notifBadge) notifBadge.classList.add("hidden");
    const dashNotifBadge = $("#dash-notif-badge");
    if (dashNotifBadge) dashNotifBadge.classList.add("hidden");
  }
}

async function applyUserPreferences() {
  if (!currentUser) return;
  try {
    const pref = await api("/api/user/preferences");
    if (pref.default_preference && $("#preference")) {
      $("#preference").value = pref.default_preference;
    }
    if ($("#pref-default-transport")) {
      $("#pref-default-transport").value = pref.default_transport || "No Preference";
    }
    if ($("#pref-default-ranking")) {
      $("#pref-default-ranking").value = pref.default_preference || "balanced";
    }
  } catch {
    // Non-critical
  }
}

// Modal open/close controls
function openModal(modalId) {
  const modal = $(`#${modalId}`);
  if (modal) modal.classList.remove("hidden");
}

function closeModal(modalId) {
  const modal = $(`#${modalId}`);
  if (modal) modal.classList.add("hidden");
}

document.querySelectorAll("[data-close]").forEach((btn) => {
  btn.addEventListener("click", () => closeModal(btn.dataset.close));
});

document.querySelectorAll(".modal-backdrop").forEach((backdrop) => {
  backdrop.addEventListener("click", (e) => {
    if (e.target === backdrop) closeModal(backdrop.id);
  });
});

if ($("#open-login-btn")) {
  $("#open-login-btn").addEventListener("click", () => openModal("login-modal"));
}
if ($("#open-register-btn")) {
  $("#open-register-btn").addEventListener("click", () => openModal("register-modal"));
}
if ($("#switch-to-register")) {
  $("#switch-to-register").addEventListener("click", (e) => {
    e.preventDefault();
    closeModal("login-modal");
    openModal("register-modal");
  });
}
if ($("#switch-to-login")) {
  $("#switch-to-login").addEventListener("click", (e) => {
    e.preventDefault();
    closeModal("register-modal");
    openModal("login-modal");
  });
}

// Login form
$("#login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const errorBox = $("#login-error");
  errorBox.classList.add("hidden");
  try {
    const res = await api("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: $("#login-email").value.trim(),
        password: $("#login-password").value,
      }),
    });
    localStorage.setItem("token", res.access_token);
    currentUser = res.user;
    updateAuthUI(res.user);
    closeModal("login-modal");
    showStatus(`Welcome back, ${res.user.full_name}!`, "success");
    applyUserPreferences();
  } catch (error) {
    errorBox.textContent = error.message;
    errorBox.classList.remove("hidden");
  }
});

// Register form
$("#register-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const errorBox = $("#register-error");
  errorBox.classList.add("hidden");
  const pw = $("#reg-password").value;
  const confirmPw = $("#reg-confirm-password").value;
  if (pw !== confirmPw) {
    errorBox.textContent = "Passwords do not match.";
    errorBox.classList.remove("hidden");
    return;
  }

  try {
    const res = await api("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({
        full_name: $("#reg-name").value.trim(),
        email: $("#reg-email").value.trim(),
        password: pw,
        confirm_password: confirmPw,
      }),
    });
    localStorage.setItem("token", res.access_token);
    currentUser = res.user;
    updateAuthUI(res.user);
    closeModal("register-modal");
    showStatus(`Account registered! Your User ID is ${res.user.user_id}`, "success");
    openDashboardModal("profile");
  } catch (error) {
    errorBox.textContent = error.message;
    errorBox.classList.remove("hidden");
  }
});

// Logout
if ($("#logout-btn")) {
  $("#logout-btn").addEventListener("click", () => {
    localStorage.removeItem("token");
    currentUser = null;
    updateAuthUI(null);
    showStatus("You have been signed out.", "info");
  });
}

// Copy User ID
if ($("#copy-user-id-btn")) {
  $("#copy-user-id-btn").addEventListener("click", () => {
    if (currentUser) {
      navigator.clipboard.writeText(currentUser.user_id);
      const btn = $("#copy-user-id-btn");
      btn.textContent = "✓ Copied!";
      setTimeout(() => { btn.textContent = "📋 Copy"; }, 2000);
    }
  });
}

// -------------------------------------------------------------
// User Dashboard Features
// -------------------------------------------------------------

function openDashboardModal(targetTab = "profile") {
  if (!currentUser) {
    openModal("login-modal");
    return;
  }

  $("#dash-user-name").textContent = currentUser.full_name;
  $("#dash-user-id").textContent = currentUser.user_id;
  $("#dash-full-name").value = currentUser.full_name;
  $("#dash-email").value = currentUser.email;

  switchDashboardTab(targetTab);
  openModal("dashboard-modal");
}

if ($("#dashboard-btn")) {
  $("#dashboard-btn").addEventListener("click", () => openDashboardModal("profile"));
}

function switchDashboardTab(tabName) {
  document.querySelectorAll(".dash-tab").forEach((t) => {
    t.classList.toggle("active", t.dataset.dashTab === tabName);
  });
  document.querySelectorAll(".dash-pane").forEach((p) => {
    p.classList.toggle("hidden", p.id !== `dash-pane-${tabName}`);
    p.classList.toggle("active", p.id === `dash-pane-${tabName}`);
  });

  if (tabName === "favourites") loadDashboardFavourites();
  if (tabName === "reports") loadDashboardReports();
  if (tabName === "notifications") loadDashboardNotifications();
}

document.querySelectorAll(".dash-tab").forEach((tab) => {
  tab.addEventListener("click", () => switchDashboardTab(tab.dataset.dashTab));
});

// Profile update
$("#update-profile-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const updated = await api("/api/auth/profile", {
      method: "PUT",
      body: JSON.stringify({ full_name: $("#dash-full-name").value.trim() }),
    });
    currentUser.full_name = updated.full_name;
    updateAuthUI(currentUser);
    $("#dash-user-name").textContent = updated.full_name;
    alert("Profile name updated successfully.");
  } catch (error) {
    alert(`Could not update profile: ${error.message}`);
  }
});

// Password change
$("#change-pw-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const msgBox = $("#change-pw-msg");
  msgBox.classList.add("hidden");
  const newPw = $("#pw-new").value;
  const confirmPw = $("#pw-confirm").value;
  if (newPw !== confirmPw) {
    msgBox.textContent = "New passwords do not match.";
    msgBox.className = "form-feedback form-error";
    msgBox.classList.remove("hidden");
    return;
  }
  try {
    await api("/api/auth/change-password", {
      method: "PUT",
      body: JSON.stringify({
        current_password: $("#pw-current").value,
        new_password: newPw,
        confirm_password: confirmPw,
      }),
    });
    msgBox.textContent = "Password changed successfully!";
    msgBox.className = "form-feedback form-success";
    msgBox.classList.remove("hidden");
    $("#change-pw-form").reset();
  } catch (error) {
    msgBox.textContent = error.message;
    msgBox.className = "form-feedback form-error";
    msgBox.classList.remove("hidden");
  }
});

// Preferences update
$("#preferences-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const msgBox = $("#pref-msg");
  msgBox.classList.add("hidden");
  try {
    const res = await api("/api/user/preferences", {
      method: "PUT",
      body: JSON.stringify({
        default_transport: $("#pref-default-transport").value,
        default_preference: $("#pref-default-ranking").value,
      }),
    });
    if ($("#preference")) {
      $("#preference").value = res.default_preference;
    }
    msgBox.textContent = "Preferences saved! Route searches will reflect your choice.";
    msgBox.className = "form-feedback form-success";
    msgBox.classList.remove("hidden");
  } catch (error) {
    msgBox.textContent = error.message;
    msgBox.className = "form-feedback form-error";
    msgBox.classList.remove("hidden");
  }
});

// -------------------------------------------------------------
// Favourites (Routes & Services)
// -------------------------------------------------------------

async function loadDashboardFavourites() {
  const routesBox = $("#fav-routes-list");
  const srvBox = $("#fav-services-list");
  routesBox.innerHTML = "<p>Loading saved routes...</p>";
  srvBox.innerHTML = "<p>Loading saved services...</p>";

  try {
    const [routes, services] = await Promise.all([
      api("/api/user/favourites/routes"),
      api("/api/user/favourites/services"),
    ]);

    if (!routes.length) {
      routesBox.innerHTML = "<p style='color: var(--text-muted); font-size: 0.85rem;'>No favourite routes saved yet.</p>";
    } else {
      routesBox.innerHTML = routes.map((r) => `
        <div class="fav-card">
          <div class="fav-card-title">${escapeHtml(r.origin)} ➔ ${escapeHtml(r.destination)}</div>
          <div class="fav-actions">
            <button type="button" class="fav-search-btn" onclick="quickSearchRoute('${escapeHtml(r.origin)}', '${escapeHtml(r.destination)}')">Search ➔</button>
            <button type="button" class="fav-del-btn" onclick="deleteFavRoute(${r.id})" title="Remove">✕</button>
          </div>
        </div>
      `).join("");
    }

    if (!services.length) {
      srvBox.innerHTML = "<p style='color: var(--text-muted); font-size: 0.85rem;'>No favourite services bookmarked yet.</p>";
    } else {
      srvBox.innerHTML = services.map((s) => `
        <div class="fav-card">
          <div>
            <span class="pill ${escapeHtml(s.transport_type)}">${getModeBadge(s.transport_type, 12)} ${escapeHtml(s.transport_type)}</span>
            <div class="fav-card-title" style="margin-top: 4px;">${escapeHtml(s.service_name)} (${escapeHtml(s.service_identifier)})</div>
          </div>
          <div class="fav-actions">
            <button type="button" class="fav-del-btn" onclick="deleteFavService(${s.id})" title="Remove">✕</button>
          </div>
        </div>
      `).join("");
    }
  } catch (error) {
    routesBox.innerHTML = `<p class="form-error">Could not load favourites: ${error.message}</p>`;
  }
}

window.quickSearchRoute = (orig, dest) => {
  closeModal("dashboard-modal");
  switchMainPage("journey", { scroll: true });
  $("#origin").value = orig;
  $("#destination").value = dest;
  $("#journey-form").dispatchEvent(new Event("submit"));
};

window.saveFavouriteRoute = async (orig, dest) => {
  if (!currentUser) {
    openModal("login-modal");
    return;
  }
  try {
    await api("/api/user/favourites/routes", {
      method: "POST",
      body: JSON.stringify({ origin: orig, destination: dest }),
    });
    showStatus(`Saved ${orig} ➔ ${dest} to your favourite routes!`, "success");
  } catch (error) {
    showStatus(`Could not save favourite route: ${error.message}`, "error");
  }
};

window.saveFavouriteService = async (type, identifier, name) => {
  if (!currentUser) {
    openModal("login-modal");
    return;
  }
  try {
    await api("/api/user/favourites/services", {
      method: "POST",
      body: JSON.stringify({ transport_type: type, service_identifier: identifier, service_name: name }),
    });
    showStatus(`Bookmarked ${name} to your favourite services!`, "success");
  } catch (error) {
    showStatus(`Could not bookmark service: ${error.message}`, "error");
  }
};

window.deleteFavRoute = async (id) => {
  try {
    await api(`/api/user/favourites/routes/${id}`, { method: "DELETE" });
    loadDashboardFavourites();
  } catch (error) {
    alert(`Could not remove route: ${error.message}`);
  }
};

window.deleteFavService = async (id) => {
  try {
    await api(`/api/user/favourites/services/${id}`, { method: "DELETE" });
    loadDashboardFavourites();
  } catch (error) {
    alert(`Could not remove service: ${error.message}`);
  }
};

// Add route from dashboard form
$("#add-fav-route-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/api/user/favourites/routes", {
      method: "POST",
      body: JSON.stringify({
        origin: $("#fav-origin").value.trim(),
        destination: $("#fav-dest").value.trim(),
      }),
    });
    $("#fav-origin").value = "";
    $("#fav-dest").value = "";
    loadDashboardFavourites();
  } catch (error) {
    alert(`Could not add route: ${error.message}`);
  }
});

// -------------------------------------------------------------
// User Issue Reporting & Complaints System
// -------------------------------------------------------------

window.openReportForRoute = (orig, dest, mode) => {
  if (!currentUser) {
    openModal("login-modal");
    showStatus("Please log in to report an issue with this route.", "info");
    return;
  }
  const formMsg = $("#report-form-msg");
  if (formMsg) {
    formMsg.classList.add("hidden");
    formMsg.textContent = "";
  }
  if ($("#report-related-route")) {
    $("#report-related-route").value = `${orig} to ${dest}`;
  }
  if ($("#report-transport-mode")) {
    const m = String(mode || "").toLowerCase();
    if (m === "bus") $("#report-transport-mode").value = "Bus";
    else if (m === "train") $("#report-transport-mode").value = "Train";
    else if (m === "multimodal") $("#report-transport-mode").value = "Bus + Train";
    else $("#report-transport-mode").value = "General";
  }
  openModal("report-modal");
};

if ($("#nav-report-link")) {
  $("#nav-report-link").addEventListener("click", (e) => {
    e.preventDefault();
    if (!currentUser) {
      openModal("login-modal");
      showStatus("Please log in to report an issue or suggestion.", "info");
      return;
    }
    const formMsg = $("#report-form-msg");
    if (formMsg) {
      formMsg.classList.add("hidden");
      formMsg.textContent = "";
    }
    openModal("report-modal");
  });
}

if ($("#dash-open-report-btn")) {
  $("#dash-open-report-btn").addEventListener("click", () => {
    const formMsg = $("#report-form-msg");
    if (formMsg) {
      formMsg.classList.add("hidden");
      formMsg.textContent = "";
    }
    openModal("report-modal");
  });
}

const reportForm = $("#report-form");
if (reportForm) {
  reportForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const formMsg = $("#report-form-msg");
    formMsg.classList.add("hidden");
    formMsg.textContent = "";

    if (currentUser && currentUser.is_blocked) {
      formMsg.textContent = "Your account is restricted from submitting new reports.";
      formMsg.className = "form-feedback form-error";
      formMsg.classList.remove("hidden");
      return;
    }

    const submitBtn = $("#submit-report-btn");
    submitBtn.disabled = true;
    submitBtn.textContent = "Submitting Report...";

    try {
      let evidence_path = null;
      const fileInput = $("#report-evidence-file");
      if (fileInput && fileInput.files && fileInput.files.length > 0) {
        const file = fileInput.files[0];
        if (file.size > 5 * 1024 * 1024) {
          throw new Error("Supporting evidence file exceeds the 5MB size limit.");
        }
        const formData = new FormData();
        formData.append("file", file);
        const token = localStorage.getItem("token");
        const uploadRes = await fetch("/api/user/reports/upload-evidence", {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: formData,
        });
        const uploadJson = await uploadRes.json().catch(() => ({}));
        if (!uploadRes.ok) {
          throw new Error(uploadJson.detail || "Failed to upload supporting evidence.");
        }
        evidence_path = uploadJson.evidence_path;
      }

      const payload = {
        category: $("#report-category").value,
        transport_mode: $("#report-transport-mode").value,
        related_route_info: $("#report-related-route").value.trim() || null,
        title: $("#report-title").value.trim(),
        description: $("#report-desc").value.trim(),
        evidence_path: evidence_path,
      };

      const res = await api("/api/user/reports", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      closeModal("report-modal");
      reportForm.reset();
      showStatus(`Report ${res.report_id} submitted successfully! Reference ID: ${res.report_id}. Our administrative team will review it.`, "success");

      // Reload reports if reports pane is currently active
      const reportsPane = $("#dash-pane-reports");
      if (reportsPane && reportsPane.classList.contains("active")) {
        loadDashboardReports();
      }
    } catch (err) {
      formMsg.textContent = err.message;
      formMsg.className = "form-feedback form-error";
      formMsg.classList.remove("hidden");
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Submit Report";
    }
  });
}

async function loadDashboardReports() {
  const container = $("#my-reports-list");
  if (!container) return;
  container.innerHTML = "<p class='empty-state-text'>Loading your submitted reports...</p>";

  try {
    const reports = await api("/api/user/reports");
    if (!reports.length) {
      container.innerHTML = "<p class='empty-state-text'>You have not submitted any issue reports or suggestions yet.</p>";
      return;
    }

    container.innerHTML = reports.map((r) => {
      const statusCls = String(r.status || "PENDING").toLowerCase();
      const modeBadge = getModeBadge(r.transport_mode, 12);
      return `
        <div class="report-item-card" data-report-id="${escapeHtml(r.report_id)}">
          <div class="report-item-top">
            <div style="display:flex; align-items:center; gap:8px;">
              <span class="report-item-id">${escapeHtml(r.report_id)}</span>
              <span class="pill small">${modeBadge} ${escapeHtml(r.transport_mode || 'General')}</span>
            </div>
            <span class="status-pill ${statusCls}">${escapeHtml(r.status)}</span>
          </div>
          <div style="font-weight:700; font-size:0.95rem; margin-top:4px; color:var(--navy);">
            ${escapeHtml(r.title)}
          </div>
          <div style="display:flex; gap:12px; font-size:0.8rem; color:var(--text-muted); margin-top:4px; flex-wrap:wrap;">
            <span>Category: <b>${escapeHtml(r.category)}</b></span>
            ${r.related_route_info ? `<span>Route/Service: <b>${escapeHtml(r.related_route_info)}</b></span>` : ''}
            <span>Submitted: ${new Date(r.submitted_at).toLocaleDateString()}</span>
          </div>
          <div class="report-item-details" style="display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; margin-top:6px;">
            ${escapeHtml(r.description)}
          </div>
          ${r.admin_response ? `
            <div class="report-item-admin-notes">
              <strong>Admin Note:</strong> ${escapeHtml(r.admin_response)}
            </div>
          ` : ''}
          <div style="display:flex; justify-content:flex-end; margin-top:8px;">
            <button type="button" class="button outline small" style="font-size:0.78rem; height:28px;" onclick="openReportDetailModal('${escapeHtml(r.report_id)}')">
              View Details ➔
            </button>
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    container.innerHTML = `<p class="form-error">Could not load reports: ${err.message}</p>`;
  }
}

window.openReportDetailModal = async (reportId) => {
  try {
    const report = await api(`/api/user/reports/${encodeURIComponent(reportId)}`);
    $("#rep-detail-title").textContent = report.title;
    $("#rep-detail-id").textContent = report.report_id;

    const badge = $("#rep-detail-status-badge");
    const st = String(report.status || "PENDING").toLowerCase();
    badge.className = `status-pill ${st}`;
    badge.textContent = report.status;

    $("#rep-detail-date").textContent = `Submitted: ${new Date(report.submitted_at).toLocaleString()}`;
    $("#rep-detail-category").textContent = report.category;
    $("#rep-detail-mode").textContent = report.transport_mode || "General";
    $("#rep-detail-route").textContent = report.related_route_info || "None specified";
    $("#rep-detail-description").textContent = report.description;

    const evidenceBox = $("#rep-detail-evidence-box");
    const evidenceLink = $("#rep-detail-evidence-link");
    if (report.evidence_path) {
      evidenceLink.href = report.evidence_path;
      evidenceBox.classList.remove("hidden");
    } else {
      evidenceBox.classList.add("hidden");
    }

    const adminBox = $("#rep-detail-admin-response-box");
    const adminHeading = $("#rep-detail-response-heading");
    const adminResp = $("#rep-detail-admin-response");
    const adminMeta = $("#rep-detail-review-meta");

    if (report.admin_response || report.status === "VERIFIED" || report.status === "REJECTED") {
      adminBox.classList.remove("hidden");
      if (report.status === "VERIFIED") {
        adminBox.style.background = "#f0fdf4";
        adminBox.style.borderColor = "#86efac";
        adminHeading.style.color = "#166534";
        adminHeading.textContent = "Admin Verification Note:";
        adminResp.style.color = "#14532d";
        adminResp.textContent = report.admin_response || "Your report has been verified and confirmed by our administrative team.";
      } else if (report.status === "REJECTED") {
        adminBox.style.background = "#fef2f2";
        adminBox.style.borderColor = "#fca5a5";
        adminHeading.style.color = "#991b1b";
        adminHeading.textContent = "Admin Rejection Reason:";
        adminResp.style.color = "#7f1d1d";
        adminResp.textContent = report.admin_response || "Your report was reviewed and rejected by our administrative team.";
      } else {
        adminBox.style.background = "#eff6ff";
        adminBox.style.borderColor = "#93c5fd";
        adminHeading.style.color = "#1e40af";
        adminHeading.textContent = "Admin Note:";
        adminResp.style.color = "#1e3a8a";
        adminResp.textContent = report.admin_response || "";
      }
      adminMeta.textContent = report.reviewed_at ? `Reviewed at: ${new Date(report.reviewed_at).toLocaleString()}` : "";
    } else {
      adminBox.classList.add("hidden");
    }

    const deleteBtn = $("#rep-detail-delete-btn");
    deleteBtn.onclick = async () => {
      if (!confirm(`Remove report ${report.report_id} from your history? The administrative record will remain preserved.`)) {
        return;
      }
      try {
        await api(`/api/user/reports/${encodeURIComponent(report.report_id)}`, { method: "DELETE" });
        closeModal("report-detail-modal");
        loadDashboardReports();
        showStatus(`Report ${report.report_id} removed from your history.`, "info");
      } catch (err) {
        alert(`Could not remove report: ${err.message}`);
      }
    };

    openModal("report-detail-modal");
  } catch (err) {
    alert(`Could not load report details: ${err.message}`);
  }
};

// -------------------------------------------------------------
// User Notifications System
// -------------------------------------------------------------

async function loadUnreadNotificationCount() {
  if (!currentUser) {
    const badge = $("#notif-count-badge");
    if (badge) badge.classList.add("hidden");
    const dashBadge = $("#dash-notif-badge");
    if (dashBadge) dashBadge.classList.add("hidden");
    return;
  }
  try {
    const res = await api("/api/user/notifications/unread-count");
    const count = Number(res.unread_count) || 0;
    const badge = $("#notif-count-badge");
    const dashBadge = $("#dash-notif-badge");
    if (badge) {
      if (count > 0) {
        badge.textContent = count > 99 ? "99+" : count;
        badge.classList.remove("hidden");
      } else {
        badge.classList.add("hidden");
      }
    }
    if (dashBadge) {
      if (count > 0) {
        dashBadge.textContent = count > 99 ? "99+" : count;
        dashBadge.classList.remove("hidden");
      } else {
        dashBadge.classList.add("hidden");
      }
    }
  } catch {
    // Non-blocking
  }
}

function formatNotifTypeBadge(type) {
  const t = String(type || "").toUpperCase();
  if (t === "REPORT_VERIFIED") {
    return '<span class="notif-type-pill verified">Verified</span>';
  }
  if (t === "REPORT_REJECTED") {
    return '<span class="notif-type-pill rejected">Rejected</span>';
  }
  if (t === "ADMIN_WARNING") {
    return '<span class="notif-type-pill warning">⚠️ Warning</span>';
  }
  if (t === "ACCOUNT_BLOCKED") {
    return '<span class="notif-type-pill blocked">⛔ Blocked</span>';
  }
  return '<span class="notif-type-pill notice">Notice</span>';
}

async function loadDashboardNotifications() {
  const container = $("#my-notifications-list");
  if (!container) return;
  container.innerHTML = "<p class='empty-state-text'>Loading notifications...</p>";

  try {
    const list = await api("/api/user/notifications");
    if (!list.length) {
      container.innerHTML = "<p class='empty-state-text'>You have no notifications right now.</p>";
      return;
    }

    container.innerHTML = list.map((n) => {
      const unreadClass = n.is_read ? "" : " unread";
      const typeBadge = formatNotifTypeBadge(n.notification_type);
      return `
        <div class="notif-item${unreadClass}" data-notif-id="${n.id}">
          <div class="notif-header">
            <div style="display:flex; align-items:center; gap:8px;">
              ${!n.is_read ? '<span class="notif-unread-dot" title="Unread"></span>' : ''}
              ${typeBadge}
              <h5 class="notif-title">${escapeHtml(n.title)}</h5>
            </div>
            <span class="notif-time">${new Date(n.created_at).toLocaleString()}</span>
          </div>
          <p class="notif-body">${escapeHtml(n.message)}</p>
        </div>
      `;
    }).join("");

    container.querySelectorAll(".notif-item.unread").forEach((el) => {
      el.addEventListener("click", async () => {
        const nid = el.dataset.notifId;
        if (nid) {
          try {
            await api(`/api/user/notifications/${nid}/read`, { method: "PUT" });
            el.classList.remove("unread");
            const dot = el.querySelector(".notif-unread-dot");
            if (dot) dot.remove();
            loadUnreadNotificationCount();
          } catch (err) {
            console.error("Failed to mark notification as read", err);
          }
        }
      });
    });
  } catch (err) {
    container.innerHTML = `<p class="form-error">Could not load notifications: ${err.message}</p>`;
  }
}

if ($("#notif-btn")) {
  $("#notif-btn").addEventListener("click", () => {
    if (!currentUser) {
      openModal("login-modal");
      return;
    }
    openDashboardModal("notifications");
  });
}

if ($("#mark-all-notifs-btn")) {
  $("#mark-all-notifs-btn").addEventListener("click", async () => {
    try {
      await api("/api/user/notifications/mark-all-read", { method: "PUT" });
      loadDashboardNotifications();
      loadUnreadNotificationCount();
      showStatus("All notifications marked as read.", "info");
    } catch (err) {
      alert(`Could not mark notifications as read: ${err.message}`);
    }
  });
}

// Check notifications periodically every 30 seconds
setInterval(loadUnreadNotificationCount, 30000);

// -------------------------------------------------------------
// Interactive 64 Districts Map Modal & Zoom Viewer
// -------------------------------------------------------------
let mapZoom = 1;

function applyMapZoom(zoom) {
  mapZoom = Math.min(Math.max(zoom, 0.75), 3.5);
  const img = $("#map-full-image");
  const badge = $("#map-zoom-val");
  if (img) {
    img.style.transform = `scale(${mapZoom})`;
  }
  if (badge) {
    badge.textContent = `${Math.round(mapZoom * 100)}%`;
  }
}

function openMapModal() {
  applyMapZoom(1);
  openModal("map-modal");
  const viewport = $("#map-viewport");
  if (viewport) {
    viewport.scrollTop = 0;
    viewport.scrollLeft = 0;
  }
}

if ($("#open-map-btn")) {
  $("#open-map-btn").addEventListener("click", openMapModal);
}
if ($("#open-map-modal-btn")) {
  $("#open-map-modal-btn").addEventListener("click", openMapModal);
}
if ($("#map-preview-trigger")) {
  $("#map-preview-trigger").addEventListener("click", openMapModal);
}

if ($("#map-zoom-in")) {
  $("#map-zoom-in").addEventListener("click", () => applyMapZoom(mapZoom + 0.25));
}
if ($("#map-zoom-out")) {
  $("#map-zoom-out").addEventListener("click", () => applyMapZoom(mapZoom - 0.25));
}
if ($("#map-zoom-reset")) {
  $("#map-zoom-reset").addEventListener("click", () => applyMapZoom(1));
}

// Mouse wheel zoom & pan support inside map viewport
const mapViewport = $("#map-viewport");
if (mapViewport) {
  mapViewport.addEventListener("wheel", (e) => {
    e.preventDefault();
    if (e.deltaY < 0) {
      applyMapZoom(mapZoom + 0.15);
    } else {
      applyMapZoom(mapZoom - 0.15);
    }
  }, { passive: false });

  // Drag-to-pan support
  let isPanning = false;
  let startX = 0;
  let startY = 0;
  let scrollLeftStart = 0;
  let scrollTopStart = 0;

  mapViewport.addEventListener("mousedown", (e) => {
    isPanning = true;
    startX = e.pageX - mapViewport.offsetLeft;
    startY = e.pageY - mapViewport.offsetTop;
    scrollLeftStart = mapViewport.scrollLeft;
    scrollTopStart = mapViewport.scrollTop;
  });

  window.addEventListener("mouseup", () => {
    isPanning = false;
  });

  mapViewport.addEventListener("mousemove", (e) => {
    if (!isPanning) return;
    e.preventDefault();
    const x = e.pageX - mapViewport.offsetLeft;
    const y = e.pageY - mapViewport.offsetTop;
    mapViewport.scrollLeft = scrollLeftStart - (x - startX);
    mapViewport.scrollTop = scrollTopStart - (y - startY);
  });
}

// Open 64 districts map modal when clicking topbar nav map link
if ($("#nav-map-link")) {
  $("#nav-map-link").addEventListener("click", (e) => {
    e.preventDefault();
    openMapModal();
  });
}

// Mobile sidebar drawer interactions
const mobileSidebarToggle = $("#mobile-sidebar-toggle");
const appSidebar = $("#app-sidebar");
const sidebarBackdrop = $("#sidebar-backdrop");
const sidebarCloseBtn = $("#sidebar-close-btn");

if (mobileSidebarToggle && appSidebar) {
  mobileSidebarToggle.addEventListener("click", () => {
    appSidebar.classList.toggle("open");
    if (sidebarBackdrop) sidebarBackdrop.classList.toggle("visible");
  });
}

if (sidebarCloseBtn && appSidebar) {
  sidebarCloseBtn.addEventListener("click", () => {
    appSidebar.classList.remove("open");
    if (sidebarBackdrop) sidebarBackdrop.classList.remove("visible");
  });
}

if (sidebarBackdrop && appSidebar) {
  sidebarBackdrop.addEventListener("click", () => {
    appSidebar.classList.remove("open");
    sidebarBackdrop.classList.remove("visible");
  });
}

document.querySelectorAll(".sidebar-nav-item").forEach((item) => {
  item.addEventListener("click", () => {
    if (window.innerWidth <= 900 && appSidebar) {
      appSidebar.classList.remove("open");
      if (sidebarBackdrop) sidebarBackdrop.classList.remove("visible");
    }
  });
});

// Startup initializations
loadDistricts();
initAuth();

// Initialize page view based on initial URL (direct visit or browser refresh)
const initialPage = getPageFromUrl();
switchMainPage(initialPage, { replaceHistory: initialPage !== "journey", scroll: false });
