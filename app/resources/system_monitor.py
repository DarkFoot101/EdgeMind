import psutil


def get_system_resources() -> dict[str, float]:
    """Return a non-blocking snapshot of available system resources."""

    return {
        "cpu_percent": psutil.cpu_percent(interval=None),
        "ram_available_gb":
            round(
                psutil.virtual_memory().available /
                (1024**3), 2
            )
    }
