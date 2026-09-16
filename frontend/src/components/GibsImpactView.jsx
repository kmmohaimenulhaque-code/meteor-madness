import { useEffect, useMemo, useState } from "react";

/**
 * Story Mode NASA GIBS view.
 *
 * IMPORTANT:
 * Story Mode must use the ACTUAL MODELLED IMPACT
 * coordinates from the simulation trajectory.
 *
 * Coordinate priority:
 *
 *   final_latitude_deg
 *   impact_latitude_deg
 *   latitude_deg
 *   entry_latitude_deg
 *
 * and the equivalent longitude fields.
 *
 * This follows the same coordinate extraction logic
 * used by EarthImpactMap.jsx.
 */

const NASA_GIBS_WMS =
  "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi";

const SATELLITE_LAYER =
  "MODIS_Terra_CorrectedReflectance_TrueColor";

const DEFAULT_MAP_SPAN_DEG = 12;

function clamp(value, min, max) {
  return Math.min(
    Math.max(value, min),
    max
  );
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

function isValidCoordinate(
  latitude,
  longitude
) {
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
 * Extract the MODELLED IMPACT coordinate.
 *
 * This is deliberately the same priority used
 * by EarthImpactMap.jsx.
 */
function getImpactCoordinates(
  trajectory,
  fallbackLatitude,
  fallbackLongitude
) {
  const latitudeCandidates = [
    trajectory?.final_latitude_deg,
    trajectory?.impact_latitude_deg,
    trajectory?.latitude_deg,
    trajectory?.entry_latitude_deg,
  ];

  const longitudeCandidates = [
    trajectory?.final_longitude_deg,
    trajectory?.impact_longitude_deg,
    trajectory?.longitude_deg,
    trajectory?.entry_longitude_deg,
  ];

  const latitude =
    latitudeCandidates.find((value) =>
      Number.isFinite(Number(value))
    ) ??
    fallbackLatitude;

  const longitude =
    longitudeCandidates.find((value) =>
      Number.isFinite(Number(value))
    ) ??
    fallbackLongitude;

  const parsedLatitude =
    Number(latitude);

  const parsedLongitude =
    Number(longitude);

  return {
    latitude: clamp(
      Number.isFinite(parsedLatitude)
        ? parsedLatitude
        : 0,
      -89.5,
      89.5
    ),

    longitude: normaliseLongitude(
      Number.isFinite(parsedLongitude)
        ? parsedLongitude
        : 0
    ),
  };
}

/**
 * EXACT same geographic calculation used
 * by EarthImpactMap.jsx.
 */
function getSatelliteBounds(
  latitude,
  longitude
) {
  const latSpan =
    DEFAULT_MAP_SPAN_DEG;

  const cosLat = Math.cos(
    (latitude * Math.PI) / 180
  );

  const lonSpan =
    DEFAULT_MAP_SPAN_DEG /
    Math.max(
      Math.abs(cosLat),
      0.25
    );

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

  const minLon =
    normaliseLongitude(
      longitude - lonSpan / 2
    );

  const maxLon =
    normaliseLongitude(
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
function buildSatelliteUrl(
  latitude,
  longitude
) {
  const bounds =
    getSatelliteBounds(
      latitude,
      longitude
    );

  /*
   * GIBS imagery is time-dependent.
   * Use yesterday because the latest complete
   * MODIS composite may not yet be available
   * for today.
   */
  const date = new Date();

  date.setUTCDate(
    date.getUTCDate() - 1
  );

  const year =
    date.getUTCFullYear();

  const month = String(
    date.getUTCMonth() + 1
  ).padStart(2, "0");

  const day = String(
    date.getUTCDate()
  ).padStart(2, "0");

  const imageDate =
    `${year}-${month}-${day}`;

  const params =
    new URLSearchParams({
      SERVICE: "WMS",
      VERSION: "1.1.1",
      REQUEST: "GetMap",

      LAYERS:
        SATELLITE_LAYER,

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
 * Convert the modelled impact coordinate
 * into the correct position inside the
 * GIBS image.
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
   * Handle a viewport crossing the
   * international date line.
   */
  if (maxLon < minLon) {
    if (lon < minLon) {
      lon += 360;
    }
  }

  let longitudeRange =
    maxLon - minLon;

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
   * Image Y increases downward while
   * latitude increases upward.
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
  trajectory,
  latitude,
  longitude,
  surface,
}) {
  /*
   * IMPORTANT:
   *
   * These are now the MODELLED IMPACT coordinates.
   *
   * The original input latitude/longitude are
   * only fallbacks if no trajectory coordinate
   * exists.
   */
  const impact = useMemo(() => {
    return getImpactCoordinates(
      trajectory,
      latitude,
      longitude
    );
  }, [
    trajectory,
    latitude,
    longitude,
  ]);

  const lat = impact.latitude;
  const lon = impact.longitude;

  const [failed, setFailed] =
    useState(false);

  const [loaded, setLoaded] =
    useState(false);

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
   *
   * IMPORTANT:
   * Uses MODELLED impact coordinates.
   */
  const satelliteUrl =
    useMemo(() => {
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
   * Put the impact marker on the actual
   * modelled impact position.
   */
  const markerPosition =
    useMemo(() => {
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
   * Reset image state whenever the
   * modelled impact coordinate changes.
   */
  useEffect(() => {
    setFailed(false);
    setLoaded(false);
  }, [satelliteUrl]);

  if (!validCoordinates) {
    return (
      <div className="story-gibs-live">
        <div className="story-gibs-missing">
          Set valid impact coordinates
          for GIBS view
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
          NASA GIBS / MODIS Terra ·{" "}
          {lat.toFixed(4)}°,{ " " }
          {lon.toFixed(4)}° ·{" "}
          {String(
            surface ?? "UNKNOWN"
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="story-gibs-live">
      <img
        key={satelliteUrl}
        src={satelliteUrl}
        alt={`NASA GIBS MODIS satellite view at modelled impact location ${lat.toFixed(
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
          aria-label={`Modelled impact location ${lat.toFixed(
            4
          )}, ${lon.toFixed(4)}`}
        >
          <span />
        </div>
      )}

      <div className="story-gibs-label">
        NASA GIBS / MODIS Terra ·{" "}
        {lat.toFixed(4)}°,{ " " }
        {lon.toFixed(4)}° ·{" "}
        {String(
          surface ?? "UNKNOWN"
        )}
      </div>
    </div>
  );
}
