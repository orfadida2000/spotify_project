import os
import platform


def _file_contains(path: str, needle: str) -> bool:
    try:
        with open(path, errors="ignore") as f:
            return needle in f.read().lower()
    except Exception:
        return False


def detect_host_verbose() -> str:
    home = os.path.expanduser("~")
    platform_specs = {key: value.lower() for key, value in platform.uname()._asdict().items()}
    os_specs = {}
    os_specs["WSL_DISTRO_NAME"] = os.environ.get("WSL_DISTRO_NAME")
    os_specs["WSL_INTEROP"] = os.environ.get("WSL_INTEROP")
    found = None

    print(f"HOME: {home}")
    print("Platform specs:")
    for key, value in platform_specs.items():
        print(f"\t{key}: {value}")
    print("OS specs:")
    for key, value in os_specs.items():
        print(f"\t{key}: {value}")

    if platform_specs["system"] == "windows":
        print("Detected Windows environment")
        found = "Windows"
    elif platform_specs["system"] == "linux":
        print("Detected Linux environment - checking for WSL...")

        # WSL: multiple robust signals
        if "microsoft" in platform_specs["release"]:
            print("Detected WSL environment based on platform release")
            found = "WSL"
        if os_specs["WSL_DISTRO_NAME"]:
            print("Detected WSL environment based on WSL_DISTRO_NAME environment variable")
            found = "WSL"
        if os_specs["WSL_INTEROP"]:
            print("Detected WSL environment based on WSL_INTEROP environment variable")
            found = "WSL"

        if _file_contains(path="/proc/sys/kernel/osrelease", needle="microsoft"):
            print("/proc/sys/kernel/osrelease contains 'microsoft' -> Detected WSL environment")
            found = "WSL"
        else:
            print("/proc/sys/kernel/osrelease does not contain 'microsoft'")

        if _file_contains(path="/proc/version", needle="microsoft"):
            print("/proc/version contains 'microsoft' -> Detected WSL environment")
            found = "WSL"
        else:
            print("/proc/version does not contain 'microsoft'")

        if not found:
            print("No WSL indicators found; assuming standard Linux environment")
            found = "Linux"
    elif platform_specs["system"] in  ["darwin", "ios", "macos", "ipados"]:
        print("Detected Darwin (macOS) environment - checking for a-Shell...")

        # a-Shell (iOS sandbox): HOME under /private/var/mobile/…
        if home.startswith("/private/var/mobile/Containers"):
            print("HOME indicates a-Shell environment")
            found = "a-Shell"
        else:
            print("HOME does not indicate a-Shell environment")

        if os.environ.get("APPNAME", "").lower() == "a-shell":
            print("APPNAME environment variable indicates a-Shell environment")
            found = "a-Shell"
        else:
            print("APPNAME environment variable does not indicate a-Shell environment")

        if not found:
            print("No a-Shell indicators found; assuming standard macOS environment")
            found = "macOS"

    if found:
        print(f"Detected environment: {found}")
    else:
        print("Environment not detected - marked as Other")
        found = "Other"

    return found


def detect_host() -> str:
    home = os.path.expanduser("~")
    platform_specs = {key: value.lower() for key, value in platform.uname()._asdict().items()}
    os_specs = {}
    os_specs["WSL_DISTRO_NAME"] = os.environ.get("WSL_DISTRO_NAME")
    os_specs["WSL_INTEROP"] = os.environ.get("WSL_INTEROP")

    if platform_specs["system"] == "windows":
        return "Windows"
    elif platform_specs["system"] == "linux":
        # WSL: multiple robust signals
        if (
            "microsoft" in platform_specs["release"]
            or os_specs["WSL_DISTRO_NAME"]
            or os_specs["WSL_INTEROP"]
            or _file_contains(path="/proc/sys/kernel/osrelease", needle="microsoft")
            or _file_contains(path="/proc/version", needle="microsoft")
        ):
            return "WSL"
        return "Linux"
    elif platform_specs["system"] in  ["darwin", "ios", "macos", "ipados"]:
        # a-Shell (iOS sandbox): HOME under /private/var/mobile/…
        if (
            home.startswith("/private/var/mobile/Containers")
            or os.environ.get("APPNAME", "").lower() == "a-shell"
        ):
            return "a-Shell"
        return "macOS"

    return "Other"


def main():
    print(detect_host())


if __name__ == "__main__":
    main()
