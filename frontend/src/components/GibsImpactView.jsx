import { useEffect, useMemo, useState } from "react";

/**
 * Story Mode NASA GIBS view.
 *
 * IMPORTANT:
 * This uses the SAME NASA GIBS WMS system as EarthImpactMap.jsx:
 *
 *   https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi
 *
 * Same:
 * - MODIS Terra Corrected Reflectance True Color layer
 * - 12 degree latitude span
 * - latitude-aware longitude span
 * - EPSG:4326
 * - WMS GetMap
 * - yesterday's imagery date
 *
 * The only difference is the Story Mode presentation/overlay.
 */

const NASA_GIBS_WMS =
  "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi";

const SATELLITE_LAYER =
  "MODIS_Terra_CorrectedReflectance_TrueColor";

const DEFAULT_MAP_SPAN_DEG = 12;

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function normaliseLongitude(lon) {
  let value = Number(lon);

  if (!Number.isFinite(value)) {
    return 0;
  }

  while (value > 180) {
    value -= 360;
  }

  while (value < -180) {
    value += 360;
  }

  return value;
}

function isValidCoordinate(latitude, longitude) {
  return (
    Number.isFinite(latitude) &&
    Number.isFinite(longitude) &&
    latitude >= -90 &&
    latitude <= 90 &&
    longitude >= -180 &&
    longitude <= 180
  );
}

/**
 * EXACT same geographic calculation used by
 * EarthImpactMap.jsx.
 */
function getSatelliteBounds(latitude, longitude) {
  const latSpan = DEFAULT_MAP_SPAN_DEG;

  const cosLat = Math.cos(
    (latitude * Math.PI) / 180
  );

  const lonSpan =
    DEFAULT_MAP_SPAN_DEG /
    Math.max(Math.abs(cosLat), 0.25);

  const minLat = clamp(
    latitude - latSpan / 2,
    -89,
    89
  );

  const maxLat = clamp(
    latitude + latSpan / 2,
    -89,
    89
  );

  const minLon = normaliseLongitude(
    longitude - lonSpan / 2
  );

  const maxLon = normaliseLongitude(
    longitude + lonSpan / 2
  );

  return {
    minLat,
    maxLat,
    minLon,
    maxLon,
  };
}

/**
 * EXACT same NASA GIBS WMS URL construction
 * used by EarthImpactMap.jsx.
 */
function buildSatelliteUrl(latitude, longitude) {
  const bounds = getSatelliteBounds(
    latitude,
    longitude
  );

  // GIBS imagery is time-dependent.
  // Use yesterday because the latest complete MODIS
  // composite may not yet be available for today.
  const date = new Date();

  date.setUTCDate(
    date.getUTCDate() - 1
  );

  const year = date.getUTCFullYear();

  const month = String(
    date.getUTCMonth() + 1
  ).padStart(2, "0");

  const day = String(
    date.getUTCDate()
  ).padStart(2, "0");

  const imageDate =
    `${year}-${month}-${day}`;

  const params = new URLSearchParams({
    SERVICE: "WMS",
    VERSION: "1.1.1",
    REQUEST: "GetMap",

    LAYERS: SATELLITE_LAYER,

    STYLES: "",

    SRS: "EPSG:4326",

    BBOX:
      `${bounds.minLon},${bounds.minLat},` +
      `${bounds.maxLon},${bounds.maxLat}`,

    WIDTH: "1000",
    HEIGHT: "700",

    FORMAT: "image/jpeg",

    TRANSPARENT: "FALSE",

    TIME: imageDate,
  });

  return (
    `${NASA_GIBS_WMS}?${params.toString()}`
  );
}

/**
 * Convert the impact coordinate into the same
 * geographic bounding box used by the GIBS image.
 *
 * This makes the marker correspond to the actual
 * satellite image rather than being hard-coded to
 * the centre of the image.
 */
function getMarkerPosition(
  latitude,
  longitude,
  bounds
) {
  if (!bounds) {
    return {
      left: 50,
      top: 50,
    };
  }

  const {
    minLat,
    maxLat,
    minLon,
    maxLon,
  } = bounds;

  let lon = longitude;

  /*
   * Handle the normalised longitude range.
   * This matters if the GIBS viewport crosses
   * the international date line.
   */
  if (maxLon < minLon) {
    if (lon < minLon) {
      lon += 360;
    }
  }

  let longitudeRange = maxLon - minLon;

  if (longitudeRange < 0) {
    longitudeRange += 360;
  }

  const latitudeRange =
    maxLat - minLat;

  if (
    longitudeRange <= 0 ||
    latitudeRange <= 0
  ) {
    return {
      left: 50,
      top: 50,
    };
  }

  let longitudeOffset =
    lon - minLon;

  if (longitudeOffset < 0) {
    longitudeOffset += 360;
  }

  const left =
    (longitudeOffset /
      longitudeRange) *
    100;

  /*
   * Image Y coordinates increase downward,
   * whereas latitude increases upward.
   */
  const top =
    ((maxLat - latitude) /
      latitudeRange) *
    100;

  return {
    left: clamp(left, 0, 100),
    top: clamp(top, 0, 100),
  };
}

export default function GibsImpactView({
  latitude,
  longitude,
  surface,
}) {
  const lat = Number(latitude);
  const lon = normaliseLongitude(
    Number(longitude)
  );

  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState(false);

  const validCoordinates =
    isValidCoordinate(lat, lon);

  /*
   * SAME 12° GIBS viewport as the main simulator.
   */
  const bounds = useMemo(() => {
    if (!validCoordinates) {
      return null;
    }

    return getSatelliteBounds(
      lat,
      lon
    );
  }, [
    lat,
    lon,
    validCoordinates,
  ]);

  /*
   * SAME GIBS WMS URL as the main simulator.
   */
  const satelliteUrl = useMemo(() => {
    if (!validCoordinates) {
      return null;
    }

    return buildSatelliteUrl(
      lat,
      lon
    );
  }, [
    lat,
    lon,
    validCoordinates,
  ]);

  /*
   * Position the Story Mode impact marker
   * against the actual GIBS bounding box.
   */
  const markerPosition = useMemo(() => {
    return getMarkerPosition(
      lat,
      lon,
      bounds
    );
  }, [
    lat,
    lon,
    bounds,
  ]);

  /*
   * Reset image state whenever the coordinates
   * or resulting GIBS URL changes.
   */
  useEffect(() => {
    setFailed(false);
    setLoaded(false);
  }, [satelliteUrl]);

  if (!validCoordinates) {
    return (
      <div className="story-gibs-live">
        <div className="story-gibs-missing">
          Set valid coordinates for GIBS view
        </div>
      </div>
    );
  }

  if (failed) {
    return (
      <div className="story-gibs-live">
        <div className="story-gibs-missing">
          NASA GIBS imagery unavailable
        </div>

        <div className="story-gibs-label">
          NASA GIBS / MODIS ·{" "}
          {lat.toFixed(4)}°,{" "}
          {lon.toFixed(4)}° ·{" "}
          {String(surface ?? "UNKNOWN")}
        </div>
      </div>
    );
  }

  return (
    <div className="story-gibs-live">
      <img
        key={satelliteUrl}
        src={satelliteUrl}
        alt={`NASA GIBS MODIS satellite view near ${lat.toFixed(
          4
        )}, ${lon.toFixed(4)}`}
        className="story-gibs-img"
        onLoad={() => {
          setLoaded(true);
        }}
        onError={() => {
          setFailed(true);
        }}
      />

      {loaded && (
        <div
          className="story-impact-pin"
          style={{
            left: `${markerPosition.left}%`,
            top: `${markerPosition.top}%`,
          }}
          aria-label={`Impact location ${lat.toFixed(
            4
          )}, ${lon.toFixed(4)}`}
        >
          <span />
        </div>
      )}

      <div className="story-gibs-label">
        NASA GIBS / MODIS Terra ·{" "}
        {lat.toFixed(4)}°,{" "}
        {lon.toFixed(4)}° ·{" "}
        {String(surface ?? "UNKNOWN")}
      </div>
    </div>
  );
}
