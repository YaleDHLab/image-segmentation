

#note: make a function to "construct article"
    #take the identifiesrs (page numbers, MODSMD_ARTICLExx)
    #check inpage value, cut pieces from each page.
    #add some extra space for each cut out piece.

#intiators for executable
#filenum = 1
#folder = 'YDNSample'
#filetitle = folder + '/' + str(filenum)
#filexml = filetitle + ".articles.xml"
#filejp2 = filetitle + ".jp2"


#def page_to_filejp2(folder, page):
#    title = folder + '/' + page
#    return title + ".jp2"



#7/20/16 notes on raw material
#NOTE: cleaner terminology: 
    #collection, paper, page, article, box
    #xml, jp2
    #read, write (folders)

#NOTE: 6.articles.xml doesn't always mean page 6. sometimes if it is the 
    #2nd file in order, it is page 2...
    #633325303581272229 1.articles.xml doesn't include the top title...
        #messes up normalization (overstretches y-axis)
        #this also includes weird additional boxes at paragraph breaks.


from xml.dom.minidom import parse
#returns articles that start on the given page/filenum
#Return list of lists of box coords, in the order
#[[x_start, y_start, width, height] , [...], [...], ...]
#(with origin at top left corner, growing to the right and bottom)
#NOTE: not really useful. Just open the whole page. some pages will 
    #not have all articles that appear on that page, because those are
    #included in earlier pages. 
def get_page_box_list(filename):
    filenum = filename.strip('.articles.xml')
    DOMTree = parse(filename)
    DOMTree_clips = DOMTree.getElementsByTagName('clip')
    uc_clips = [x for x in DOMTree_clips if x.getAttribute('type') == 'uc']
    box_list = []
    for clip in uc_clips:
        coords = clip.getElementsByTagName("coord")
        #coords if they are on given page
        coord_list = [coord.firstChild.nodeValue for coord in coords
                      if coord.getAttribute("inpage") == str(filenum)]
        box_list += [coord.split(":") for coord in coord_list]
    return box_list

'''return a Nodelist of all articles that start on the page.
Each article is an xml element of the format:
<article>
    <id>MODSMD_ARTICLE18</id>
    <title></title>
    <type></type>
    <subheadline></subheadline>
    <clip type="uc">
      <coord inpage="2">1421:52485:12272:7704</coord>
      <coord inpage="4">27039:2203:37202:7499</coord>
    </clip>
''' #note the linguistic confusion: this is list of articles. the one
#below is box_list that belong to an article. But both are "article_sthsth"
def get_article_list(filename):
    DOMTree = parse(filename)
    return DOMTree.getElementsByTagName('article')


#take an article as an xml element.(Node) (see format above)
#return list of list of lists: For each page with at least a box/piece
#of the article, return a box_list. e.g.
#[[[page1 box1 coords],[page1 box2 coords], ...], [[page6 box1 coords]]...]
def get_article_box_lists(article):
    #access xml node 'article', then 'uc_clips'.
    article_clips = article.getElementsByTagName('clip')
    uc_clips = [x for x in article_clips if x.getAttribute('type') == 'uc']
    if len(uc_clips) != 1:
        raise Exception("article in page does not have single set of "
                        "box uc-coordinates")
    #gather page_indices with pieces of the article
    #(sometimes boxes jump from page 1 to p.4 back to p.1)
    box_nodes = uc_clips[0].getElementsByTagName('coord')
    page_indice = list(set([box_node.getAttribute('inpage') for box_node
                in box_nodes]))
    #for each page, make a list within list.
    pages = []
    for page in page_indice:
        pages.append([])
    for box_node in box_nodes:
        box = box_node.firstChild.nodeValue.split(":")
        cur_inpage = (box_node.getAttribute('inpage'))
        page_index = page_indice.index(cur_inpage)
        pages[page_index].append(box)
    return pages


#take an article xml element (Node).
#return article_id
def get_article_id(article):
    return article.getElementsByTagName('id')[0].firstChild.nodeValue

def get_article_pages(article):
    pages = [box.getAttribute('inpage') 
            for box in article.getElementsByTagName('coord')]
    pages = list(set(pages))
    return pages


#get normalizer constants based on a standard-setting file (i.e. one where
#articles appear throughout the whole page)
#write json of dict {x_max, y_max, x_min, y_min, x_dim, y_dim} 
    #reminder: box_format is [x_start, y_start, width, height]
    #imports json module if write_json is True
def write_n_consts(filexml, filejp2, out_path, write_json = True):
    box_list = get_page_box_list(filexml)
    #
    box_num = len(box_list)
    #
    #x_start + width
    x_lims = [int(box_list[i][0]) + int(box_list[i][2]) for i in range(box_num)]
    #y_start + height
    y_lims = [int(box_list[i][1]) + int(box_list[i][3]) for i in range(box_num)]
    #
    x_max = max(x_lims)
    y_max = max(y_lims)
    x_min = min([int((box_list[i][0])) for i in range(box_num)])
    y_min = min([int((box_list[i][1])) for i in range(box_num)])
    #
    fullres = read_jp2(filejp2)
    #x and y seemed to be inverted in fullres.shape
    x_dim = fullres.shape[1]
    y_dim = fullres.shape[0]
    #
    n_consts = {'x_max': x_max, 'y_max': y_max,
                'x_min': x_min,'y_min': y_min,
                'x_dim': x_dim, 'y_dim': y_dim}
    if write_json:
        import json
        n_consts_json = json.dumps(n_consts)
        f = open(out_path + 'n_consts.json', 'w')
        f.write(n_consts_json)
        f.close()
    return n_consts             #Maybe remove this return,or turn into print

#read normalizer constants from json file
def read_n_consts(path):
    import json
    f = open(path + 'n_consts.json', 'r')
    json_consts = f.read()
    f.close()
    return json.loads(json_consts)


#take coordinate number and normalize it by given normalize_constant_dict
#(i.e. translate xml coord to pixel)
def normalize(coord, n_consts, x_val=True):
    if x_val == True:
        mx, dm = n_consts['x_max'], n_consts['x_dim']
    else:
        mx, dm = n_consts['y_max'], n_consts['y_dim']
    return round(coord * dm / mx)



'''read jp2
'''

#read in jp2 file
def read_jp2(filename):
    import glymur
    jp2 = glymur.Jp2k(filename)
    return jp2[:] 




#NOTE:maybe fuzz those bounds a little. subtract from first val, 
#add to end val.
#x_bounds= [(round(x*x_dim), round(x_end*x_dim))
#                   for (x,x_end) in x_bound_props]
#y_bounds= [(round(y*y_dim), round(y_end*y_dim))
#                   for (y,y_end) in y_bound_props]


'''bound correction'''
#method 1 constant fuzzing
#enlarge the bounding box boundaries. if lower bound, stretch lower;
#if upper bound, stretch higher
#Assume normalized bound (coord)
def fuzz(bound, n_consts, lower=True, x_val = True):
    fuzz_const = 50        #set by eyeballing a case article, in pixels
    upper_bound = normalize(n_consts['x_max'], n_consts, x_val)\
                    if (x_val==True)\
                    else normalize(n_consts['y_max'], n_consts, x_val)
    if lower:
        #round down and (subtract a bit)         
        output = (int(bound - fuzz_const))
        return max(output, 0)
    else:
        output = (int(bound + fuzz_const))
        return min(output, upper_bound)


#method 2 shift the minimum (x,y) as the new origin. (subtract x_min from
#all x's and y_min from all y's.)
#Assume normalized bound (coord)
def shift(bound, n_consts, x_val=True):
    if x_val == True:
        mx, mn, dm = n_consts['x_max'], n_consts['x_min'], n_consts['x_dim']
    else:
        mx, mn, dm = n_consts['y_max'], n_consts['y_min'], n_consts['y_dim']
    #use minimum (upper left corner) to account for margins. divide by 2 
    #for even distribution between page top and bot
    new_bound = bound - (normalize(mn, n_consts,x_val)/2)
    return max(round(new_bound), 0)

'''form and write jpeg'''
#boxnum = 6
#outfile = '2testbox.jp2'










#
#to do: write executable part, for all and for articles. debug what came#rewrite writejp2.
#write in_box ()  for building word list.(use unnormalzied coordinates. )

#NOTE: set filejp2 according to page number!
def write_jp2_box(n_consts, box, jp2, outfile, write=True):
    import glymur
    #x, y, width, height
    x,y,w,h = int(box[0]), int(box[1]), int(box[2]), int(box[3])
    #box corners
    corners = [x, y, x+w, y+h]
    #normalized corners
    norm_corners = [normalize(corners[i], n_consts, x_val = (i+1)% 2)
                    for i in range(4)]
    print('norm_corners: ', norm_corners)
    print('norm_corner diffs: ', norm_corners[2]-norm_corners[0],
          norm_corners[3]-norm_corners[1])
    #fuzzed/shifted corners
    shift_corners = [shift(norm_corners[i], n_consts, x_val = (i+1)%2)
                    for i in range(4)]
    print('shift_corners: ', shift_corners)
    #read box areas from jp2
    #note: glymur reads data as (y,x). so y_lower:y_upper, x_lower:x_upper
    jp2_crop = jp2[shift_corners[1]:norm_corners[3],
                   shift_corners[0]:norm_corners[2]]
    if write:
        glymur.Jp2k(outfile, data = jp2_crop)
    else:
        return jp2_crop



#debug from here


#QUESTIONS: shift or fuzz corners? change in write_jp2_box()
        #what are the filenames, folders, paper_ids?

#have names by paper_id? decide outfolder.
#NOTE: maybe need paper id separately
#input newspage filexml, crop all articles that begin on this page, 
#write them in outfolder. (maybe name outfolder by pagename
def write_articles(n_consts, filexml, filejp2s, outfolder, debug=False):
    for article in get_article_list(filexml):
        missing_pages = []
        id = get_article_id(article)
        article_page_ids = sorted(get_article_pages(article))
        print('aricle_page_ids:', article_page_ids)
        for i, a_page in enumerate(get_article_box_lists(article)):
            print('write_articles: ',
                  list(enumerate(get_article_box_lists(article))))
            page = article_page_ids[i]
            print('page:', page)
            filejp2 = str(page) + '.jp2'
            print('filejp2, jp2s:', filejp2, filejp2s)
            if filejp2 not in filejp2s:
                print('added missing page')
                missing_pages.append((id, page, a_page))
                continue
            print('read and write crops')
            if debug:
                filejp2 = 'YDNSample/' + filejp2
            jp2 = read_jp2(filejp2)
            for k, box in enumerate(a_page):
                outfile = outfolder + '/' + 'a' + id\
                                    + 'p' + page + 'box' + str(k) + '.jp2'
                write_jp2_box(n_consts, box, jp2, outfile)
                print('\nwrite_articles: outfile, box\n', outfile, box, 
                     '\n\n\n')
        #record missing pages that have content of this article.
        mp_file = outfolder + '/' + 'a' + id + 'missing_pages'
        f = open(mp_file, 'w')
        f.write('(article id, pagenum, box_coordinates on page)\n'\
                 + str(missing_pages))
        f.close()


#for testing:
#n_consts = read_n_consts('YDNSample/')
#filexml = 'YDNSample/1.articles.xml'
#outfolder = '.'

#write_articles(n_consts, filexml, ['1.jp2'], outfolder, debug=True)





'''change directory, taken from
http://stackoverflow.com/questions/431684/how-do-i-cd-in-python/24176022#24176022
on 7/19/16'''
from contextlib import contextmanager
import os

@contextmanager
def cd(newdir):
    prevdir = os.getcwd()
    os.chdir(os.path.expanduser(newdir))
    try:
        yield
    finally:
        os.chdir(prevdir)

#create dir for output
def mk_out_dir(path, name):
    out_folder = path + name
    try:
        subprocess.check_call(["mkdir", out_folder])
    except subprocess.CalledProcessError as error:
        print (out_folder, ": mkdir error\n")
        print ("but let's continue")





'''executable'''


#could specify folders by full paths, or commandline arguments
    #actually not cmd line arguments - one-time corpus cropping may assume
    #extra carefulness to open the executable and write stuff there.

#7/19 assume your current directory contains the read folder, and you 
#will write a crop folder in the same directory, with the same folder names
#(so you can collapse the read and write directories by moving their 
#folders into the same directory.)
'''top folders and paths for reading and writing files'''
import subprocess
#top_folder containing (news)papers
source_code_path = subprocess.check_output(['pwd']).decode('utf-8').strip('\n') + '/'
read_top_path = source_code_path + '../'
read_top_folder = 'YDNtest'         #read_top_folder = 'LaCie'
write_top_path = source_code_path + '../'
write_top_folder = read_top_folder + 'crops'



#change directory to top_folder
##NOTE: the cd is probably redundant. I could just ls with the given path.
##remove if efficiency matters.
with cd(read_top_path + read_top_folder):
    #list subfolders (each folder is a newspaper)
    read_paper_folder_ls = subprocess.check_output(['ls']).decode('utf-8').split('\n')
    mk_out_dir(write_top_path, write_top_folder)
    #for each paper_paper_folder, enter it
    for paper_folder in read_paper_folder_ls:
        #print('paper_folder: ', paper_folder)
        with cd(paper_folder):
            #create write_paper_folder for paper.
            write_paper_path = write_top_path + write_top_folder + '/'
            mk_out_dir(write_paper_path, paper_folder)
            write_page_path = write_paper_path + paper_folder + '/'
            #within a paper_paper_folder, check which pages exist
            files =  subprocess.check_output(['ls']).decode('utf-8').split('\n')
            filexmls = [x for x in files if x.find('articles.xml') != -1]
            #print('filexmls: ', filexmls)
            filejp2s = [x.replace('articles.xml', 'jp2') for x in filexmls]
            #use front-most existing page to define standard normalization
            #constants. Use these constants for all pages.
            #(this is because later pages don't include boxes for all 
            #of their articles, so their dimensions won't reveal the 
            #dimensions of the whole page.)
            #print ('write_n_consts input: ', filexmls[0], filejp2s[0])
            n_consts = write_n_consts(filexmls[0], filejp2s[0],
                                      write_paper_path, write_json=False)
            #print('n_consts:', n_consts)
            #for a page in paper_folder
            for filexml in filexmls:
                #no need to read and write n_consts separately.
                #n_consts = read_n_consts(write_paper_path)
                #create write_folder for page
                page_folder_title = filexml.replace('xml', 'crops')
                mk_out_dir(write_page_path, page_folder_title)
                #write articles into page_folder
                #print('writing', filexml)
                out_folder = write_page_path + page_folder_title
                write_articles(n_consts, filexml, filejp2s, out_folder)
            #error in changing directories to news paper dir
            #raise Exception("cd failed for news paper dir ", folder,
            #               "\n jump back to top folder")
    #raise Exception("cd failed for read_top_dir",
            #       "\n jump back to starting folder")



