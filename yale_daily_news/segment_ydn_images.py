from __future__ import division
from multiprocessing import Pool
from collections import defaultdict
from skimage import io
from scipy import ndimage
import matplotlib.pyplot as plt
import numpy as np
import glob, os, codecs, sys, json, shutil

'''
## Processing notes

The Alto XML structure is as follows:

Each `root_dir` has multiple `issues`.
Each `issue` has multiple `pages`.
Each `page` has multiple `articles`.
Each `article` has multiple `images`.
Each image can belong to one page (if the article fits entirely on one page)
or multiple pages (if the article spans multiple pages).
'''

######################################
# Convert jp2 images to numpy arrays #
######################################

def convert_jp2_images_to_numpy_arrays(root_data_directory):
  '''
  Read in the path to a directory that contains subdirectories
  for each newspaper issue, iterate over the jp2 files 
  in those directories and write each to disk as a numpy array
  '''
  
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
  '''
  Read in the path to a directory that contains a series of
  subdirectories, each of which should contain one or more files 
  for the images/pages in that issue of the paper. Return an array
  of all of the issue subdirectories
  '''
  return glob.glob(directory_with_issue_directories + '/*')[:max_files_to_process]


def get_images_in_directory(path_to_directory):
  '''
  Read in a path to a directory and return an array of jp2
  files in that directory
  '''
  return list( glob.glob(path_to_directory + '/*.jp2')[:max_files_to_process] )


def image_path_to_npy(path_to_jp2_image):
  '''
  Read in the full path to a jp2 image, read that image into memory,
  convert to a numpy array and save as a npy file
  '''
  jp2_array =  jp2_path_to_array(path_to_jp2_image)
  write_jp2_array_to_disk(jp2_array, path_to_jp2_image)


def jp2_path_to_array(path_to_jp2_file):
  '''
  Read in the path to a jp2 image file and return that
  file as a numpy array that represents the pixel values of 
  that image
  '''

  # try to read the numpy array into memory from a npy file. 
  # if the image hasn't been converted yet, convert it and then write it 
  # at the end of this loop, to save on i/o the next time we process this file
  try:
    jp2_issue_directory = path_to_jp2_file.split('/')[-2]
    jp2_basename = os.path.basename(path_to_jp2_file)
    
    path_to_saved_numpy_array =  './numpy_arrays/' + jp2_issue_directory 
    path_to_saved_numpy_array += '/' + jp2_basename + '.npy'

    jp2_array = np.load(path_to_saved_numpy_array)

    if verbosity_level > 0:
      print 'read the following image from disk', path_to_jp2_file

    return jp2_array

  # if an exception arises, then read the image from disk and write its npy file
  except Exception as exc:
    jp2_array = io.imread(path_to_jp2_file, plugin='freeimage')     
    write_jp2_array_to_disk(jp2_array, path_to_jp2_file)

    return jp2_array


def write_jp2_array_to_disk(jp2_array, jp2_path):
  '''
  Read in a numpy array and the path to the jp2 file, and
  write that numpy array to disk in a directory with the same 
  name as the issue subdirectory from which the image was read
  '''

  jp2_filename = os.path.basename(jp2_path)
  jp2_issue_directory = jp2_path.split('/')[-2]

  out_directory = 'numpy_arrays/' + jp2_issue_directory + '/'
  out_path = out_directory + jp2_filename + '.npy'

  if not os.path.exists(out_directory):
    os.makedirs(out_directory)

  np.save(out_path, jp2_array)


######################
# XML Helper Methods #
######################

def get_page_mappings(issue_directory):
  '''
  In 1.articles.xml (e.g.) there are <coord> elements with
  inpage attributes:

  <page id="1" {...} unit="pixel">
    <article>
      <id>DIVL11</id>
      <title></title>
      <type>ARTICLE</type>
      <clip type="normal">
        <coord inpage="1">425:619:210:20</coord>  <- inpage attribute
        <coord inpage="1">185:666:687:202</coord>
        <coord inpage="1">178:915:668:47</coord>
      </clip>
    {...}
  </page>

  These inpage values refer to the id attribute of the page
  on which the given rect appears.

  With each issue directory, there's a file /index.cpd that lists
  the pages in 1-based index positions:

  <?xml version="1.0"?>
  <cpd>
    <type>Document</type>
    <page>
      <pagetitle>Page 1</pagetitle>
      <pagefile>1.jp2</pagefile>
      <pageptr>+</pageptr>
    </page>
    <page>
      <pagetitle>Page 2</pagetitle>
      <pagefile>5.jp2</pagefile>
      <pageptr>+</pageptr>
    </page>
  </cpd>

  Here 1.jp2 is page id 1, 5.jp2 is page id 2, and so on.

  Return a mapping from page name to page id
  and a mapping from page id to page name.
  '''

  page_file_to_page_id = {}
  page_id_to_page_file = {}

  with codecs.open(issue_directory + '/index.cpd', 'r', 'utf-8') as f:
    f = f.read()
    pages = f.split('<page>')

    for page_index, page in enumerate(pages[1:]):

      # use 1-based indexing as the coord elements do
      page_index += 1

      page_content = page.split('</page>')[0]
      page_file = page_content.split('<pagefile>')[1]
      clean_page_file = page_file.split('</pagefile>')[0]
      page_file_to_page_id[clean_page_file] = page_index
      page_id_to_page_file[page_index] = clean_page_file

  return page_id_to_page_file, page_file_to_page_id


def get_article_xml_files(issue_directory):
  '''
  Read in the path to a directory with files for a single issue and
  return an array of article xml files within that directory's issue
  '''
  return glob.glob(issue_directory + '/*.articles.xml')


def read_xml_file(xml_file_path):
  '''
  Read in the path to an xml file and return that
  xml file content in string form
  '''
  with codecs.open(xml_file_path, 'r', 'utf-8') as f:
    return f.read()


def get_xml_articles(xml_content):
  '''
  Read in a string containing XML content and return an array
  of the articles in that XML document
  '''
  articles = []
  
  for i in xml_content.split('<article')[1:]:
    article_start = '>'.join(i.split('>')[1:])
    article_content = article_start.split('</article')[0]
    articles.append(article_content)

  return articles


def get_article_clips(article, restrict_to_uc=1):
  '''
  Read in the xml content from an article and return an array of
  the clips in that article. If restrict_to_uc == 1, only return
  clips if they have type 'uc'
  '''
  
  article_clips = []
  
  for i in article.split('<clip')[1:]:

    if restrict_to_uc == 1:
      if 'type="uc"' not in i:
        continue

    clip_start = '>'.join(i.split('>')[1:])
    clip_content = clip_start.split('</clip')[0]
    article_clips.append(clip_content)
  
  return article_clips 


def get_clip_coords(article_clip):
  '''
  Read in the clip content of a jp2 xml file and return an array of the
  coord elements within that clip element
  '''

  clip_coords = []

  for i in article_clip.split('\n')[1:-1]:
    clip_coords.append(i.replace('\r',''))

  return clip_coords


def get_coordinate_array(coord_element):
  '''
  Read in a string denoting one <coord>...</coord>
  element in the current jp2's associated xml file, and return
  an array of integers that denote the element's x offset
  y offset, width, and height (in that order), as well as
  an integer that indicates the page in which that rectangle
  is present
  '''

  page_with_rectangle = coord_element.split('inpage="')[1].split('"')[0]

  coordinates_start = coord_element.split('<coord')[1]
  coordinates_clean_start = '>'.join(coordinates_start.split('>')[1:])
  clean_coordinates = coordinates_clean_start.split('</coord>')[0]

  try:
    return [int(i) for i in clean_coordinates.split(':')], page_with_rectangle
  except:
    print 'coordinate parsing failed; exiting'
    sys.exit()


###############################
# Generate Master XML Mapping #
###############################

def generate_issue_page_rectangle_mapping(root_data_directory):
  '''
  Read in a path to a directory that has subdirectories, each of
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
  Then write this mapping to disk
  '''

  # unique identifier given to each rectangle created
  rect_id = 0

  # d[issue_directory][article_xml_filename][article_index] = [{img_with_rect:, rect_coords:}]
  rects_to_articles = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

  # d[issue_directory][img_file] = [{rect_id: , rect_coords: }]
  imgs_to_crop = defaultdict(lambda: defaultdict(list))

  # each issue_directory contains a single issue of the newspaper
  issue_directories = get_issue_directories(root_data_directory)
  for issue_directory in issue_directories:
    page_id_to_page_file, page_file_to_page_id = get_page_mappings(issue_directory)
  
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

        # store a boolean indicating whether this article includes rects from
        # multiple images. This is used to prevent us from duplicating rects
        # in articles with multiple pages (as the ALTO XML does)
        rects_already_stored = False

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
          for xml_coord_index, xml_coord in enumerate(xml_coords):

            xml_coordinate_array, coord_inpage_value = get_coordinate_array(xml_coord)

            # now use the coord_inpage_value to identify the file with the rectangle
            img_with_rect = page_id_to_page_file[int(coord_inpage_value)]

            # also parse out the xml file that references the image
            article_xml_filename = os.path.basename(xml_page)

            # identify the image for the current xml file
            current_img = os.path.basename(article_xml_filename)
            current_img = current_img.replace('.articles.xml','.jp2')

            # d[issue_directory][img_file] = [{rect_id: , rect_coords: }]
            imgs_to_crop[issue_directory][img_with_rect].append({
              'coords': xml_coordinate_array,
              'rect_id': rect_id
            })

            # articles that appear on multiple pages have their XML coordinates
            # expressed on each page where they occur--this is part of the ALTO
            # XML schema. To ensure we don't create duplicate outputs for those
            # articles, examine the first XML coordinate for the given rect.
            # If the image for that coord set occurs on the current image, store
            # the mapping, else continue
            if xml_coord_index == 0:
              if current_img != img_with_rect:
                rects_already_stored = True

            print article_index, xml_coord_index, img_with_rect, rect_id

            if not rects_already_stored:
              rects_to_articles[issue_directory][article_xml_filename][article_index].append({
                'img_with_rect': img_with_rect,
                'rect_coords': xml_coordinate_array,
                'rect_id': rect_id
              })

            rect_id +=1

  with open('rects_to_articles.json', 'w') as out:
    json.dump(rects_to_articles, out)

  with open('imgs_to_crop.json', 'w') as out:
    json.dump(imgs_to_crop, out)

##################
# Segment Images #
##################

def segment_images(process_id):
  '''
  Read in a process id that will indicate which enumerated issues
  the current process is responsible for. Then read into memory
  the imgs_to_crop JSON, read in the
  numpy array that corresponds to each image file identified in
  that JSON file, pluck out the appropriate rectangles, and save
  them to disk. To ensure equal division of labor among processors,
  only allow the current process to work on an issue directory if
  issue directory index position % total number of processes ==
  process id
  '''

  with open('imgs_to_crop.json') as f:
    rectangle_mappings = json.load(f)

  for c, issue_directory in enumerate(rectangle_mappings.iterkeys()):

    # to distribute work among available processors, enumerate the issue directories,
    # take the current issue directory number modulo the total number of processes,
    # and check if that value == the current process id; if not, continue
    if c % n_processes != process_id:
      continue

    for page in rectangle_mappings[issue_directory].iterkeys():

      # fetch the numpy array for cropping
      jp2_array = jp2_path_to_array(issue_directory + '/' + page)

      for rect in rectangle_mappings[issue_directory][page]:
        rect_id = rect['rect_id']
        rect_coords = rect['coords']
        jp2_coordinates = convert_coordinates(rect_coords, jp2_array, page)

        if not jp2_coordinates:
          print 'jp2_coordinates unavailable for', page
          continue

        min_row, max_row, min_col, max_col = [int(i) for i in jp2_coordinates]

        if verbosity_level > 1:
          print issue_directory, page, article_index
          print xml_coordinates
          print min_row, max_row, min_col, max_col

        cropped = jp2_array[min_row:max_row, min_col:max_col]

        # write the cropped image to disk
        out_path  = 'cropped_images/' + issue_directory + '/'

        if not os.path.exists(out_path):
          os.makedirs(out_path)

        io.imsave(out_path + str(rect_id) + '.png', cropped)
        

def convert_coordinates(xml_coordinate_array, jp2_array, page):
  '''
  Read in an array of four coordinates that describe a
  single rectangle in XML type='uc' coordinates, a jp2 image pixel
  array, and a page identifier, and return an array of the
  min_row, max_row, min_col, max_col values
  needed in jp2 pixels to describe the same rectangle
  '''

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

###########################################
# Sort the segmented images into articles #
###########################################

def sort_segmented_images():
  '''
  Once all the segmented images are on disk, sort them into their relevant
  articles
  '''

  with open('rects_to_articles.json') as f:
    rects_to_articles = json.load(f)

  for issue in rects_to_articles.keys():
    for page in rects_to_articles[issue].keys():
      for article_index in rects_to_articles[issue][page]:
        for rect_meta in rects_to_articles[issue][page][article_index]:
          page_number = page.split('.')[0]

          print('making', 'cropped_images' + issue + '/' + article_index + '/')
          img_path = 'cropped_images' + issue + '/' + str(rect_meta['rect_id']) + '.png'
          out_path  = 'segmented_images' + issue + '/' + page_number + '/' + article_index + '/'
          if not os.path.exists(out_path):
            os.makedirs(out_path)
          shutil.move(img_path, out_path)
          print(issue, page, article_index, rect_meta)

##############
# Main Block #
##############

if __name__ == '__main__':

  ###
  # Global params 
  ###

  # Define the directory that contains subdirectories for each paper issue
  root_data_directory = '/Users/doug/Desktop/ydn-sample/'

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

  # Rearrange the segmented files into /issue/page/article subdirs
  sort_segmented_images()