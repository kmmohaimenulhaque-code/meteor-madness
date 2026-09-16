import { useMemo, useState } from "react";

/**
 * NASA GIBS / Worldview impact-location view.
 *
 * The snapshot is generated from a geographic BBOX around the
 * supplied impact coordinates.
 *
 * The impact marker is positioned using the same BBOX rather
 * than being hard-coded to the centre of the image.
 */

const SNAPSHOT_SPAN = 2.5;
const SNAPSHOT_TIME = "2024-06-15";

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function isValidCoordinate(lat, lon) {
  return (
    Number.isFinite(lat) &&
    Number.isFinite(lon) &&
    lat >= -90 &&
    lat <= 90 &&
    lon >= -180 &&
    lon <= 180
  );
}

/**
 * Geographic bounds used by the NASA snapshot.
 */
function getSnapshotBounds(lat, lon, span = SNAPSHOT_SPAN) {
  return {
    south: clamp(lat - span, -90, 90),
    north: clamp(lat + span, -90, 90),
    west: clamp(lon - span, -180, 180),
    east: clamp(lon + span, -180, 180),
  };
}

/**
 * Convert geographic coordinates to image percentages.
 *
 * Longitude:
 *   west  -> 0%
 *   east  -> 100%
 *
 * Latitude:
 *   north -> 0%
 *   south -> 100%
 *
 * The Y axis is inverted because browser image coordinates
 * increase from top to bottom.
 */
function getMarkerPosition(lat, lon, bounds) {
  const { south, north, west, east } = bounds;

  const longitudeRange = east - west;
  const latitudeRange = north - south;

  if (longitudeRange <= 0 || latitudeRange <= 0) {
    return {
      left: 50,
      top: 50,
    };
  }

  const left =
    ((lon - west) / longitudeRange) * 100;

  const top =
    ((north - lat) / latitudeRange) * 100;

  return {
    left: clamp(left, 0, 100),
    top: clamp(top, 0, 100),
  };
}

/**
 * Build the NASA Worldview Snapshot URL.
 */
function worldviewSnapshotUrl(
  lat,
  lon,
  span = SNAPSHOT_SPAN
) {
  const {
    south,
    north,
    west,
    east,
  } = getSnapshotBounds(lat, lon, span);

  const params = new URLSearchParams({
    REQUEST: "GetSnapshot",

    LAYERS:
      "MODIS_Terra_CorrectedReflectance_TrueColor,Coastlines_15m",

    CRS: "EPSG:4326",

    TIME: SNAPSHOT_TIME,

    WRAP: "DAY",

    /*
     * Geographic BBOX:
     * south, west, north, east
     */
    BBOX:
      `${south},${west},${north},${east}`,

    FORMAT: "image/jpeg",

    WIDTH: "960",

    HEIGHT: "640",

    AUTOSCALE: "TRUE",
  });

  return (
    "https://wvs.earthdata.nasa.gov/api/v1/snapshot?" +
    params.toString()
  );
}

/**
 * Global Blue Marble fallback.
 *
 * NOTE:
 * This is only a fallback image.
 * The precise impact marker is only geographically exact
 * when the primary Worldview snapshot is being displayed.
 */
function blueMarbleUrl(lat, lon) {
  const z = 5;
  const n = 2 ** z;

  const x = Math.floor(
    ((lon + 180) / 360) * n
  );

  const y = Math.floor(
    ((90 - lat) / 180) * n
  );

  return (
    "https://gibs.earthdata.nasa.gov/wmts/" +
    "epsg4326/best/" +
    "BlueMarble_NextGeneration/" +
    "default/2004-01-01/500m/" +
    `${z}/${y}/${x}.jpg`
  );
}

export default function GibsImpactView({
  latitude,
  longitude,
  surface,
}) {
  const lat = Number(latitude);
  const lon = Number(longitude);

  const [failed, setFailed] = useState(false);

  const validCoordinates = isValidCoordinate(
    lat,
    lon
  );

  /**
   * The exact geographic BBOX used to generate
   * the primary NASA snapshot.
   */
  const bounds = useMemo(() => {
    if (!validCoordinates) {
      return null;
    }

    return getSnapshotBounds(
      lat,
      lon,
      SNAPSHOT_SPAN
    );
  }, [
    lat,
    lon,
    validCoordinates,
  ]);

  /**
   * Primary NASA Worldview snapshot.
   */
  const primary = useMemo(() => {
    if (!validCoordinates) {
      return null;
    }

    return worldviewSnapshotUrl(
      lat,
      lon,
      SNAPSHOT_SPAN
    );
  }, [
    lat,
    lon,
    validCoordinates,
  ]);

  /**
   * Fallback NASA Blue Marble tile.
   */
  const fallback = useMemo(() => {
    if (!validCoordinates) {
      return null;
    }

    return blueMarbleUrl(
      lat,
      lon
    );
  }, [
    lat,
    lon,
    validCoordinates,
  ]);

  /**
   * Calculate the exact position of the impact
   * coordinate inside the snapshot image.
   */
  const markerPosition = useMemo(() => {
    if (!bounds || !validCoordinates) {
      return {
        left: 50,
        top: 50,
      };
    }

    return getMarkerPosition(
      lat,
      lon,
      bounds
    );
  }, [
    lat,
    lon,
    bounds,
    validCoordinates,
  ]);

  const src = failed
    ? fallback
    : primary;

  if (!validCoordinates) {
    return (
      <div className="story-gibs-live">
        <div className="story-gibs-missing">
          Set valid coordinates for GIBS view
        </div>
      </div>
    );
  }

  return (
    <div className="story-gibs-live">
      {src ? (
        <img
          key={src}
          src={src}
          alt={
            `NASA GIBS satellite view near ` +
            `${lat.toFixed(4)}, ${lon.toFixed(4)}`
          }
          className="story-gibs-img"
          onError={() => {
            if (!failed) {
              setFailed(true);
            }
          }}
        />
      ) : (
        <div className="story-gibs-missing">
          Unable to load NASA GIBS imagery
        </div>
      )}

      {/*
       * Coordinate-aware impact marker.
       *
       * IMPORTANT:
       * This is deliberately NOT centred.
       */
      {!failed && (
        <div
          className="story-impact-pin"
          style={{
            left: `${markerPosition.left}%`,
            top: `${markerPosition.top}%`,
          }}
          aria-label={
            `Impact location ` +
            `${lat.toFixed(4)}, ${lon.toFixed(4)}`
          }
        >
          <span />
        </div>
      )}

      <div className="story-gibs-label">
        NASA GIBS / Worldview ·{" "}
        {lat.toFixed(4)}°,{" "}
        {lon.toFixed(4)}° ·{" "}
        {String(surface ?? "UNKNOWN")}
      </div>
    </div>
  );
}
