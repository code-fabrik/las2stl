import pyvista as pv
import laspy as lp
import numpy as np
import trimesh

SAMPLE_RATE = 0.05
SCALEXY = 0.1
SCALEZ = 0.1
BASE_THICKNESS = 50.0
BASE_HEIGHT = 800
COMMON_BASE = False

filename = input("Enter the filename (without extension) of a *.las file in the 'las' folder: ")

print("Ground extraction...")
# Extract lidar features marked as ground
cloud = lp.read('./las/' + filename + '.las')
cloud.points = cloud.points[cloud.classification == 2]

points = np.vstack((cloud.x, cloud.y, cloud.z)).transpose()

print("Point cloud compression...")
# Discard 90% of the points
points = points[::10]

print("Surface reconstruction...")
# Generate a surface mesh from the point cloud
mesh = pv.wrap(points).delaunay_2d(alpha=0.0, progress_bar=True)
mesh = mesh.compute_normals(progress_bar=True)

print("Simplification...")
# Decimate polygons
compression_factor = 1 - SAMPLE_RATE
mesh = mesh.decimate(compression_factor, progress_bar=True)

print("Re-save...")
mesh.save('./stl/' + filename + '.stl')

print("Translation...")
# Move the entire mesh to (0,0,0)
tmesh = trimesh.load('./stl/' + filename + '.stl')
bounding_box = tmesh.bounds

# Z translation is base height for common ground and minheight for non-common ground
if COMMON_BASE:
    z_translation = -BASE_HEIGHT
else:
    z_translation = -bounding_box[0][2]

translation_vector = [-bounding_box[0][0], -bounding_box[0][1], z_translation]
tmesh.apply_translation(translation_vector)
tmesh.export('./stl/' + filename + '.stl')

print("Extrusion...")
# Extrude the surface mesh downwards to create a volume
mesh = pv.read("./stl/" + filename + ".stl")
size = bounding_box[1] - bounding_box[0]
xcenter = 0.5 * size[0]
ycenter = 0.5 * size[1]
plane = pv.Plane(
    center=(xcenter, ycenter, -BASE_THICKNESS * (1 - SCALEZ)),
    direction=(0, 0, -1),
    i_size=size[0],
    j_size=size[1],
)
mesh = mesh.extrude_trim((0, 0, -1.0), plane, progress_bar=True)

print("Scale...")
# Scale the mesh according to the settings
mesh = mesh.scale([SCALEXY, SCALEXY, SCALEZ], inplace=False)

print("Saving...")
mesh.save('./stl/' + filename + '.stl')

if not COMMON_BASE:
    spacer = (bounding_box[0][2] - BASE_HEIGHT) * SCALEZ
    print("This tile needs a " + str(spacer) + "mm spacer")

print("Done.")
