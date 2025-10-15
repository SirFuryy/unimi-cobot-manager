import numpy as np


points = []
for x in np.linspace(-0.05, 0.05, 10):
    for y in np.linspace(-0.03, 0.03, 8):
        for z in np.linspace(0.1, 0.25, 6):
            points.append([x, y, z])

points = np.array(points)



bbox_min = np.min(points, axis=0)
bbox_max = np.max(points, axis=0)
x0, y0, z0 = bbox_min[0], bbox_min[1], bbox_min[2]
x1, y1, z1 = bbox_max[0], bbox_max[1], bbox_max[2]

bbxpts = {
    "min": {"x": float(x0), "y": float(y0), "z": float(z0)},
    "max": {"x": float(x1), "y": float(y1), "z": float(z1)}
}

print(bbxpts["min"].items())
print(bbxpts["min"])
print(type(bbxpts["min"].items()))
print(type(bbxpts["min"].items()))

x_vals = [bbxpts["min"]["x"], bbxpts["max"]["x"]]
print(x_vals)
print(type(x_vals))


min_pt = {k: v for k, v in bbxpts["min"].items()}
max_pt = {k: v for k, v in bbxpts["max"].items()}

x_v = [min_pt["x"], max_pt["x"]]
print(x_v)
print(type(x_v))