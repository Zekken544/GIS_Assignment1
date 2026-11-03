import argparse
import csv
from dataclasses import dataclass
from math import dist, isfinite
from pathlib import Path


@dataclass(frozen=True)
class Location:
    kind: str
    identifier: str
    name: str
    x: float
    y: float

    @property
    def xy(self):
        return self.x, self.y


def load(path):
    groups = {"school": [], "stop": []}
    seen = set()
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["kind", "id", "name", "x", "y"]:
            raise ValueError("Expected CSV columns kind,id,name,x,y")
        for row in reader:
            kind, identifier, name = (row[key] or "" for key in ("kind", "id", "name"))
            try:
                x, y = float(row["x"]), float(row["y"])
                if kind not in groups or not identifier.strip() or not name.strip():
                    raise ValueError
                if identifier in seen or not all(map(isfinite, (x, y))):
                    raise ValueError
            except (ValueError, TypeError) as error:
                raise ValueError(f"Invalid location on CSV line {reader.line_num}") from error
            groups[kind].append(Location(kind, identifier, name, x, y))
            seen.add(identifier)
    if not all(groups.values()):
        raise ValueError("Provide at least one school and one stop")
    return groups["school"], groups["stop"]


def nearest_stop(school, stops):
    distance, _, stop = min((dist(school.xy, stop.xy), stop.identifier, stop) for stop in stops)
    return stop, distance


def show(schools, stops):
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.title("School to bus stop - GIS prototype")
    width, height = 780, 500
    selection = tk.StringVar(value=schools[0].identifier)
    selector = ttk.Combobox(root, textvariable=selection,
                            values=[school.identifier for school in schools], state="readonly")
    ttk.Label(root, text="Select school ID").pack()
    selector.pack()
    canvas = tk.Canvas(root, width=width, height=height, background="white")
    canvas.pack()
    status = tk.StringVar()
    ttk.Label(root, textvariable=status, padding=8).pack()
    xs, ys = zip(*(point.xy for point in schools + stops))
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
    scales = [pixels / span for pixels, span in
              ((width - 160, xmax - xmin), (height - 100, ymax - ymin)) if span]
    scale = min(scales, default=1)

    def screen(point):
        return (width / 2 + (point.x - (xmin + xmax) / 2) * scale,
                height / 2 - (point.y - (ymin + ymax) / 2) * scale)

    def draw(event=None):
        canvas.delete("all")
        school = next(point for point in schools if point.identifier == selection.get())
        stop, distance = nearest_stop(school, stops)
        canvas.create_line(*screen(school), *screen(stop), fill="#cf4b24", width=3, dash=(5, 4))
        for point in schools + stops:
            x, y = screen(point)
            color = "#1e55a0" if point.kind == "school" else "#18724f"
            if point in (school, stop):
                canvas.create_oval(x-10, y-10, x+10, y+10, outline="#cf4b24", width=2)
            if point.kind == "school":
                canvas.create_rectangle(x-5, y-5, x+5, y+5, fill=color, outline="")
            else:
                canvas.create_oval(x-5, y-5, x+5, y+5, fill=color, outline="")
            canvas.create_text(x+8, y-12, text=f"{point.identifier} {point.name}", anchor="w")
        status.set(f"{school.name} → {stop.name} | Straight-line distance: {distance:.2f} m")

    selector.bind("<<ComboboxSelected>>", draw)
    draw()
    root.mainloop()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path(__file__).with_name("locations.csv"))
    parser.add_argument("--no-gui", action="store_true")
    args = parser.parse_args()
    try:
        schools, stops = load(args.input)
        for school in schools:
            stop, distance = nearest_stop(school, stops)
            print(f"{school.identifier} -> {stop.identifier}: {distance:.2f} m")
        if not args.no_gui:
            show(schools, stops)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
