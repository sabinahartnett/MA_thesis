"""
CAPP 30122: Course Search Engine Part 1

Sabina Hartnett

"""
# DO NOT REMOVE THESE LINES OF CODE
# pylint: disable-msg=invalid-name, redefined-outer-name, unused-argument, unused-variable

import queue
import json
import sys
import csv
import re
import bs4
import util

INDEX_IGNORE = set(['a', 'also', 'an', 'and', 'are', 'as', 'at', 'be',
                    'but', 'by', 'course', 'for', 'from', 'how', 'i',
                    'ii', 'iii', 'in', 'include', 'is', 'not', 'of',
                    'on', 'or', 's', 'sequence', 'so', 'social', 'students',
                    'such', 'that', 'the', 'their', 'this', 'through', 'to',
                    'topics', 'units', 'we', 'were', 'which', 'will', 'with',
                    'yet'])


def text_clean_lower(str_text):
    ''' 
    Takes a string text and removes the &#160 character (which in 
       divobject.text looks like: r'\xa0'), replaces new line chars 
       with a space and lowers all words
    Inputs:
        str_text: a string object of text.

    Outputs:
        cln_text: a string object of cleaned text.
    '''
    text1 = str_text.replace(u'\xa0', u' ')
    text2 = text1.replace(u'\n', u' ')
    cln_text = text2.lower()

    return cln_text

def find_code_title(div_object):
    '''
    Called by get_course_info: Finds the course code and course 
        title from a beautiful soup div object.
    Inputs:
        div_object: a beautiful soup translate object of text 
            within a div block.

    Outputs:
        list: list[0] is the stripped & cleaned course code
              list[1] is the stripped & cleaned course title.
    '''

    crse_ttl = div_object.find_all('p', class_="courseblocktitle")

    if len(crse_ttl) > 0:
        crse_title = crse_ttl[0].text.replace(u'\xa0', u' ')
        course_code_lst = re.findall(r'\w{4} [0-9]{5,6}', crse_title)
        cln_course_title = re.sub(r'\w{4} [0-9]{5,6}', '', crse_title)

        if len(course_code_lst) == 1:
            course_code = course_code_lst[0]
        else:
            print("Warning: Multiple Course Codes processed as a single")
            course_code=course_code_lst[0]

    elif len(crse_ttl) == 0:
    #then there is no course title - nothing should be entered
        course_code = ''
        cln_course_title = ''

    return [course_code, cln_course_title]

def get_course_info(soup_text):
    '''
    Called by find_page_links. Parses a beautiful soup object 
      for course information, entering this information into a dict.

    Inputs:
        soup_text: a beautiful soup object.

    Outputs:
        Dictionary of courses {course code: course title & description, ...}.
    '''
    dict_courses = {}

    div_blocks = soup_text.find_all('div')
    # each div is a course (incl. title, description, subsequences)
    for div in div_blocks:
        #note: subsequences will also be included in div_blocks and passed
        #  through this for loop (which adds their individual course info)

        course_code = find_code_title(div)[0]
        course_title = find_code_title(div)[1]
        
        course_descs = div.find_all('p', class_="courseblockdesc")

        cln_course_desc = ''

        if len(course_descs) > 0:
            for desc in course_descs:
                cln_course_desc += text_clean_lower(desc.text)

        if course_code in dict_courses.keys() and course_code != '':
            dict_courses[course_code].append(course_title + cln_course_desc)
        elif course_code not in dict_courses.keys() and course_code != '':
            dict_courses[course_code] = [(course_title + cln_course_desc)]

        subseqs = util.find_sequence(div)
        if len(subseqs) > 0:
        #grab the course codes of the subsequences and add to dict
        # with the current course title & description
            subs_ttls = []
            for subsq in subseqs:
                
                s_cd = find_code_title(subsq)[0]

                #now include the course descriptions for the 'header' course in
                #  the dict at each of the subsequence locations:
                if s_cd in dict_courses.keys() and s_cd != '':
                    dict_courses[s_cd].append(course_title + cln_course_desc)
                elif s_cd not in dict_courses.keys() and s_cd != '':
                    dict_courses[s_cd] = [(course_title + cln_course_desc)]

    return dict_courses


def ID_split_index(map_dict, course_code, text_block, my_index):
    '''
    mini indexer: maps each unique word in the text_block to it's respective
      course ID

    Inputs:
        map_dict: a dictionary mapping course IDs to course codes.
        course_code: the relevant course code for the text_block.
        text_block: a block of beautiful soup text which is the title and
            description of the relevant course.
        my_index: (dict) the final index produced (mapping words to course IDs)

    Outputs:
        my_index: a dictionary object mapping relevant course IDs
            to words {word: [list, of, IDs], ... }.
    '''

    relevant_ID = 0
    for code, ID in map_dict.items(): 
        if course_code == code: 
            relevant_ID = ID

    text = text_clean_lower(text_block)
    split_text1 = re.findall(r'\w+', text)

    #now we only want unique words:
    split_text = list(set(split_text1))

    for word in split_text:
        if word not in INDEX_IGNORE:
            if word in my_index.keys() and relevant_ID not in my_index[word]:
                my_index[word].append(relevant_ID)
            elif word not in my_index.keys():
                my_index[word] = [relevant_ID]

    return my_index


def find_page_links(start_url, limiting_domain, map_dict, link_queue):
    '''
    Crawl the url passed in and find all links on that page.

    Inputs:
        start_url: the url of the page to collect from.
        limiting domain: the limiting domain (to be sure pages are relevant).
        map_dict: a dictionary mapping course codes to IDs.
        link_queue: the queue of links to be visited.

    Outputs:
        code_courseinfo: Returns the output from get_course_info: dict object
            of courses {course code: course title & description, ...}
    '''

    url_request = util.get_request(start_url)
    read_url = util.read_request(url_request)
    soup_text = bs4.BeautifulSoup(read_url, "html5lib")

    code_courseinfo = get_course_info(soup_text)

    all_urls = soup_text.find_all('a')

    #collect all the links    
    regex_ex = r'<a.href=".+?(?=\<\/a\>)'

    #regex_rtrn is a LIST of strings which are URLs/URL endings
    str_urls = re.findall(regex_ex, str(all_urls))

    clean_lst = []
    for url in str_urls:

        #clean the returned links to be just urls/url endings:
        temp_str = re.sub(r'<a.href="', '', url)
        temp_lst = re.findall(r'.+?(?=\")', temp_str)

        if util.is_absolute_url(temp_lst[0]):
            append_url = temp_lst[0]

        elif not util.is_absolute_url(temp_lst[0]):
            rel_url = util.remove_fragment(temp_lst[0])
            append_url = util.convert_if_relative_url(start_url, rel_url)

        if append_url not in clean_lst and util.is_url_ok_to_follow(append_url, limiting_domain):
            clean_lst.append(append_url)
            link_queue.put(append_url)

    return code_courseinfo

def write_csv(index_words_ID, index_filename):
    '''
    Writes a CSV based on the index separating the course ID and word with
       a bar (|)

    Inputs:
        index_words_ID: a dictionary object mapping relevant course IDs
            to words {word: [list, of, IDs], ... }.

    Creates:
        CSV file of the index.
    '''

    with open(index_filename, mode = 'w', newline = '') as csvfile:
        writing = csv.writer(csvfile)

        writing.writerow(['ID|word'])

        for word, list_IDs in index_words_ID.items():
            for i in range(len(list_IDs)):
                writing = csv.writer(csvfile, delimiter='|')
                writing.writerow([str(list_IDs[i]), word])



def go(num_pages_to_crawl, course_map_filename, index_filename):
    '''
    Crawl the college catalog and generates a CSV file with an index.

    Inputs:
        num_pages_to_crawl: the number of pages to process during the crawl
        course_map_filename: the name of a JSON file that contains the mapping
          course codes to course identifiers
        index_filename: the name for the CSV of the index.

    Outputs:
        CSV file of the index index.
    '''

    starting_url = ("http://www.classes.cs.uchicago.edu/archive/2015/winter"
                    "/12200-1/new.collegecatalog.uchicago.edu/index.html")
    limiting_domain = "classes.cs.uchicago.edu"

    #load in the course_map file
    map_file = open(course_map_filename,)
    crs_ID_d = json.load(map_file)

    #initialize the queue with the starting url
    link_queue = queue.Queue()
    link_queue.put(starting_url)
    already_visited = []

    d_wrds_cds = {}

    #crawl until you reach max pages or until there are no more new links
    while not link_queue.empty() and len(already_visited) < num_pages_to_crawl:
        next_url = link_queue.get()
        if next_url not in already_visited and util.is_url_ok_to_follow(next_url, limiting_domain):
        #then visit the URL:
            
            already_visited.append(next_url)
            
            c_c_info = find_page_links(next_url, limiting_domain, crs_ID_d, link_queue)
            #c_c_info will contain the code and course info from next_url in dict form

            for key, text in c_c_info.items():
            #parse through that info and make it into a dict where {uniqueword: [all, 
            #  IDs, which, feature, that, word]} will update dict: d_wrds_cds
                final_index = ID_split_index(crs_ID_d, key, text[0], d_wrds_cds)
    
    #at this point, either all links or max num pages have been 
    # visited: ready to convert dict to csv

    # ** note: already_visited is a list of all the URLs visited
    
    write_csv(final_index, index_filename)



if __name__ == "__main__":
    usage = "python3 crawl.py <number of pages to crawl>"
    args_len = len(sys.argv)
    course_map_filename = "course_map.json"
    index_filename = "catalog_index.csv"
    if args_len == 1:
        num_pages_to_crawl = 1000
    elif args_len == 2:
        try:
            num_pages_to_crawl = int(sys.argv[1])
        except ValueError:
            print(usage)
            sys.exit(0)
    else:
        print(usage)
        sys.exit(0)

    go(num_pages_to_crawl, course_map_filename, index_filename)
