import { useMemo, useState } from "react";

/**
 * NASA GIBS / Worldview impact-location view.
 *
 * Creates a NASA Worldview snapshot around the supplied
 * impact coordinates and places the impact marker according
 * to the same geographic bounding box.
 */

const SNAPSHOT_SPAN = 2.5;
const SNAPSHOT_TIME = "2024-06-15";

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
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

function getSnapshotBounds(latitude, longitude) {
  return {
    south: clamp(latitude - SNAPSHOT_SPAN, -90, 90),
    north: clamp(latitude + SNAPSHOT_SPAN, -90, 90),
    west: clamp(longitude - SNAPSHOT_SPAN, -180, 180),
    east: clamp(longitude + SNAPSHOT_SPAN, -180, 180),
  };
}

function getMarkerPosition(latitude, longitude, bounds) {
  if (!bounds) {
    return {
      left: 50,
      top: 50,
    };
  }

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
    ((longitude - west) / longitudeRange) * 100;

  const top =
    ((north - latitude) / latitudeRange) * 100;

  return {
    left: clamp(left, 0, 100),
    top: clamp(top, 0, 100),
  };
}

function buildWorldviewUrl(latitude, longitude) {
  const bounds = getSnapshotBounds(latitude, longitude);

  const params = new URLSearchParams({
    REQUEST: "GetSnapshot",
    LAYERS:
      "MODIS_Terra_CorrectedReflectance_TrueColor,Coastlines_15m",
    CRS: "EPSG:4326",
    TIME: SNAPSHOT_TIME,
    WRAP: "DAY",
    BBOX: [
      bounds.south,
      bounds.west,
      bounds.north,
      bounds.east,
    ].join(","),
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

function buildBlueMarbleUrl(latitude, longitude) {
  const zoom = 5;
  const tileCount = 2 ** zoom;

  const x = Math.floor(
    ((longitude + 180) / 360) * tileCount
  );

  const y = Math.floor(
    ((90 - latitude) / 180) * tileCount
  );

  return (
    "https://gibs.earthdata.nasa.gov/wmts/" +
    "epsg4326/best/" +
    "BlueMarble_NextGeneration/" +
    "default/2004-01-01/500m/" +
    `${zoom}/${y}/${x}.jpg`
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

  const validCoordinates = isValidCoordinate(lat, lon);

  const bounds = useMemo(() => {
    if (!validCoordinates) {
      return null;
    }

    return getSnapshotBounds(lat, lon);
  }, [lat, lon, validCoordinates]);

  const primaryUrl = useMemo(() => {
    if (!validCoordinates) {
      return null;
    }

    return buildWorldviewUrl(lat, lon);
  }, [lat, lon, validCoordinates]);

  const fallbackUrl = useMemo(() => {
    if (!validCoordinates) {
      return null;
    }

    return buildBlueMarbleUrl(lat, lon);
  }, [lat, lon, validCoordinates]);

  const markerPosition = useMemo(() => {
    return getMarkerPosition(lat, lon, bounds);
  }, [lat, lon, bounds]);

  if (!validCoordinates) {
    return (
      <div className="story-gibs-live">
        <div className="story-gibs-missing">
          Set valid coordinates for GIBS view
        </div>
      </div>
    );
  }

  const imageUrl = failed ? fallbackUrl : primaryUrl;

  return (
    <div className="story-gibs-live">
      {imageUrl ? (
        <img
          key={imageUrl}
          src={imageUrl}
          alt={`NASA GIBS satellite view near ${lat.toFixed(
            4
          )}, ${lon.toFixed(4)}`}
          className="story-gibs-img"
          onError={() => {
            setFailed(true);
          }}
        />
      ) : (
        <div className="story-gibs-missing">
          Unable to load NASA GIBS imagery
        </div>
      )}

      {!failed ? (
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
      ) : null}

      <div className="story-gibs-label">
        NASA GIBS / Worldview ·{" "}
        {lat.toFixed(4)}°, {lon.toFixed(4)}° ·{" "}
        {String(surface ?? "UNKNOWN")}
      </div>
    </div>
  );
}
