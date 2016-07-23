from __future__ import division
from skimage import io
from scipy import ndimage
import matplotlib.pyplot as plt
import numpy as np
import glob, os, codecs, sys

####################################
# JP2 File to XML Coordinate Array #
####################################

def retrieve_image_list(path_to_directory):
  """Read in a path to a directory and return an array of jp2
  files in that directory"""
  return list( glob.glob(path_to_directory + "/*.jp2") )


def jp2_to_array(jp2_file):
  """Read in a jp2 image file and return that a numpy array
  that represents the pixel values of that image"""
  return io.imread(jp2_file, plugin='freeimage') 


def get_image_height_width(numpy_array):
  """Read in a numpy array of a jp2 file and return a tuple
  that contains the height and width of the image in pixels /
  numpy values"""
  return numpy_array.shape


def remove_right_and_bottom_margins(jp2_image_dimensions, margins):
  """Read in an iterable with n_pixels in height, width of jp2 image
  and return an iterable with those same units minus the right and
  bottom margins"""
  adjusted_height = jp2_image_dimensions[0] - margins["bottom"]
  adjusted_width = jp2_image_dimensions[1] - margins["right"]

  return [adjusted_height, adjusted_width]


def jp2_file_to_height_width(jp2_file):
  """Read in a jp2 file and return a tuple that indicates
  that file's height and width"""
  jp2_numpy_array = jp2_to_array(jp2_file)
  return get_image_height_width(jp2_numpy_array)


def get_image_file_id(jp2_file):
  """Read in a jp2 file and return the unique integer id
  for the file"""
  filename = os.path.basename(jp2_file)
  file_root = filename.replace(".jp2","")
  return file_root


def get_xml_file_for_file_id(jp2_file_id):
  """Read in the unique integer that identifies a jp2 file
  and return the xml that corresponds to that image file"""
  return directory_with_images + "/" + jp2_file_id + ".articles.xml"


def read_xml_file(xml_file_path):
  """Read in the path to an xml file and return that 
  xml file content in string form"""
  with codecs.open(xml_file_path, "r", "utf-8") as f:
    return f.read()


def get_xml_articles(xml_content):
  """Read in a string containing XML content and return an array
  of the articles in that XML document"""
  articles = []
  
  for i in xml_content.split("<article")[1:]:
    article_start = ">".join(i.split(">")[1:])
    article_content = article_start.split("</article")[0]
    clean_article = article_content
    articles.append(clean_article)

  return articles


def get_article_clips(article):
  """Read in the xml content from an article and return an array of
  the clips in that article"""
  
  article_clips = []
  
  for i in article.split("<clip")[1:]:
    clip_start = ">".join(i.split(">")[1:])
    clip_content = clip_start.split("</clip")[0]
    article_clips.append(clip_content)
  
  return article_clips 


def get_clip_coords(article_clip):
  """Read in the clip content of a jp2 xml file and return an array of the 
  coord elements within that clip element"""

  clip_coords = []

  for i in article_clip.split("\n")[1:-1]:
    clip_coords.append(i.replace("\r",""))

  return clip_coords


def jp2_file_to_clip_coords(jp2_file_path):
  """Read in a jp2 file path and return an array of the coords in that jp2
  file's associated xml file"""

  jp2_file_clip_coords = []

  jp2_numpy_array    = jp2_to_array(jp2_file_path)
  image_height_width = get_image_height_width(jp2_numpy_array)
  image_integer_id   = get_image_file_id(jp2_file_path)
  jp2_xml_file_path  = get_xml_file_for_file_id(image_integer_id)
  jp2_xml_content    = read_xml_file(jp2_xml_file_path)
  xml_articles       = get_xml_articles(jp2_xml_content)

  # iterate over the articles in that jp2 file
  for article in xml_articles:
      article_clips = get_article_clips(article)       

      # iterate over the article clips
      for article_clip in article_clips:
        clip_coords = get_clip_coords(article_clip) 
        for j in clip_coords:
          jp2_file_clip_coords.append(j)

  return jp2_file_clip_coords


###########################
# XML Coordinate Analysis #
###########################

def get_coordinate_array(coord_element):
  """Read in a string denoting one <coord>...</coord>
  element in the current jp2's associated xml file, and return
  an array of integers that denote the element's x offset
  y offset, width, and height (in that order)"""

  coordinates_start = coord_element.split("<coord")[1]
  coordinates_clean_start = ">".join(coordinates_start.split(">")[1:])
  clean_coordinates = coordinates_clean_start.split("</coord>")[0]

  try:
    return [int(i) for i in clean_coordinates.split(":")]
  except:
    print "coordinate parsing failed; exiting"
    sys.exit()


def find_max_height_width_in_clip_coords(clip_coords):
  """Read in an array of <coord> elements within the current jp2 file
  and return the maximum distance along the x and y axes"""
  max_x = 0
  max_y = 0

  for coord in clip_coords:
    x_offset, y_offset, width, height = get_coordinate_array(coord)    

    if verbosity_level > 1:
      print "x-offset, y-offset, width, height:", x_offset, y_offset, width, height
  
    # to get the right-most position of this box, add x offset + width
    rightmost_position = x_offset + width

    if rightmost_position > max_x:
      max_x = rightmost_position

    # to get the bottom-most position of this box, add y offset + height
    bottommost_position = y_offset + height

    if bottommost_position > max_y:
      max_y = bottommost_position

  return [max_x, max_y]


def get_bounding_box_for_coord_element(coord, image_height_and_width, xml_height_and_width):
  """Read in the xml content from a single <coord> element, and the height and width
  params for both the image and the xml construct, and return the 
  min_row, max_row, min_column, and max_column, which allow the element to
  be plucked from the larger image/matrix in which they're embedded"""

  x_offset, y_offset, width, height = get_coordinate_array(coord)    

  # offsets are given from the top left corner in xml units 
  # so normalize them to {0,1} in the xml space by dividing by the max in the 
  # current dimension, then multiply that scaled value by the max in that 
  # dimension within the image (that is, multiply by the image's height or width.
  # then round to the nearest int, as pixels are 1 quantized
  min_row_in_normalized_xml_units =  y_offset / xml_height_and_width[0]
  max_row_in_normalized_xml_units = (y_offset + height) / xml_height_and_width[0]
  min_col_in_normalized_xml_units =  x_offset / xml_height_and_width[1]
  max_col_in_normalized_xml_units = (x_offset + width) / xml_height_and_width[1]

  min_row = int( min_row_in_normalized_xml_units * image_height_and_width[0] )
  max_row = int( max_row_in_normalized_xml_units * image_height_and_width[0] )
  min_column = int( min_col_in_normalized_xml_units * image_height_and_width[1] )
  max_column = int( max_col_in_normalized_xml_units * image_height_and_width[1] )

  return [min_row, max_row, min_column, max_column]


##################
# Image analysis #
##################

def bin_np_array(np_array_image, new_bit_resolution=4):
  """Instead of using the full range 0:255 values possible in the default
  8 bit color schema, use an artifically smaller bitrate by creating
  an array of bins that partition the 0:255 space, then place each pixel
  into the appropriate bin. Here n_bins controls the total number of
  bins to create, where the bins to create is 2**n_bins"""
  bin_breakpoints = []

  length_of_each_breakpoint = 256 / (2 ** new_bit_resolution)

  for i in xrange( 2 ** new_bit_resolution):
    bin_breakpoints.append( (i+1) * length_of_each_breakpoint )

  breakpoint_array = np.array(bin_breakpoints)
  quantized_image_vector = np.digitize(np_array_image, breakpoint_array)

  return quantized_image_vector


def dilate_pixels_in_x_y_dimensions(image_array):
  """Read in a numpy array describing the image to process and
  visualize the histograms of pixel density along the x and
  y axes, then return the top, bottom, left, and right margins
  in a dictionary"""
  row_vals = list([sum(r) for r in image_array  ])
  col_vals = list([sum(c) for c in image_array.T])

  if show_plots == 1:
    plt.plot(col_vals)
    plt.show()

    plt.plot(row_vals)
    plt.show()

  # use the dilations of the (quantized) image array to determine the page margins
  max_row_sum = max(row_vals)
  max_col_sum = max(col_vals)
  
  top_margin = 0

  for row in row_vals:
    if row == max_row_sum:
      top_margin += 1
    else:
      break

  bottom_margin = 0

  for row in reversed(row_vals):
    if row == max_row_sum:
      bottom_margin += 1
    else:
      break

  left_margin = 0

  for col in col_vals:
    if col == max_col_sum:
      left_margin += 1
    else:
      break

  right_margin = 0

  for col in reversed(col_vals):
    if col == max_col_sum:
      right_margin += 1
    else:
      break

  margins = {
    "top": top_margin,
    "right": right_margin,
    "bottom": bottom_margin,
    "left": left_margin
  }

  return margins

##################
# Write outfiles #
##################

def make_outdir_if_necessary(filename):
  """Read in a file name and make an outfile directory within segmented_images
  if that out directory doesn't exist yet"""
  if not os.path.exists("cropped_images/" + filename):
    os.makedirs("cropped_images/" + filename)


def write_segmented_images(filename, cropped_images_array):
  """Read in a filename and an array of cropped images and write the latter
  to disk within a directory within segmented_images that has the outfile's
  name"""

  filename = ".".join( os.path.basename(filename).split(".")[:-1] )

  make_outdir_if_necessary(filename)

  for c, cropped_image in enumerate(cropped_images_array):
    io.imsave( "cropped_images/" + filename + "/" + str(c) + ".png", cropped_image)


##############
# Main Block #
##############

if __name__ == "__main__":

  # define whether to run code in verbose mode
  verbosity_level = 1

  # define whether to show generated plots
  show_plots = 1

  # set the padding to be added to cropped images
  pad = 20

  directory_with_images = "./YDNSample"
  jp2_files = retrieve_image_list(directory_with_images)

  # iterate over each jp2 file
  for jp2_file in jp2_files[:1]:

    # transform the image file into a numpy array
    jp2_array = jp2_to_array(jp2_file) 

    # quantize the image vector by translating into a lower bitrate space
    quantized_image_vector = bin_np_array(jp2_array, new_bit_resolution=1)

    # compute the image margins and display the pixel dilations in the x and y dimensions
    image_margins = dilate_pixels_in_x_y_dimensions(quantized_image_vector)

    # define an empty array of cropped image coordinates
    cropped_images = []

    jp2_file_clip_coords = jp2_file_to_clip_coords(jp2_file)
    max_height_and_width_positions_in_xml = find_max_height_width_in_clip_coords(jp2_file_clip_coords)
    jp2_image_dimensions = get_image_height_width(jp2_array)

    # adjust the image height and width to remove the right and bottom margins
    height_and_width_of_jp2 = remove_right_and_bottom_margins(jp2_image_dimensions, image_margins)

    for coord in jp2_file_clip_coords:
      if verbosity_level == 1:
        print coord

      bounding_box = get_bounding_box_for_coord_element(coord, height_and_width_of_jp2,
          max_height_and_width_positions_in_xml)
      min_row, max_row, min_column, max_column = bounding_box

      if verbosity_level == 1:
        print "bounding box coordinates for coord:", min_row, max_row, min_column, max_column

      cropped_images.append(jp2_array[min_row-pad:max_row+pad, min_column-pad:max_column+pad])

    write_segmented_images(jp2_file, cropped_images)


