from skimage import filters, segmentation, io
from skimage.measure import label
from skimage.color import label2rgb
from scipy import ndimage
import matplotlib.pyplot as plt
import sys

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
plt.show()

###############
# Crop images #
###############

# can crop using: cropped = image_array[x1:x2,y1:y2]
