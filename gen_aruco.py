"""Generate printable ArUco markers 1 and 2 using DICT_4X4_50.

Install: python -m pip install opencv-contrib-python
Run:     python gen_aruco.py
Output:  aruco_markers/ next to this script (or --output PATH).
"""

import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=int, default=800,
                        help="Marker side length in pixels, excluding white margin")
    parser.add_argument("--margin", type=int, default=100,
                        help="White margin on each side in pixels")
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).resolve().parent / "aruco_markers")
    args = parser.parse_args()
    if args.size < 60 or args.margin < 1:
        parser.error("--size must be at least 60 and --margin at least 1")

    try:
        import cv2
    except ImportError:
        parser.exit(1, "Install first: python -m pip install opencv-contrib-python\n")
    if not hasattr(cv2, "aruco"):
        parser.exit(1, "This OpenCV installation has no aruco module. "
                    "Use an environment with opencv-contrib-python.\n")

    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    args.output.mkdir(parents=True, exist_ok=True)
    tiles = []
    for marker_id in (1, 2):
        marker = cv2.aruco.generateImageMarker(dictionary, marker_id, args.size)
        printable = cv2.copyMakeBorder(
            marker, args.margin, args.margin, args.margin, args.margin,
            cv2.BORDER_CONSTANT, value=255,
        )
        path = args.output / f"aruco_DICT_4X4_50_id_{marker_id}.png"
        if not cv2.imwrite(str(path), printable):
            raise OSError(f"Could not write {path}")
        print(f"Saved ID {marker_id}: {path.resolve()}")
        tiles.append(printable)

    # Each marker retains its own white margin for reliable detection.
    combined = cv2.hconcat(tiles)
    combined_path = args.output / "aruco_DICT_4X4_50_ids_1_2.png"
    if not cv2.imwrite(str(combined_path), combined):
        raise OSError(f"Could not write {combined_path}")
    print(f"Saved combined IDs 1 and 2: {combined_path.resolve()}")


if __name__ == "__main__":
    main()
