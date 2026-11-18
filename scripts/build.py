"""Stage the public website files for the CodePipeline artifact."""

from pathlib import Path
from shutil import copyfile

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_FILES = ("index.html", "styles.css")


def main():
    destination = ROOT / "dist"
    destination.mkdir(exist_ok=True)
    for filename in PUBLIC_FILES:
        copyfile(ROOT / "site" / filename, destination / filename)
        print(f"Packaged {filename}")


if __name__ == "__main__":
    main()
