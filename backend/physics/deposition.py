from __future__ import annotations


def energy_deposited_between_samples(
    energy_rate_start_W: float,
    energy_rate_end_W: float,
    timestep_s: float,
) -> float:
    """Estimate deposited energy using trapezoidal integration."""

    if energy_rate_start_W < 0:
        raise ValueError("energy_rate_start_W cannot be negative")

    if energy_rate_end_W < 0:
        raise ValueError("energy_rate_end_W cannot be negative")

    if timestep_s < 0:
        raise ValueError("timestep_s cannot be negative")

    return 0.5 * (
        energy_rate_start_W + energy_rate_end_W
    ) * timestep_s


def energy_deposition_per_altitude(
    energy_deposited_J: float,
    altitude_change_m: float,
) -> float:
    """Return deposited energy per metre of altitude travelled."""

    if energy_deposited_J < 0:
        raise ValueError("energy_deposited_J cannot be negative")

    if altitude_change_m <= 0:
        raise ValueError("altitude_change_m must be greater than zero")

    return energy_deposited_J / altitude_change_m

def build_energy_deposition_profile(samples):
    """Build atmospheric energy deposition between trajectory samples."""

    profile = []

    for previous, current in zip(samples, samples[1:]):
        dt = current.time_s - previous.time_s

        if dt <= 0:
            continue

        altitude_change_m = (
            previous.altitude_m - current.altitude_m
        )

        if altitude_change_m <= 0:
            continue

        deposited_energy_J = energy_deposited_between_samples(
            energy_rate_start_W=previous.drag_power_W,
            energy_rate_end_W=current.drag_power_W,
            timestep_s=dt,
        )

        deposition_per_meter_J_m = energy_deposition_per_altitude(
            energy_deposited_J=deposited_energy_J,
            altitude_change_m=altitude_change_m,
        )

        profile.append(
            {
                "altitude_m": (
                    previous.altitude_m + current.altitude_m
                ) / 2.0,
                "energy_deposited_J": deposited_energy_J,
                "energy_deposition_per_meter_J_m": (
                    deposition_per_meter_J_m
                ),
            }
        )

    return tuple(profile)

def bin_energy_deposition(
    profile,
    bin_size_m: float = 1000.0,
):
    """Group energy deposition into altitude bins."""

    if bin_size_m <= 0:
        raise ValueError("bin_size_m must be greater than zero")

    bins = {}

    for sample in profile:
        altitude_m = sample["altitude_m"]
        bin_index = int(altitude_m // bin_size_m)

        bins.setdefault(bin_index, 0.0)
        bins[bin_index] += sample["energy_deposited_J"]

    return tuple(
        {
            "altitude_min_m": index * bin_size_m,
            "altitude_max_m": (index + 1) * bin_size_m,
            "energy_deposited_J": energy,
        }
        for index, energy in sorted(
            bins.items(),
            reverse=True,
        )
    )

def total_deposited_energy(profile) -> float:
    """Return total atmospheric energy deposited by the trajectory."""

    return sum(
        sample["energy_deposited_J"]
        for sample in profile
    )
