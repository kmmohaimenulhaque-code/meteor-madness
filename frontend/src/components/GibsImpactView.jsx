import { useMemo, useState } from "react";

/**
 * NASA GIBS / Worldview snapshot around impact coordinates.
 * Falls back to Blue Marble tile grid if snapshot fails.
 */
function clamp(n, lo, hi) {
  return Math.min(hi, Math.max(lo, n));
}

function worldviewSnapshotUrl(lat, lon, span = 2.5) {
  const south = clamp(lat - span, -90, 90);
  const north = clamp(lat + span, -90, 90);
  const west = clamp(lon - span, -180, 180);
  const east = clamp(lon + span, -180, 180);
  // Prefer a recent fixed day for true-color MODIS (GIBS archive)
  const time = "2024-06-15";
  const params = new URLSearchParams({
    REQUEST: "GetSnapshot",
    LAYERS: "MODIS_Terra_CorrectedReflectance_TrueColor,Coastlines_15m",
    CRS: "EPSG:4326",
    TIME: time,
    WRAP: "DAY",
    BBOX: `${south},${west},${north},${east}`,
    FORMAT: "image/jpeg",
    WIDTH: "960",
    HEIGHT: "640",
    AUTOSCALE: "TRUE",
  });
  return `https://wvs.earthdata.nasa.gov/api/v1/snapshot?${params.toString()}`;
}

function blueMarbleUrl(lat, lon) {
  // GIBS Blue Marble Next Generation via WMTS (approx tile at zoom 5)
  const z = 5;
  const n = 2 ** z;
  const x = Math.floor(((lon + 180) / 360) * n);
  const y = Math.floor(((90 - lat) / 180) * n);
  return `https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/BlueMarble_NextGeneration/default/2004-01-01/500m/${z}/${y}/${x}.jpg`;
}

export default function GibsImpactView({ latitude, longitude, surface }) {
  const lat = Number(latitude);
  const lon = Number(longitude);
  const [failed, setFailed] = useState(false);

  const primary = useMemo(() => {
    if (Number.isNaN(lat) || Number.isNaN(lon)) return null;
    return worldviewSnapshotUrl(lat, lon);
  }, [lat, lon]);

  const fallback = useMemo(() => {
    if (Number.isNaN(lat) || Number.isNaN(lon)) return null;
    return blueMarbleUrl(lat, lon);
  }, [lat, lon]);

  const src = failed ? fallback : primary;

  return (
    <div className="story-gibs-live">
      {src ? (
        <img
          key={src}
          src={src}
          alt={`NASA GIBS satellite view near ${lat.toFixed(2)}, ${lon.toFixed(2)}`}
          className="story-gibs-img"
          onError={() => setFailed(true)}
        />
      ) : (
        <div className="story-gibs-missing">Set valid coordinates for GIBS view</div>
      )}
      <div className="story-impact-pin story-impact-pin-center">
        <span />
      </div>
      <div className="story-gibs-label">
        NASA GIBS / Worldview · {lat.toFixed(2)}°, {lon.toFixed(2)}° · {String(surface)}
      </div>
    </div>
  );
}
