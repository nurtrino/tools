"""Puck launcher: trajectory and error-budget simulation (preliminary design).

Models a spin-stabilised regulation puck launched flat (disc plane containing the
launch velocity) from a seat `d` metres horizontally from centre ice and `h` metres
above it. Answers three questions:

  1. What launch speed / angle does each seat need?
  2. How sensitive is the landing point to each error source?
  3. Given an error budget, what fraction of shots first-impact within 1 m?

Coordinates: x downrange toward centre ice, y lateral (left), z up.
The aero coefficients are estimates and must be replaced by calibration shots.

Run:  python3 trajectory_sim.py
"""
import numpy as np

G = 9.81
MASS = 0.165          # kg   (regulation 156-170 g; weigh the actual puck)
DIA = 0.0762          # m
THICK = 0.0254        # m
S_FACE = np.pi * DIA**2 / 4
S_EDGE = DIA * THICK
I_SPIN = 0.5 * MASS * (DIA / 2) ** 2

# Aerodynamic model (crossflow / Polhamus form), all need calibration:
CD_EDGE = 0.65        # edge-on drag coeff on S_EDGE
K_LIFT = 1.8          # normal-force slope on S_FACE (low aspect ratio disc)
CD_FACE = 1.1         # face-on drag coeff on S_FACE
CP_FRAC = 0.15        # centre of pressure ahead of centre, fraction of DIA
RHO = 1.20            # kg/m^3

# Arena constraints (placeholders until measured)
HALF_WIDTH = 13.0     # m, centre ice to side boards
GLASS_TOP = 3.3       # m above ice, incl. margin
SCOREBOARD_H = 9.0    # m, underside of scoreboard above ice
SCOREBOARD_R = 8.0    # m, half-width of scoreboard


def simulate(v0, pitch, yaw, h, *, rho=RHO, cd_scale=1.0, wind=(0.0, 0.0),
             disc_pitch_err=0.0, disc_roll_err=0.0, mass=MASS, spin_sign=1.0,
             dt=0.004, t_max=6.0, track=False):
    """Vectorised RK4. All inputs broadcast to shape (N,). Angles in radians.

    Returns landing (x, y), flight time, impact speed, descent angle [rad];
    with track=True also returns the path of sample 0.
    """
    args = np.broadcast_arrays(v0, pitch, yaw, h, rho, cd_scale, wind[0], wind[1],
                               disc_pitch_err, disc_roll_err, mass)
    v0, pitch, yaw, h, rho, cd_scale, wx, wy, dpe, dre, mass = [
        np.atleast_1d(a).astype(float) for a in args]
    n_s = v0.size
    pos = np.stack([np.zeros(n_s), np.zeros(n_s), h], axis=1)
    cp, sp, cy, sy = np.cos(pitch), np.sin(pitch), np.cos(yaw), np.sin(yaw)
    vel = np.stack([v0 * cp * cy, v0 * cp * sy, v0 * sp], axis=1)
    # Disc normal: perpendicular to velocity in the vertical plane, plus tilt errors.
    dp = pitch + dpe
    nrm = np.stack([-np.sin(dp) * cy, -np.sin(dp) * sy, np.cos(dp)], axis=1)
    lat = np.stack([-sy, cy, np.zeros(n_s)], axis=1)
    nrm = nrm + np.tan(dre)[:, None] * lat
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    wind_v = np.stack([wx, wy, np.zeros(n_s)], axis=1)
    # Wheel-on-rail launch: puck rolls along the rail, so spin = v / r.
    l_spin = (I_SPIN * mass / MASS) * (v0 / (DIA / 2)) * spin_sign
    q = (0.5 * rho * cd_scale)[:, None]
    m = mass[:, None]

    def deriv(vel, nrm):
        vr = vel - wind_v
        vn = np.sum(vr * nrm, axis=1, keepdims=True)
        vt_vec = vr - vn * nrm
        vt = np.linalg.norm(vt_vec, axis=1, keepdims=True)
        f_n = -q * S_FACE * (K_LIFT * vt * vn + CD_FACE * np.abs(vn) * vn) * nrm
        f_t = -q * S_EDGE * CD_EDGE * vt * vt_vec
        acc = (f_n + f_t) / m
        acc[:, 2] -= G
        # Pitching moment from the forward centre of pressure -> gyroscopic precession.
        speed = np.linalg.norm(vr, axis=1, keepdims=True) + 1e-9
        r_cp = CP_FRAC * DIA * (vt / speed) * vt_vec / (vt + 1e-9)
        dn = np.cross(r_cp, f_n) / l_spin[:, None]
        return acc, dn

    land = np.full((n_s, 2), np.nan)
    t_land = np.full(n_s, np.nan)
    v_imp = np.full(n_s, np.nan)
    gamma = np.full(n_s, np.nan)
    alive = np.ones(n_s, bool)
    path = [pos[0].copy()] if track else None
    t = 0.0
    while alive.any() and t < t_max:
        a1, n1 = deriv(vel, nrm)
        a2, n2 = deriv(vel + 0.5 * dt * a1, nrm + 0.5 * dt * n1)
        a3, n3 = deriv(vel + 0.5 * dt * a2, nrm + 0.5 * dt * n2)
        a4, n4 = deriv(vel + dt * a3, nrm + dt * n3)
        new_pos = pos + dt * vel + dt**2 / 6 * (a1 + a2 + a3)
        new_vel = vel + dt / 6 * (a1 + 2 * a2 + 2 * a3 + a4)
        nrm = nrm + dt / 6 * (n1 + 2 * n2 + 2 * n3 + n4)
        nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
        hit = alive & (new_pos[:, 2] <= 0.0)
        if hit.any():
            f = (pos[hit, 2] / (pos[hit, 2] - new_pos[hit, 2]))[:, None]
            p = pos[hit] + f * (new_pos[hit] - pos[hit])
            vv = vel[hit] + f * (new_vel[hit] - vel[hit])
            land[hit] = p[:, :2]
            t_land[hit] = t + f[:, 0] * dt
            v_imp[hit] = np.linalg.norm(vv, axis=1)
            gamma[hit] = np.arctan2(-vv[:, 2], np.hypot(vv[:, 0], vv[:, 1]))
            alive &= ~hit
        pos, vel = new_pos, new_vel
        t += dt
        if track and alive[0]:
            path.append(pos[0].copy())
    out = (land[:, 0], land[:, 1], t_land, v_imp, gamma)
    return out + (np.array(path),) if track else out


def solve_speed(pitch, d, h, **kw):
    """Launch speed that lands at downrange distance d, for each pitch (bisection)."""
    pitch = np.atleast_1d(pitch).astype(float)
    lo, hi = np.full(pitch.shape, 3.0), np.full(pitch.shape, 45.0)
    for _ in range(26):
        mid = 0.5 * (lo + hi)
        x = simulate(mid, pitch, 0.0, h, **kw)[0]
        short = np.isnan(x) | (x < d)
        lo, hi = np.where(short, mid, lo), np.where(short, hi, mid)
    return 0.5 * (lo + hi)


def clearances(v0, pitch, d, h):
    """(height over the glass, max height under the scoreboard footprint)."""
    path = simulate(v0, pitch, 0.0, h, track=True)[-1]
    z_glass = np.interp(d - HALF_WIDTH, path[:, 0], path[:, 2])
    under = path[:, 0] >= d - SCOREBOARD_R
    return z_glass, path[under, 2].max(), path[:, 2].max()


def seat(row):
    """Rough side-centre seat geometry: (horizontal distance, launcher height)."""
    if row <= 22:                       # lower bowl, ~22 deg rake
        return HALF_WIDTH + 1.5 + 0.85 * row, 0.6 + 0.34 * row + 1.2
    d22, h22 = seat(22)
    n = row - 22                        # upper bowl, ~34 deg rake, 3 m setback
    return d22 + 3.0 + 0.80 * n, h22 + 3.0 + 0.54 * n


# 1-sigma error budget. "shot" terms vary shot to shot; "setup" terms are one-off
# biases that a single shot cannot average out (so they matter just as much).
BUDGET = dict(
    speed_frac=0.005,        # shot : exit-speed repeatability (closed-loop flywheel)
    pitch=np.radians(0.10),  # setup: inclinometer + mount flex
    yaw=np.radians(0.15),    # setup: sight alignment to the centre dot
    disc_tilt=np.radians(0.5),  # shot: puck attitude leaving the rail (pitch & roll)
    range_m=0.15,            # setup: measured distance to centre ice
    height_m=0.05,           # setup: measured height above ice
    cd_frac=0.03,            # setup: aero model residual after calibration
    rho_frac=0.01,           # setup: air-density residual (temperature/pressure)
    wind=0.20,               # shot : arena HVAC drafts, m/s each axis
    mass=0.0005,             # setup: puck mass after weighing, kg
)


def monte_carlo(v0, pitch, d, h, budget=BUDGET, n=4000, seed=1):
    r = np.random.default_rng(seed)
    g = lambda s: r.normal(0.0, s, n)
    # Range/height mis-measurement = shooting the nominal solution from a seat that
    # is really somewhere slightly different.
    x, y, *_ = simulate(
        v0 * (1 + g(budget["speed_frac"])), pitch + g(budget["pitch"]), g(budget["yaw"]),
        h + g(budget["height_m"]), rho=RHO * (1 + g(budget["rho_frac"])),
        cd_scale=1 + g(budget["cd_frac"]), wind=(g(budget["wind"]), g(budget["wind"])),
        disc_pitch_err=g(budget["disc_tilt"]), disc_roll_err=g(budget["disc_tilt"]),
        mass=MASS + g(budget["mass"]))
    x0, y0, *_ = simulate(v0, pitch, 0.0, h)
    ex = x - x0 + g(budget["range_m"])
    ey = y - y0
    return ex, ey


def sensitivities(v0, pitch, d, h):
    """Landing shift per unit of each error source: {name: (dx, dy, unit)}."""
    x0, y0, *_ = simulate(v0, pitch, 0.0, h)
    def delta(**kw):
        a = dict(v0=v0, pitch=pitch, yaw=0.0, h=h)
        a.update(kw)
        x, y, *_ = simulate(a.pop("v0"), a.pop("pitch"), a.pop("yaw"), a.pop("h"), **a)
        return float(x[0] - x0[0]), float(y[0] - y0[0])
    deg = np.radians(1.0)
    return {
        "speed +1%": delta(v0=v0 * 1.01),
        "pitch +1 deg": delta(pitch=pitch + deg),
        "yaw +1 deg": delta(yaw=deg),
        "disc nose-up +1 deg": delta(disc_pitch_err=deg),
        "disc roll +1 deg": delta(disc_roll_err=deg),
        "height +0.1 m": delta(h=h + 0.1),
        "drag/lift coeffs +10%": delta(cd_scale=1.10),
        "air density +4%": delta(rho=RHO * 1.04),
        "headwind 1 m/s": delta(wind=(-1.0, 0.0)),
        "crosswind 1 m/s": delta(wind=(0.0, 1.0)),
        "puck mass +5 g": delta(mass=MASS + 0.005),
    }


def best_pitch(d, h):
    """Minimum-launch-speed pitch that clears the glass and stays under the
    scoreboard. At minimum speed the landing point is first-order insensitive to
    pitch error, and the puck carries the least energy."""
    pitches = np.radians(np.arange(-10.0, 61.0, 1.0))
    v = solve_speed(pitches, d, h)
    for i in np.argsort(v):
        zg, zs, apex = clearances(v[i], pitches[i], d, h)
        if zg >= GLASS_TOP and zs <= SCOREBOARD_H:
            return pitches[i], v[i], zg, zs, apex
    return None


def report(rows=(5, 10, 15, 20, 30, 40)):
    print(f"{'row':>4}{'dist':>7}{'height':>7}{'pitch':>7}{'speed':>7}{'energy':>7}"
          f"{'wheel':>8}{'apex':>6}{'glass':>7}{'descent':>8}{'impact':>7}"
          f"{'drift':>7}{'sig_x':>7}{'sig_y':>7}{'P(<1m)':>8}{'P(<.5m)':>8}")
    print(f"{'':>4}{'m':>7}{'m':>7}{'deg':>7}{'m/s':>7}{'J':>7}{'rpm':>8}{'m':>6}"
          f"{'m':>7}{'deg':>8}{'m/s':>7}{'m':>7}{'m':>7}{'m':>7}{'':>8}{'':>8}")
    results = {}
    for row in rows:
        d, h = seat(row)
        sol = best_pitch(d, h)
        if sol is None:
            print(f"{row:>4}{d:7.1f}{h:7.1f}   no trajectory clears glass and scoreboard")
            continue
        pitch, v, zg, zs, apex = sol
        _, y_nom, tof, vimp, gam = simulate(v, pitch, 0.0, h)
        ex, ey = monte_carlo(v, pitch, d, h)
        miss = np.hypot(ex, ey)
        rpm = 2 * v / (np.pi * 0.100) * 60          # 100 mm wheel, puck rolls on rail
        print(f"{row:>4}{d:7.1f}{h:7.1f}{np.degrees(pitch):7.0f}{v:7.2f}"
              f"{0.5 * MASS * v * v:7.1f}{rpm:8.0f}{apex:6.1f}{zg:7.1f}"
              f"{np.degrees(gam[0]):8.0f}{vimp[0]:7.1f}{y_nom[0]:7.2f}{ex.std():7.2f}{ey.std():7.2f}"
              f"{(miss < 1).mean():8.1%}{(miss < 0.5).mean():8.1%}")
        results[row] = (d, h, pitch, v, ex, ey)
    return results


if __name__ == "__main__":
    print("== Seat sweep (side of rink, on the centre line) ==")
    res = report()

    row = 15
    d, h, pitch, v, ex, ey = res[row]
    print(f"\n== Sensitivities, row {row} (d={d:.1f} m, h={h:.1f} m, "
          f"{np.degrees(pitch):.0f} deg, {v:.2f} m/s) ==")
    for name, (dx, dy) in sensitivities(v, pitch, d, h).items():
        print(f"  {name:<24} downrange {dx:+6.2f} m   lateral {dy:+6.2f} m")

    print(f"\n== Speed repeatability vs hit rate, row {row} ==")
    for sf in (0.0025, 0.005, 0.01, 0.015, 0.02):
        b = dict(BUDGET, speed_frac=sf)
        ex, ey = monte_carlo(v, pitch, d, h, budget=b)
        miss = np.hypot(ex, ey)
        print(f"  speed sigma {sf:6.2%}:  sig_x {ex.std():.2f} m   "
              f"P(<1 m) {(miss < 1).mean():6.1%}")

    print(f"\n== Outdoor calibration, row {row}: effect of 1-sigma wind during calibration ==")
    for w in (0.2, 0.5, 1.0, 2.0):
        b = dict(BUDGET, wind=w)
        ex, ey = monte_carlo(v, pitch, d, h, budget=b)
        print(f"  wind sigma {w:.1f} m/s:  sig_x {ex.std():.2f} m  sig_y {ey.std():.2f} m")
