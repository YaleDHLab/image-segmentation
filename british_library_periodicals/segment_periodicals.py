from skimage import filters, segmentation, io
from skimage.measure import label, regionprops
from skimage.color import label2rgb
from scipy import ndimage
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import sys, os

image_file = sys.argv[1]
file_extension = image_file.split(".")[-1]
plots_to_show = []


if file_extension in ["jpg", "jpeg"]:
  im = ndimage.imread(image_file)

elif file_extension in ["jp2"]:
  im = io.imread(image_file, plugin='freeimage')

else:
  print "your input file isn't jpg or jp2"
  sys.exit()

############################
# X-Y axis pixel dilations #
############################

# plot the amount of white ink across the columns & rows
row_vals = list([sum(r) for r in im  ])
col_vals = list([sum(c) for c in im.T])

if "col_sums" in plots_to_show:
  plt.plot(col_vals)
  plt.show()

if "row_sums" in plots_to_show:
  plt.plot(row_vals)
  plt.show()

#########################################
# Otsu method of boolean classification #
#########################################

val = filters.threshold_otsu(im)
mask = im < val

clean_border = segmentation.clear_border(mask)

plt.imshow(clean_border, cmap='gray')
plt.show()

#######################
# Label image regions #
#######################

labeled = label(clean_border)
image_label_overlay = label2rgb(labeled, image=im)

fig, ax = plt.subplots(ncols=1, nrows=1, figsize=(6, 6))
ax.imshow(image_label_overlay)
#plt.show()

#########################################
# Draw bounding box around each article #
#########################################

# create array in which to store cropped articles
cropped_images = []

# define amount of padding to add to cropped image
pad = 20

for region_index, region in enumerate(regionprops(labeled)):
  if region.area < 2000:
    continue

  # draw a rectangle around the segmented articles
  # bbox describes: min_row, min_col, max_row, max_col
  minr, minc, maxr, maxc = region.bbox
  
  # use those bounding box coordinates to crop the image
  cropped_images.append(im[minr-pad:maxr+pad, minc-pad:maxc+pad])
  
  print "region", region_index, "bounding box:", minr, minc, maxr, maxc

  rect = mpatches.Rectangle((minc, minr), maxc - minc, maxr - minr,
                              fill=False, edgecolor='red', linewidth=2)

  ax.add_patch(rect)

plt.show()

###############
# Crop images #
###############

out_dir = "segmented_articles/"
if not os.path.exists(out_dir):
  os.makedirs(out_dir)

# can crop using: cropped = image_array[x1:x2,y1:y2]

for c, cropped_image in enumerate(cropped_images):
  io.imsave( out_dir + str(c) + ".png", cropped_image)
