import pyvista as pv
import laspy as lp
import numpy as np

GROUND_ONLY = False
SAMPLE_RATE = 0.05
SCALEXY = 0.1
SCALEZ = 0.1
BASE_THICKNESS = 50.0
BASE_HEIGHT = 800
COMMON_BASE = False

filename = input("Enter the filename (without extension) of a *.las file in the 'las' folder: ")

print("Load...")
# Extract lidar features marked as ground
cloud = lp.read('./las/' + filename + '.las')

if GROUND_ONLY:
    cloud.points = cloud.points[cloud.classification == 2]

print("Point cloud sampling...")
# Keep SAMPLE_RATE of the points. Triangulating the full cloud and decimating
# the mesh afterwards needs more memory than most machines have.
rng = np.random.default_rng(0)
cloud.points = cloud.points[rng.random(len(cloud.points)) < SAMPLE_RATE]

points = np.vstack((cloud.x, cloud.y, cloud.z)).transpose()

print("Translation...")
# Move the cloud to (0,0,0) before meshing. STL stores 32 bit floats, which
# can't resolve real world coordinates (~2'600'000m) better than 0.25m.
lowest = points.min(axis=0)

# Z translation is base height for common ground and minheight for non-common ground
if COMMON_BASE:
    z_translation = -BASE_HEIGHT
else:
    z_translation = -lowest[2]

points += [-lowest[0], -lowest[1], z_translation]

print("Surface reconstruction...")
# Generate a surface mesh from the point cloud
surface = pv.wrap(points).delaunay_2d(alpha=0.0, progress_bar=True)
vertices = surface.points
top = surface.faces.reshape(-1, 4)[:, 1:]

# Orient all triangles counterclockwise when seen from above
a, b, c = vertices[top].transpose(1, 0, 2)
clockwise = (b - a)[:, 0] * (c - a)[:, 1] - (b - a)[:, 1] * (c - a)[:, 0] < 0
top = np.where(clockwise[:, None], top[:, ::-1], top)

print("Extrusion...")
# Close the surface into a watertight volume: walls from its outline straight
# down to the base, and a flat floor fanned out from the center of the base.
# The outline consists of the edges that belong to a single triangle.
edges = np.concatenate((top[:, [0, 1]], top[:, [1, 2]], top[:, [2, 0]]))
edge_ids = np.sort(edges, axis=1) @ [len(vertices), 1]
_, inverse, counts = np.unique(edge_ids, return_inverse=True, return_counts=True)
start, end = edges[counts[inverse.ravel()] == 1].transpose()

n = len(vertices)
base = vertices.copy()
base[:, 2] = -BASE_THICKNESS * (1 - SCALEZ)
vertices = np.vstack((vertices, base, base.mean(axis=0)))
faces = np.vstack((
    top,
    np.column_stack((start, start + n, end + n)),
    np.column_stack((start, end + n, end)),
    np.column_stack((np.full_like(start, 2 * n), end + n, start + n)),
))

print("Scale...")
# Scale the mesh according to the settings
vertices *= [SCALEXY, SCALEXY, SCALEZ]

print("Saving...")
faces = np.hstack((np.full((len(faces), 1), 3), faces))
pv.PolyData(vertices, faces.ravel()).save('./stl/' + filename + '.stl')

if not COMMON_BASE:
    spacer = (lowest[2] - BASE_HEIGHT) * SCALEZ
    print("This tile needs a " + str(spacer) + "mm spacer")

print("Done.")
