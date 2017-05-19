from __future__ import division
from multiprocessing import Pool
from collections import defaultdict
from skimage import io
from scipy import ndimage
import matplotlib.pyplot as plt
import numpy as np
import glob, os, codecs, sys, json

######################################
# Convert jp2 images to numpy arrays #
######################################

def convert_jp2_images_to_numpy_arrays(root_data_directory):
  """Read in the path to a directory that contains subdirectories 
  for each newspaper issue, iterate over the jp2 files 
  in those directories and write each to disk as a numpy array"""
  
  # each image file in the issue_directory contains a single page of the newspaper
  issue_directories = get_issue_directories(root_data_directory)

  # iterate over each issue directory
  for issue_directory in issue_directories:

    # find all jp2 images within the current issue directory
    issue_images = get_images_in_directory(issue_directory)

    # create process pool using all available cpu processors
    pool_one = Pool(n_processes)

    # use the process pool to convert each jp2 image to a numpy array
    for result in pool_one.imap(image_path_to_npy, issue_images):
      pass

    pool_one.close()
    pool_one.join()


def get_issue_directories(directory_with_issue_directories):
  """Read in the path to a directory that contains a series of 
  subdirectories, each of which should contain one or more files 
  for the images/pages in that issue of the paper. Return an array
  of all of the issue subdirectories"""
  return glob.glob(directory_with_issue_directories + "/*")[:max_files_to_process]


def get_images_in_directory(path_to_directory):
  """Read in a path to a directory and return an array of jp2
  files in that directory"""
  return list( glob.glob(path_to_directory + "/*.jp2")[:max_files_to_process] )


def image_path_to_npy(path_to_jp2_image):
  """Read in the full path to a jp2 image, read that image into memory,
  convert to a numpy array and save as a npy file"""
  jp2_array =  jp2_path_to_array(path_to_jp2_image)
  write_jp2_array_to_disk(jp2_array, path_to_jp2_image)


def jp2_path_to_array(path_to_jp2_file):
  """Read in the path to a jp2 image file and return that 
  file as a numpy array that represents the pixel values of 
  that image"""

  # try to read the numpy array into memory from a npy file. 
  # if the image hasn't been converted yet, convert it and then write it 
  # at the end of this loop, to save on i/o the next time we process this file
  try:
    jp2_issue_directory = path_to_jp2_file.split("/")[-2]
    jp2_basename = os.path.basename(path_to_jp2_file)
    
    path_to_saved_numpy_array =  "./numpy_arrays/" + jp2_issue_directory 
    path_to_saved_numpy_array += "/" + jp2_basename + ".npy"

    jp2_array = np.load(path_to_saved_numpy_array)

    if verbosity_level > 0:
      print "read the following image from disk", path_to_jp2_file

    return jp2_array

  # if an exception arises, then read the image from disk and write its npy file
  except Exception as exc:
    jp2_array = io.imread(path_to_jp2_file, plugin='freeimage')     
    write_jp2_array_to_disk(jp2_array, path_to_jp2_file)

    return jp2_array


def write_jp2_array_to_disk(jp2_array, jp2_path):
  """Read in a numpy array and the path to the jp2 file, and 
  write that numpy array to disk in a directory with the same 
  name as the issue subdirectory from which the image was read"""

  jp2_filename = os.path.basename(jp2_path)
  jp2_issue_directory = jp2_path.split("/")[-2]

  out_directory = "numpy_arrays/" + jp2_issue_directory + "/"
  out_path = out_directory + jp2_filename + ".npy"

  if not os.path.exists(out_directory):
    os.makedirs(out_directory)

  np.save(out_path, jp2_array)


######################
# XML Helper Methods #
######################

def get_page_mapping(issue_directory):
  """In 1.articles.xml (e.g.) there are <coord> elements with 
  inpage elements. Each inpage element refers to the page that 
  contains the box defined within the coord element xml. 
  These inpage elements indicate the 1-based index position of 
  the page that contains the rectangle described in the xml. So 
  return a 1 based mapping from pageid {1:n_pages_in_issue} to
  the file in which that issue is displayed"""

  page_id_to_page_file = {}

  with codecs.open(issue_directory + "/index.cpd", "r", "utf-8") as f:
    f = f.read()
    pages = f.split("<page>")

    for page_index, page in enumerate(pages[1:]):

      # use 1-based indexing as the coord elements do
      page_index += 1

      page_content = page.split("</page>")[0]
      page_file = page_content.split("<pagefile>")[1]
      clean_page_file = page_file.split("</pagefile>")[0]

      page_id_to_page_file[page_index] = clean_page_file

  return page_id_to_page_file


def get_article_xml_files(issue_directory):
  """Read in the path to a directory with files for a single issue and 
  return an array of article xml files within that directory's issue"""
  return glob.glob(issue_directory + "/*.articles.xml")


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
    articles.append(article_content)

  return articles


def get_article_clips(article, restrict_to_uc=1):
  """Read in the xml content from an article and return an array of
  the clips in that article. If restrict_to_uc == 1, only return
  clips if they have type 'uc'"""
  
  article_clips = []
  
  for i in article.split("<clip")[1:]:

    if restrict_to_uc == 1:
      if 'type="uc"' not in i:
        continue

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


def get_coordinate_array(coord_element):
  """Read in a string denoting one <coord>...</coord>
  element in the current jp2's associated xml file, and return
  an array of integers that denote the element's x offset
  y offset, width, and height (in that order), as well as
  an integer that indicates the page in which that rectangle
  is present"""

  page_with_rectangle = coord_element.split('inpage="')[1].split('"')[0]

  coordinates_start = coord_element.split("<coord")[1]
  coordinates_clean_start = ">".join(coordinates_start.split(">")[1:])
  clean_coordinates = coordinates_clean_start.split("</coord>")[0]

  try:
    return [int(i) for i in clean_coordinates.split(":")], page_with_rectangle
  except:
    print "coordinate parsing failed; exiting"
    sys.exit()


###############################
# Generate Master XML Mapping #
###############################

def generate_issue_page_rectangle_mapping(root_data_directory):
  """Read in a path to a directory that has subdirectories, each of
  which has files for a single newspaper issue. Iterate over those
  issue directories and create a dictionary that maps the following
  hierarchy:

  issue directory -> multiple pages
    each page id -> multiple rectangles

  For each rectangle, store that rectangle's coordinates
  and the page and article to which the rectangle belongs
  (e.g. if we have a rectangle printed on page 2 that is continued
  from page 1, store an indicate that the rectangle belongs
  to an article with a particular index position on page 1).
  Then write this mapping to disk"""

  master_xml_mapping = defaultdict(lambda: defaultdict(list))
  issue_directories = get_issue_directories(root_data_directory)

  # each issue_directory contains a single issue of the newspaper
  for issue_directory in issue_directories:
    page_mapping = get_page_mapping(issue_directory)
  
    # each xml/jp2 file combination in the issue_directory 
    # contains a single newspaper page
    xml_pages = get_article_xml_files(issue_directory)

    # iterate over each xml file and get all articles on that page
    for page_index, xml_page in enumerate(xml_pages):

      # xml_content is a unicode string with the xml content
      xml_content = read_xml_file(xml_page)

      # page_articles is an array of the article elements in the xml
      xml_articles = get_xml_articles(xml_content)

      # loop over each article and get all 'clips' for that article
      for article_index, xml_article in enumerate(xml_articles):

        # xml_clips is an array of the clips within the current article
        xml_clips = get_article_clips(xml_article)

        # each xml_clip contains a sequence of coordinates that define 
        # a rectangle a user drew on a jp2 image
        for clip_index, xml_clip in enumerate(xml_clips):

          # xml_coords is an array of the coords in the current clip
          xml_coords = get_clip_coords(xml_clip)

          # each xml_coord is an array of 4 coordinates that describe the 
          # x_offset, y_offset, width, height of a rectangle to be
          # extracted from the jp2. This rectangle is described in xml
          # units and must be converted into pixel units for extraction
          # The coord_inpage_value indicates the integer used in the <coord
          # inpage={int} value, which must be mapped to a proper file
          for xml_coord in xml_coords:

            xml_coordinate_array, coord_inpage_value = get_coordinate_array(xml_coord)

            # now use the coord_inpage_value to identify the file with the rectangle
            image_file_with_rectangle = page_mapping[int(coord_inpage_value)]

            # also lookup the image file to which the rectangle belongs
            image_file_to_which_rectangle_belongs = page_mapping[page_index+1]

            # append the current rectangle with associated metadata to the master
            # mapping of images to rectangles
            master_xml_mapping[issue_directory][image_file_with_rectangle].append(
              {
                "rectangle_coordinates": xml_coordinate_array,
                "image_file_with_rectangle": image_file_with_rectangle,
                "belongs_to_page_index": image_file_to_which_rectangle_belongs,
                "belongs_to_article_index": article_index
              }
            )

  # write the master xml file mapping to disk
  with open("issue_to_pages_to_rectangles.json", "w") as xml_mapping_out:
    json.dump(master_xml_mapping, xml_mapping_out)


##################
# Segment Images #
##################

def segment_images(process_id):
  """Read in a process id that will indicate which enumerated issues
  the current process is responsible for. Then read into memory
  the issue_to_pages_to_rectangles JSON, read in the
  numpy array that corresponds to each image file identified in
  that JSON file, pluck out the appropriate rectangles, and save
  them to disk. To ensure equal division of labor among processors,
  only allow the current process to work on an issue directory if
  issue directory index position % total number of processes ==
  process id"""

  with open("issue_to_pages_to_rectangles.json") as f:
    rectangle_mappings = json.load(f)

  # create a dictionary of the rectangles to crop
  cropped_images = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

  for c, issue_directory in enumerate(rectangle_mappings.iterkeys()):

    # to distribute work among available processors, enumerate the issue directories,
    # take the current issue directory number modulo the total number of processes,
    # and check if that value == the current process id; if not, continue
    if c % n_processes != process_id:
      continue

    for page in rectangle_mappings[issue_directory].iterkeys():

      # fetch the numpy array for cropping
      jp2_array = jp2_path_to_array(issue_directory + "/" + page)

      page_rectangles = rectangle_mappings[issue_directory][page]
      for rectangle_index, rectangle in enumerate(page_rectangles):
        article_index   = rectangle["belongs_to_article_index"]

        xml_coordinates = rectangle["rectangle_coordinates"]
        jp2_coordinates = convert_coordinates(xml_coordinates, jp2_array, page)

        if not jp2_coordinates:
          continue

        min_row, max_row, min_col, max_col = [int(i) for i in jp2_coordinates]

        if verbosity_level > 1:
          print issue_directory, page, article_index
          print xml_coordinates
          print min_row, max_row, min_col, max_col

        cropped = jp2_array[min_row:max_row, min_col:max_col]
        cropped_images[issue_directory][page][article_index].append(cropped)

  write_segmented_images(cropped_images)
        

def convert_coordinates(xml_coordinate_array, jp2_array, page):
  """Read in an array of four coordinates that describe a 
  single rectangle in XML type='uc' coordinates, a jp2 image pixel
  array, and a page identifier, and return an array of the
  min_row, max_row, min_col, max_col values
  needed in jp2 pixels to describe the same rectangle"""

  # magic number plucked from client side js in extant YDN app
  # it's the largest 16 bit integer
  multiplier = 65535

  # scale is a positive integer that indicates zoom level in the app
  scale = 100

  # array of uc coordinates from XML
  left, top, width, height = xml_coordinate_array

  if len(jp2_array.shape) != 2:
    print 'could not process', page, jp2_array.shape
    return None

  # the height and width of the original image
  img_height, img_width = jp2_array.shape

  new_left   = ((left / multiplier) * img_width) * scale / 100
  new_top    = ((top / multiplier) * img_height) * scale / 100
  new_width  = ((width / multiplier) * img_width) * scale / 100
  new_height = ((height / multiplier) * img_height) * scale / 100

  # return these values in min_row, max_row, min_col, max_col form
  return new_top, new_top+new_height, new_left, new_left+new_width
  

def write_segmented_images(cropped_images_dict):
  """Read in a defaultdict with the following structure:
    cropped_images[issue_directory][page][article_index].append(cropped)
  and write each jp2 cropping from each image to disk"""

  for issue_directory in cropped_images_dict.iterkeys():
    for page in cropped_images_dict[issue_directory].iterkeys():
      for article in cropped_images_dict[issue_directory][page].iterkeys():
        cropped_rectangles = cropped_images_dict[issue_directory][page][article]

        for c, cropped_rectangle in enumerate(cropped_rectangles):

          out_path  = "cropped_images/" + issue_directory + "/"
          out_path += page + "/article_" + str(article) + "/" 

          if not os.path.exists(out_path):
            os.makedirs(out_path)

          io.imsave(out_path + str(c) + ".png", cropped_rectangle)


##############
# Main Block #
##############

if __name__ == "__main__":

  ###
  # Global params 
  ###

  # Define the directory that contains subdirectories for each paper issue
  root_data_directory = "/Volumes/LaCie 10GB/YDN/"

  # Define whether to run code in verbose mode
  verbosity_level = 1

  # Identify the maximum number of processors to use during analysis
  n_processes = 4

  # Specify the maximum number of files to process
  max_files_to_process = 20

  # allow users to toggle multiprocessing on/off
  multiprocess = False

  # Convert jp2 images into numpy arrays (must only be run once)
  convert_jp2_images_to_numpy_arrays(root_data_directory)

  # Generate master XML mapping
  generate_issue_page_rectangle_mapping(root_data_directory)

  # Generate array of process ids
  process_ids = list(xrange(n_processes))

  # Generate a pool to manage processes for image segmentation
  pool_two = Pool(n_processes)

  # Segment the images
  if multiprocess:
    for result in pool_two.imap(segment_images, process_ids):
      pass

  else:
    for i in process_ids:
      segment_images(i)