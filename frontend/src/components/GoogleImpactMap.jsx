import { useEffect, useMemo, useRef, useState } from "react";
import "./GoogleImpactMap.css";

const GOOGLE_MAPS_API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;
const GOOGLE_MAP_ID = import.meta.env.VITE_GOOGLE_MAPS_MAP_ID || "DEMO_MAP_ID";

let googleMapsPromise = null;

function loadGoogleMaps() {
  if (window.google?.maps) {
    return Promise.resolve(window.google.maps);
  }

  if (!GOOGLE_MAPS_API_KEY) {
    return Promise.reject(
      new Error("Missing VITE_GOOGLE_MAPS_API_KEY")
    );
  }

  if (googleMapsPromise) {
    return googleMapsPromise;
  }

  googleMapsPromise = new Promise((resolve, reject) => {
    const existingScript = document.querySelector(
      'script[data-meteor-madness-google-maps="true"]'
    );

    if (existingScript) {
      existingScript.addEventListener("load", () =>
        resolve(window.google.maps)
      );
      existingScript.addEventListener("error", () =>
        reject(new Error("Google Maps failed to load"))
      );
      return;
    }

    const script = document.createElement("script");

    script.src =
      `https://maps.googleapis.com/maps/api/js` +
      `?key=${encodeURIComponent(GOOGLE_MAPS_API_KEY)}` +
      `&loading=async` +
      `&v=weekly` +
      `&auth_referrer_policy=origin`;

    script.async = true;
    script.defer = true;
    script.dataset.meteorMadnessGoogleMaps = "true";

    script.onload = () => {
      if (window.google?.maps) {
        resolve(window.google.maps);
      } else {
        reject(new Error("Google Maps loaded without API"));
      }
    };

    script.onerror = () => {
      reject(new Error("Google Maps API could not be loaded"));
    };

    document.head.appendChild(script);
  });

  return googleMapsPromise;
}

function getImpactCoordinates(trajectory) {
  const latCandidates = [
    trajectory?.final_latitude_deg,
    trajectory?.impact_latitude_deg,
    trajectory?.latitude_deg,
    trajectory?.entry_latitude_deg,
  ];

  const lonCandidates = [
    trajectory?.final_longitude_deg,
    trajectory?.impact_longitude_deg,
    trajectory?.longitude_deg,
    trajectory?.entry_longitude_deg,
  ];

  const lat = latCandidates.find((value) =>
    Number.isFinite(Number(value))
  );

  const lon = lonCandidates.find((value) =>
    Number.isFinite(Number(value))
  );

  return {
    lat: Number(lat ?? 0),
    lng: Number(lon ?? 0),
  };
}

function getEntryCoordinates(trajectory, impact) {
  const lat = Number(trajectory?.entry_latitude_deg);
  const lng = Number(trajectory?.entry_longitude_deg);

  if (Number.isFinite(lat) && Number.isFinite(lng)) {
    return { lat, lng };
  }

  return impact;
}

function getRadius(consequences, keys) {
  for (const key of keys) {
    const value = Number(
      consequences?.[key]
    );

    if (Number.isFinite(value) && value > 0) {
      return value;
    }
  }

  return 0;
}

function getEnvironmentLabel(environment, impactBranch) {
  return (
    environment?.place?.short_name ||
    environment?.place?.display_name ||
    environment?.place_name ||
    environment?.location_name ||
    impactBranch?.location_name ||
    null
  );
}

function createImpactMarkerContent() {
  const element = document.createElement("div");

  element.className = "google-impact-marker";

  element.innerHTML = `
    <div class="google-impact-marker-core">☄</div>
    <div class="google-impact-marker-pulse"></div>
  `;

  return element;
}

function createEntryMarkerContent() {
  const element = document.createElement("div");

  element.className = "google-entry-marker";

  element.innerHTML = `
    <div class="google-entry-marker-core">✦</div>
  `;

  return element;
}

function createLabelContent(title, subtitle) {
  const element = document.createElement("div");

  element.className = "google-map-label";

  element.innerHTML = `
    <div class="google-map-label-title">${title}</div>
    ${
      subtitle
        ? `<div class="google-map-label-subtitle">${subtitle}</div>`
        : ""
    }
  `;

  return element;
}

export default function GoogleImpactMap({
  trajectory,
  consequences,
  environment,
  impactBranch,
  selectedAsteroid,
}) {
  const mapContainerRef = useRef(null);
  const mapRef = useRef(null);
  const objectsRef = useRef([]);

  const [mapReady, setMapReady] = useState(false);
  const [mapError, setMapError] = useState("");
  const [satelliteMode, setSatelliteMode] = useState(false);

  const impact = useMemo(
    () => getImpactCoordinates(trajectory),
    [trajectory]
  );

  const entry = useMemo(
    () => getEntryCoordinates(trajectory, impact),
    [trajectory, impact]
  );

  const environmentLabel = useMemo(
    () =>
      getEnvironmentLabel(
        environment,
        impactBranch
      ),
    [environment, impactBranch]
  );

  const radii = useMemo(
    () => ({
      thermal: getRadius(consequences, [
        "maximum_thermal_radius_m",
        "thermal_radius_m",
      ]),
      blast: getRadius(consequences, [
        "maximum_blast_radius_m",
        "blast_radius_m",
      ]),
      seismic: getRadius(consequences, [
        "maximum_seismic_radius_m",
        "seismic_radius_m",
      ]),
    }),
    [consequences]
  );

  /*
   * ---------------------------------------------------------
   * LOAD GOOGLE MAPS
   * ---------------------------------------------------------
   */

  useEffect(() => {
    let cancelled = false;

    async function initialise() {
      try {
        await loadGoogleMaps();

        if (cancelled || !mapContainerRef.current) {
          return;
        }

        const { Map } =
          await window.google.maps.importLibrary("maps");

        if (cancelled || !mapContainerRef.current) {
          return;
        }

        const map = new Map(
          mapContainerRef.current,
          {
            center: impact,
            zoom: 7,

            mapId: GOOGLE_MAP_ID,

            mapTypeId: "roadmap",

            gestureHandling: "greedy",

            streetViewControl: false,

            fullscreenControl: true,

            mapTypeControl: true,

            zoomControl: true,

            clickableIcons: true,

            restriction: undefined,
          }
        );

        mapRef.current = map;

        setMapReady(true);
      } catch (error) {
        console.error(
          "Google Maps initialisation failed:",
          error
        );

        if (!cancelled) {
          setMapError(
            error instanceof Error
              ? error.message
              : "Google Maps failed to initialise"
          );
        }
      }
    }

    initialise();

    return () => {
      cancelled = true;
    };
  }, []);

  /*
   * ---------------------------------------------------------
   * DRAW / UPDATE IMPACT VISUALISATION
   * ---------------------------------------------------------
   */

  useEffect(() => {
    if (!mapReady || !mapRef.current || !window.google?.maps) {
      return;
    }

    let cancelled = false;

    async function renderImpactLayer() {
      const map = mapRef.current;

      /*
       * Remove previous Google Maps objects.
       */
      objectsRef.current.forEach((object) => {
        if (object?.setMap) {
          object.setMap(null);
        } else if ("map" in object) {
          object.map = null;
        }
      });

      objectsRef.current = [];

      const { AdvancedMarkerElement } =
        await window.google.maps.importLibrary("marker");

      const { InfoWindow } =
        await window.google.maps.importLibrary("maps");

      if (cancelled) {
        return;
      }

      /*
       * -----------------------------------------------------
       * MAP POSITION
       * -----------------------------------------------------
       */

      map.setCenter(impact);

      map.setZoom(7);

      /*
       * -----------------------------------------------------
       * ENTRY → IMPACT TRAJECTORY
       * -----------------------------------------------------
       */

      const trajectoryLine =
        new window.google.maps.Polyline({
          path: [
            entry,
            impact,
          ],

          geodesic: true,

          strokeOpacity: 0.9,

          strokeWeight: 4,

          clickable: false,
        });

      trajectoryLine.setMap(map);

      objectsRef.current.push(
        trajectoryLine
      );

      /*
       * -----------------------------------------------------
       * IMPACT MARKER
       * -----------------------------------------------------
       */

      const impactMarker =
        new AdvancedMarkerElement({
          map,

          position: impact,

          title: "Meteor Madness modelled impact",
        });

      impactMarker.content =
        createImpactMarkerContent();

      objectsRef.current.push(
        impactMarker
      );

      /*
       * -----------------------------------------------------
       * ENTRY MARKER
       * -----------------------------------------------------
       */

      if (
        Number.isFinite(entry.lat) &&
        Number.isFinite(entry.lng) &&
        (
          Math.abs(entry.lat - impact.lat) > 0.001 ||
          Math.abs(entry.lng - impact.lng) > 0.001
        )
      ) {
        const entryMarker =
          new AdvancedMarkerElement({
            map,

            position: entry,

            title: "Atmospheric entry point",
          });

        entryMarker.content =
          createEntryMarkerContent();

        objectsRef.current.push(
          entryMarker
        );
      }

      /*
       * -----------------------------------------------------
       * IMPACT INFORMATION WINDOW
       * -----------------------------------------------------
       */

      const infoWindow =
        new InfoWindow({
          content: `
            <div style="
              min-width:220px;
              padding:4px;
              font-family:Arial,sans-serif;
            ">
              <strong style="
                font-size:16px;
              ">
                ☄️ Meteor Madness Impact
              </strong>

              <div style="
                margin-top:8px;
                line-height:1.5;
              ">
                <div>
                  <strong>Latitude:</strong>
                  ${impact.lat.toFixed(4)}°
                </div>

                <div>
                  <strong>Longitude:</strong>
                  ${impact.lng.toFixed(4)}°
                </div>

                ${
                  environmentLabel
                    ? `
                      <div>
                        <strong>Location:</strong>
                        ${environmentLabel}
                      </div>
                    `
                    : ""
                }

                ${
                  environment?.surface
                    ? `
                      <div>
                        <strong>Environment:</strong>
                        ${environment.surface}
                      </div>
                    `
                    : ""
                }

                ${
                  impactBranch?.branch
                    ? `
                      <div>
                        <strong>Physics branch:</strong>
                        ${impactBranch.branch}
                      </div>
                    `
                    : ""
                }

                ${
                  selectedAsteroid?.name
                    ? `
                      <div>
                        <strong>Asteroid:</strong>
                        ${selectedAsteroid.name}
                      </div>
                    `
                    : ""
                }
              </div>
            </div>
          `,
        });

      impactMarker.addListener(
        "click",
        () => {
          infoWindow.open({
            map,
            anchor: impactMarker,
          });
        }
      );

      /*
       * -----------------------------------------------------
       * CONSEQUENCE ZONES
       * -----------------------------------------------------
       */

      const zones = [
        {
          radius: radii.thermal,
          name: "Thermal radiation",
          className: "thermal",
          opacity: 0.18,
        },

        {
          radius: radii.blast,
          name: "Blast zone",
          className: "blast",
          opacity: 0.16,
        },

        {
          radius: radii.seismic,
          name: "Seismic zone",
          className: "seismic",
          opacity: 0.12,
        },
      ];

      zones.forEach((zone) => {
        if (!zone.radius || zone.radius <= 0) {
          return;
        }

        const circle =
          new window.google.maps.Circle({
            map,

            center: impact,

            radius: zone.radius,

            strokeOpacity: 0.75,

            strokeWeight: 2,

            fillOpacity: zone.opacity,

            clickable: false,
          });

        objectsRef.current.push(
          circle
        );
      });

      /*
       * -----------------------------------------------------
       * IMPACT LABEL
       * -----------------------------------------------------
       */

      const labelMarker =
        new AdvancedMarkerElement({
          map,

          position: {
            lat: impact.lat + 0.15,
            lng: impact.lng,
          },

          title: "Impact location",
        });

      labelMarker.content =
        createLabelContent(
          "MODELLED IMPACT",
          environmentLabel ||
            `${impact.lat.toFixed(3)}°, ${impact.lng.toFixed(3)}°`
        );

      objectsRef.current.push(
        labelMarker
      );
    }

    renderImpactLayer();

    return () => {
      cancelled = true;
    };
  }, [
    mapReady,
    impact,
    entry,
    environment,
    environmentLabel,
    impactBranch,
    consequences,
    radii,
    selectedAsteroid,
  ]);

  /*
   * ---------------------------------------------------------
   * MAP TYPE
   * ---------------------------------------------------------
   */

  useEffect(() => {
    if (!mapRef.current) {
      return;
    }

    mapRef.current.setMapTypeId(
      satelliteMode
        ? "hybrid"
        : "roadmap"
    );
  }, [satelliteMode]);

  /*
   * ---------------------------------------------------------
   * FIT THE IMPACT CORRIDOR
   * ---------------------------------------------------------
   */

  function fitImpactView() {
    if (
      !mapRef.current ||
      !window.google?.maps
    ) {
      return;
    }

    const bounds =
      new window.google.maps.LatLngBounds();

    bounds.extend(entry);
    bounds.extend(impact);

    mapRef.current.fitBounds(
      bounds,
      100
    );
  }

  if (!GOOGLE_MAPS_API_KEY) {
    return (
      <section className="panel google-impact-panel">
        <div className="panel-header">
          <div>
            <p className="section-label">
              GOOGLE MAPS
            </p>

            <h2>
              Geographic Impact Intelligence
            </h2>
          </div>

          <span className="badge">
            API KEY REQUIRED
          </span>
        </div>

        <div className="google-map-error">
          <strong>
            Google Maps is not configured.
          </strong>

          <p>
            Add
            {" "}
            <code>
              VITE_GOOGLE_MAPS_API_KEY
            </code>
            {" "}
            to the frontend environment.
          </p>
        </div>
      </section>
    );
  }

  return (
    <section className="panel google-impact-panel">
      <div className="panel-header">
        <div>
          <p className="section-label">
            GOOGLE MAPS / GEOSPATIAL INTELLIGENCE
          </p>

          <h2>
            Annotated Impact Map
          </h2>

          <p className="scenario-note">
            Geographic context layered onto the
            Meteor Madness physics model.
          </p>
        </div>

        <span className="badge">
          {mapError
            ? "MAP ERROR"
            : mapReady
              ? "LIVE MAP"
              : "LOADING MAP"}
        </span>
      </div>

      <div className="google-map-toolbar">
        <button
          type="button"
          onClick={() =>
            setSatelliteMode(false)
          }
          className={
            !satelliteMode
              ? "active"
              : ""
          }
        >
          🗺️ Map
        </button>

        <button
          type="button"
          onClick={() =>
            setSatelliteMode(true)
          }
          className={
            satelliteMode
              ? "active"
              : ""
          }
        >
          🛰️ Satellite
        </button>

        <button
          type="button"
          onClick={fitImpactView}
        >
          🎯 Impact corridor
        </button>
      </div>

      {mapError ? (
        <div className="google-map-error">
          <strong>
            Google Maps could not load.
          </strong>

          <p>
            {mapError}
          </p>
        </div>
      ) : (
        <div
          ref={mapContainerRef}
          className="google-impact-map"
        />
      )}

      <div className="google-map-telemetry">
        <div>
          <span>IMPACT</span>

          <strong>
            {impact.lat.toFixed(4)}°,
            {" "}
            {impact.lng.toFixed(4)}°
          </strong>
        </div>

        <div>
          <span>ENVIRONMENT</span>

          <strong>
            {environment?.surface ||
              "Unknown"}
          </strong>
        </div>

        <div>
          <span>PHYSICS</span>

          <strong>
            {impactBranch?.branch ||
              "Unknown"}
          </strong>
        </div>

        {environmentLabel && (
          <div>
            <span>LOCATION</span>

            <strong>
              {environmentLabel}
            </strong>
          </div>
        )}
      </div>
    </section>
  );
}
