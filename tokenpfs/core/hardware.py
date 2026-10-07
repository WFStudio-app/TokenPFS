"""Hardware power measurement + automatic token-rate tuning (/autt).

Measures: CPU cores, load average, free RAM, disk space, thermal zone.
Computes a 0..100 "power score" and recommends tokens/sec for the
selected model (heavier models need more headroom).
Pure stdlib — works on Termux and Linux.
"""

import os
import shutil


def _cpu_count():
    try:
        return os.cpu_count() or 1
    except Exception:
        return 1


def _load_avg():
    try:
        return os.getloadavg()[0]
    except (OSError, AttributeError):
        return 0.0


def _mem_info():
    """Return (total_mb, available_mb) from /proc/meminfo."""
    total = avail = 0.0
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    total = float(line.split()[1]) / 1024.0
                elif line.startswith("MemAvailable:"):
                    avail = float(line.split()[1]) / 1024.0
    except OSError:
        pass
    return total, avail


def _disk_free_gb(path=None):
    try:
        u = shutil.disk_usage(path or os.path.expanduser("~"))
        return u.free / (1024 ** 3)
    except OSError:
        return 0.0


def _thermal_c():
    """Best-effort SoC temperature in Celsius (Termux/RPi/x86)."""
    base = "/sys/class/thermal"
    try:
        for zone in sorted(os.listdir(base)):
            tp = os.path.join(base, zone, "temp")
            tz = os.path.join(base, zone, "type")
            if not os.path.exists(tp):
                continue
            ztype = ""
            try:
                with open(tz) as f:
                    ztype = f.read().strip().lower()
            except OSError:
                pass
            if any(k in ztype for k in ("soc", "cpu", "x86_pkg", "core")):
                with open(tp) as f:
                    return int(f.read().strip()) / 1000.0
    except OSError:
        pass
    return None


def measure():
    """Collect hardware snapshot."""
    cores = _cpu_count()
    total_mb, avail_mb = _mem_info()
    data = {
        "cores": cores,
        "load1": _load_avg(),
        "ram_total_mb": round(total_mb),
        "ram_avail_mb": round(avail_mb),
        "disk_free_gb": round(_disk_free_gb(), 1),
        "temp_c": _thermal_c(),
    }
    # ---- power score 0..100 ----
    cpu_score = min(cores / 8.0, 1.0) * 45                      # up to 45
    ram_score = min(avail_mb / 4096.0, 1.0) * 35 if avail_mb else 0.15 * 35
    load_penalty = max(0.0, min(data["load1"] / max(cores, 1), 1.0)) * 15
    temp_penalty = 0.0
    if data["temp_c"] is not None and data["temp_c"] > 70:
        temp_penalty = min((data["temp_c"] - 70) / 30.0, 1.0) * 10
    score = max(0.0, cpu_score + ram_score - load_penalty - temp_penalty)
    data["power_score"] = round(score, 1)
    return data


def recommend_tps(model_size_gb: float, hw: dict) -> float:
    """Tokens/sec recommendation: heavier model -> slower; stronger iron -> faster."""
    score = hw.get("power_score", 20)
    size = max(float(model_size_gb or 1.0), 0.3)
    base = 4.0 + score * 0.9          # weak phone ~8, desktop ~85
    tps = base / (size ** 0.55)       # heavy models scaled down
    avail = hw.get("ram_avail_mb", 0)
    if avail and avail < size * 1024 * 1.2:   # model barely fits in RAM
        tps *= 0.5
    return round(max(0.5, min(tps, 250.0)), 1)
