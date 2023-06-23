#!/usr/bin/env python

import re
import json
from sys import argv
from bs4 import BeautifulSoup
from ebooklib import epub
from typing import Union, Iterable
from copy import deepcopy
from pathlib import Path, PurePath
from time import time

__all__ = [
    'extract_series_json',
    'parse_novel_content',
    'generate_epub',
    'pdb_epub_builder_help',
]


HELP_MESSAGE = '''
INFO
    Author           - Gavin1937
    Version          - 2023.05.31.v02
    pdb_epub_builder - Build EPUB book for novels downloaded by PixivBatchDownloader(https://github.com/xuejianxianzun/PixivBatchDownloader)

SYNOPSIS
    python3 pdb_epub_builder.py -r ROOT_DIR [-l SERIES_JSON_LIST | -w SERIES_JSON_WILDCARD] -d DATA_PATH -o OUTPUT_PATH OPTIONAL_ARGS
    
    you can set pdb_epub_builder.py to an executable file and use:
    ./pdb_epub_builder.py ROOT_DIR [-l SERIES_JSON_LIST | -w SERIES_JSON_WILDCARD] -d DATA_PATH -o OUTPUT_PATH OPTIONAL_ARGS

DESCRIPTION
    Build EPUB book for novels downloaded by PixivBatchDownloader(https://github.com/xuejianxianzun/PixivBatchDownloader).
    This tool provides a more structure epub build compare to PixivBatchDownloader's epub generator.
    You will need to download the novel|series by "Crawl series of novels" first,
    and then download crawled result (seriesjson) by "export results".

REQUIREMENTS
    * EbookLib            >= 0.18
    * beautifulsoup4      >= 4.12.2
    * lxml                >= 4.9.2
    
    install with `pip install -r requirements.txt`

ARGUMENTS
    -r ROOT_DIR                 path to root directory of novel content, novel images, and seriesjson files
    
    -l SERIES_JSON_LIST         input a list of series json
                                you cannot use this option with -w
                                SERIES_JSON_LIST        a list of relative path to seriesjson files
    
    -w SERIES_JSON_WILDCARD     input a string wild card to match seriesjson files
                                you cannot use this option with -l
                                SERIES_JSON_WILDCARD    a single string of relative path with wild card to seriesjson file
                                                        only support wild card charater "*", represents zero or more characters
    
    -d DATA_PATH                input a relative path to directory contains all the txt file and images
    
    -o OUTPUT_PATH              input an output directory path

OPTIONAL ARGUMENTS
    -idx                        flag to indicate whether to add numerical index before novel title (default False)
    
    -title TITLE                string template to overwrite & customize series title inside epub.
                                if not supplied, this script will use "%SERIES_TITLE%" by default.
                                series_title is picked from "series_title" field in seriesjson, if exists.
                                if it does not exist, we will pick the "novel_title" field of the first novel in the list.
    
    -file FILENAME              string template to output & customize epub filename.
                                if not supplied, this script will use "[%AUTHOR_NAME%] %SERIES_TITLE%.epub" by default
    
    -cover COVER_FILENAME       string, relative path to cover image file inside data folder. Default None.
                                default use cover image of the first novel in the series.
    
    -v | --verbose              flag to enable verbose mode

STRING TEMPLATE
    %AUTHOR_NAME%               string author_name
    %AUTHOR_ID%                 string author's pixiv id
    %SERIES_TITLE%              string series title
    %SERIES_ID%                 string series id in pixiv
    %TIMESTAMP%                 string unix timestamp to seconds
    
    string template can be applied to arguments "-title" and "-file"

EXAMPLES
    
    build an epub from root directory "data",
    taking all json files and with data_path "data/contents". output to current directory
    
        python3 pbd_epub_builder.py -r data -l 'result1.json' 'result2.json' 'result3.json' -d contents -o ./
    
    build an epub from root directory "data",
    taking all json files matches wild card "result*.json" and with data_path "data/contents".
    output to current directory. and add numerical index before novel title.
    
        python3 pbd_epub_builder.py -r data -w result*.json -d contents -o ./ -idx
    
    build an epub from root directory "data",
    taking all json files matches wild card "result*.json" and with data_path "data/contents".
    output to current directory. and add numerical index before novel title.
    and with specified title & filename template
    
        python3 pbd_epub_builder.py -r data -w result*.json -d contents -o ./ -idx -title '[%AUTHOR_NAME% %AUTHOR_ID%] %SERIES_TITLE% (%TIMESTAMP%)' -file '[%AUTHOR_NAME% %AUTHOR_ID%] %SERIES_TITLE% (%TIMESTAMP%).epub'
'''


def extract_series_json(seriesjson:Union[str,Path,list,dict]) -> dict:
    '''
    extract key info from a single series json file
    
    Parameters:
    -----------
        - seriesjson     => seriesjson (result json dump) from PixivBatchDownloader
    '''
    
    raw = None
    if isinstance(seriesjson, str) or isinstance(seriesjson, Path):
        with open(seriesjson, 'r', encoding='utf-8') as file:
            raw = json.load(file)
    if isinstance(seriesjson, dict):
        raw = [seriesjson]
    elif isinstance(seriesjson, list):
        raw = []
        if isinstance(seriesjson[0], str) or isinstance(seriesjson[0], Path):
            for j in seriesjson:
                with open(j, 'r', encoding='utf-8') as file:
                    raw += json.load(file)
        elif isinstance(seriesjson[0], dict):
            raw = [*seriesjson]
    
    
    output = {
        'author_id': None,
        'author_name': None,
        'series_id': None,
        'series_title': None,
        'novels': dict(),
    }
    
    # extract series info
    output['author_id'] = raw[0]['userId']
    output['author_name'] = raw[0]['user']
    series_id = raw[0]['seriesId']
    if series_id is None: # not a series, just a novel with 1 episode
        series_id = raw[0]['id']
    output['series_id'] = int(series_id)
    series_title = raw[0]['seriesTitle']
    if series_title is None or len(series_title) == 0: # not a series, just a novel with 1 episode
        series_title = raw[0]['title']
    output['series_title'] = series_title
    
    # extract individual novel info
    for novel in raw:
        if 'novelMeta' in novel:
            novel_id = int(novel['novelMeta']['id'])
            novel_title = novel['novelMeta']['title']
            novel_description = novel['novelMeta']['description']
            novel_cover_img_name = f'{novel_id}.{novel["novelMeta"]["coverUrl"].split(".")[-1]}'
            novel_embedded_imgs = None
            if 'embeddedImages' in novel['novelMeta'] and novel['novelMeta']['embeddedImages'] is not None:
                novel_embedded_imgs = deepcopy(novel['novelMeta']['embeddedImages'])
                for k,v in novel['novelMeta']['embeddedImages'].items():
                    img_ext = v.split('.')[-1]
                    img_name = f'{novel_id}-{k}.{img_ext}'
                    novel_embedded_imgs[k] = img_name
            output['novels'][novel_id] = {
                'novel_id': novel_id,
                'novel_title': novel_title,
                'novel_description': novel_description,
                'novel_cover_img_name': novel_cover_img_name,
                'novel_embedded_imgs': novel_embedded_imgs,
            }
    output['novels'] = dict(sorted(output['novels'].items(), key=lambda item:item[0]))
    
    return output


def parse_novel_content(seriesjson:dict, novel_id:int, novel_index:int, content:str, img_path:str):
    '''
    parse txt novel content & return BeautifulSoup Object
    
    Parameters:
    -----------
        - seriesjson     => seriesjson (result json dump) from PixivBatchDownloader
        - novel_id       => novel id of novel content
        - novel_index    => novel index in the series
        - content        => string content of the novel (not html str)
        - img_path       => path to image folder
    '''
    
    img_path = PurePath(img_path)
    html = BeautifulSoup('<div class="novel_content"></div>', 'lxml')
    html.html.unwrap()
    html.body.unwrap()
    
    # parse novel content
    pattern = r'^(.*)\[uploadedimage:(\d+)\](.*)$'
    for line in content.splitlines():
        if len(line) == 0: # line = '\n', convert it to '<br/>
            new_br = html.new_tag('br')
            html.div.append(new_br)
        else:
            new_p = html.new_tag('p')
            match = re.search(pattern, line)
            if match: # add novel embedded image
                new_p.append(match.group(1))
                img_id = match.group(2)
                img_name = seriesjson['novels'][novel_id]['novel_embedded_imgs'][img_id]
                img_path_str = str(img_path/img_name)
                new_img = html.new_tag('img')
                new_img['src'] = img_path_str
                new_p.append(new_img)
                new_p.append(match.group(3))
            else:
                new_p.append(line)
            html.div.append(new_p)
    
    # parse novel cover & description
    meta_section = html.new_tag('div')
    meta_section['class'] = 'novel_meta'
    novel_cover_img = html.new_tag('img')
    novel_cover_img['src'] = str(img_path/seriesjson['novels'][novel_id]['novel_cover_img_name'])
    meta_section.append(novel_cover_img)
    novel_title_h1 = html.new_tag('h1')
    if novel_index != -1:
        novel_title_h1.string = f'{novel_index}. {seriesjson["novels"][novel_id]["novel_title"]}'
    else:
        novel_title_h1.string = f'{seriesjson["novels"][novel_id]["novel_title"]}'
    meta_section.append(novel_title_h1)
    novel_description_p = html.new_tag('p')
    novel_description_p = BeautifulSoup(
        f'<p>{seriesjson["novels"][novel_id]["novel_description"]}</p>',
        'lxml'
    )
    novel_description_p = novel_description_p.find('p')
    meta_section.append(novel_description_p)
    html.select_one('.novel_content').insert_before(meta_section)
    html.select_one('.novel_content').insert_before(html.new_tag('hr'))
    
    return html


def _parse_str_template(seriesjson:dict, template:str) -> str:
    if not isinstance(template, str):
        raise ValueError('Parameter "template" must be a string')
    
    # - %AUTHOR_NAME%     => string author_name
    # - %AUTHOR_ID%       => string author's pixiv id
    # - %SERIES_TITLE%    => string series title
    # - %SERIES_ID%       => string series id in pixiv
    # - %TIMESTAMP%       => string current unix timestamp to seconds
    
    output = deepcopy(template)
    output = output.replace('%AUTHOR_NAME%', seriesjson['author_name'])
    output = output.replace('%AUTHOR_ID%', str(seriesjson['author_id']))
    output = output.replace('%SERIES_TITLE%', seriesjson['series_title'])
    output = output.replace('%SERIES_ID%', str(seriesjson['series_id']))
    output = output.replace('%TIMESTAMP%', str(int(time())))
    
    return output

def _pprint(obj, name:str, indent:int=2):
    try:
        print(name, json.dumps(obj, indent=indent, ensure_ascii=False))
    except:
        print(name, obj)

def generate_epub(root_path:Union[str,Path], seriesjson_list:Union[list,str], data_path:Union[str,Path], output_path:Union[str,Path], **kwargs) -> Path:
    '''
    generate epub from PixivBatchDownloader downloaded novels.
    
    you need to download novel series by "Crawl series of novels" first,
    and then "export results" to get seriesjson.
    
    note that, the order of novels inside a series will be sort base on their novel_id found inside seriesjson file.
    
    Parameters:
    -----------
        - root_path          => root path to working directory
        - seriesjson_list    => list of relative path to seriesjson (result json dump) from PixivBatchDownloader.
                                or, you can use a string wild card to match multiple json files.
                                use wild card character "*" to represents zero or more characters.
                                this function will use pathlib.Path.rglob() to recursive search the root_path with given wild card.
                                in this case, seriesjson_list MUST BE A STRING.
        - data_path          => relative path to directory contains all the txt & images (MUST BE RELATIVE PATH)
        - output_path        => path to output directory
        - kwargs:
            - use_idx        => bool, whether to add numerical index before novel title
            - series_title   => str, if supplied, overwrite series title with this str template inside epub
                                if not supplied, this function will use "%SERIES_TITLE%" by default
                                series_title is picked from "series_title" field in seriesjson, if exists.
                                if it does not exist, we will pick the "novel_title" field of the first novel in the list.
            - filename       => str, if supplied, overwrite output epub filename with this str template
                                if not supplied, this function will use "[%AUTHOR_NAME%] %SERIES_TITLE%.epub" by default
            - cover          => str, relative path to cover image file inside data folder. Default None.
                                default use cover image of the first novel in the series.
            - verbose        => bool, whether to enable verbose mode
    
    String Template:
    ----------------
        - %AUTHOR_NAME%     => string author_name
        - %AUTHOR_ID%       => string author's pixiv id
        - %SERIES_TITLE%    => string series title
        - %SERIES_ID%       => string series id in pixiv
        - %TIMESTAMP%       => string unix timestamp to seconds
        
        string template can be applied to kwargs "series_title" and "filename"
    
    Returns:
    --------
        - Path to output epub file
    '''
    
    if isinstance(root_path, str):
        root_path = Path(root_path)
    if not root_path.exists():
        raise ValueError('Input "root_path" does not exists.')
    data_path = root_path/data_path
    if not data_path.exists():
        raise ValueError('Input "data_path" does not exists.')
    
    if isinstance(output_path, str):
        output_path = Path(output_path)
    if not output_path.exists():
        raise ValueError('Input "output_path" does not exists.')
    
    verbose = False
    if 'verbose' in kwargs:
        verbose = bool(kwargs['verbose'])
    
    tmp = []
    if isinstance(seriesjson_list, list):
        for series in seriesjson_list:
            if (isinstance(series, str) or isinstance(series, Path)) and (root_path/series).exists():
                tmp.append(root_path/series)
            else:
                raise ValueError('Some relative path in input "seriesjson_list" does not exists.')
    elif isinstance(seriesjson_list, str):
        tmp = [i for i in root_path.rglob(seriesjson_list) if i.is_file() and 'json' in i.suffix]
    else:
        raise ValueError('Input "seriesjson_list" must be a list of relative path.')
    if len(tmp) <= 0:
        raise ValueError('No input "seriesjson_list" is valid.')
    seriesjson = extract_series_json(tmp)
    del tmp
    if verbose:
        _pprint(seriesjson, 'seriesjson =')
    
    
    book = epub.EpubBook()
    toc = []
    
    # add metadata
    if 'series_title' in kwargs and kwargs['series_title'] is not None:
        book.set_title(_parse_str_template(seriesjson, kwargs['series_title']))
    else:
        book.set_title(seriesjson['series_title'])
    book.add_author(seriesjson['author_name'])
    
    # add series cover
    cover_file:Path = None
    cover_content:bytes = None
    if 'cover' in kwargs and kwargs['cover'] is not None:
        cover_file = data_path/kwargs['cover']
    if cover_file is None or not cover_file.exists():
        novel_id,novel_obj = list(seriesjson['novels'].items())[0]
        cover_img_name = novel_obj['novel_cover_img_name']
        cover_file = data_path/cover_img_name
    with open(cover_file, 'rb') as file:
        cover_content = file.read()
    book.set_cover(
        file_name=f'image/cover-{cover_file.name}',
        content=cover_content,
        create_page=True
    )
    
    # add novels
    for idx,(novel_id,novel_obj) in enumerate(seriesjson['novels'].items(), 1):
        # load novel content txt
        novel_file = data_path/f'{novel_obj["novel_id"]}.txt'
        novel_title = None
        if not novel_file.exists():
            raise ValueError(f'Novel File "{novel_file}" does not exists.')
        with open(novel_file, 'r', encoding='utf-8') as file:
            if 'use_idx' in kwargs and kwargs['use_idx']:
                novel_content_html = parse_novel_content(seriesjson, novel_id, idx, file.read(), 'image')
                novel_title = novel_content_html.select_one('.novel_meta h1').getText()
            else:
                novel_content_html = parse_novel_content(seriesjson, novel_id, -1, file.read(), 'image')
                novel_title = novel_obj['novel_title']
        novel_epub = epub.EpubHtml(title=novel_title, file_name=f'{novel_id}.xhtml')
        novel_epub.content = str(novel_content_html)
        book.add_item(novel_epub)
        toc.append(novel_epub)
        
        # load novel images (novel cover)
        cover_img_name = novel_obj['novel_cover_img_name']
        with open(data_path/cover_img_name, 'rb') as file:
            cover_image_content = file.read()
        book.add_item(epub.EpubImage(
            uid=cover_img_name.split('.')[0],
            file_name=f'image/{cover_img_name}',
            media_type=f'image/{cover_img_name.split(".")[-1]}',
            content=cover_image_content
        ))
        # load novel images (embedded)
        if novel_obj['novel_embedded_imgs'] is not None:
            for img_id,img_name in novel_obj['novel_embedded_imgs'].items():
                with open(data_path/img_name, 'rb') as file:
                    image_content = file.read()
                book.add_item(epub.EpubImage(
                    uid=img_name.split('.')[0],
                    file_name=f'image/{img_name}',
                    media_type=f'image/{img_name.split(".")[-1]}',
                    content=image_content
                ))
    
    book.toc = toc
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ['cover', 'nav', *toc]
    
    filename = None
    if 'filename' in kwargs and kwargs['filename'] is not None:
        filename = _parse_str_template(seriesjson, kwargs['filename'])
    else:
        filename = _parse_str_template(seriesjson, '[%AUTHOR_NAME%] %SERIES_TITLE%.epub')
    output_path = output_path/filename
    epub.write_epub(output_path, book, {})
    return output_path.resolve()



def pdb_epub_builder_help():
    print(HELP_MESSAGE)

def check_arg(argkey:Union[str,Iterable], arglen:int, args:list, arg_cursor:int) -> bool:
    is_correct_argkey = None
    have_enough_args = None
    
    if arglen is None or arglen <= 1:
        is_correct_argkey = lambda ak: (args[arg_cursor] == ak)
    else:
        have_enough_args = len(args) >= (argv_cursor-1+arglen)
        is_correct_argkey = lambda ak: (args[arg_cursor] == ak and have_enough_args)
    
    if isinstance(argkey, str):
        return is_correct_argkey(argkey)
    elif isinstance(argkey, Iterable):
        return any([is_correct_argkey(ak) for ak in argkey])

if __name__ == '__main__':
    try:
        if len(argv) == 1:
            pdb_epub_builder_help()
            exit()
        
        if '-h' in argv or '--help' in argv or 'help' in argv:
            pdb_epub_builder_help()
            exit()
        
        
        arg_keys = [
            '-r','-l','-w',
            '-d','-o',
            '-idx','-title',
            '-file','-cover',
            '-v','--verbose',
        ]
        mandatory_args = {
            'root_path': None,
            'seriesjson_list': None,
            'data_path': None,
            'output_path': None,
        }
        duplication_flags = {
            'seriesjson_flag': False
        }
        optional_args = dict()
        argv_cursor = 1
        
        # parser loop
        while len(argv) > argv_cursor:
            
            # mandatory arguments
            
            if check_arg('-r', 2, argv, argv_cursor):
                argv_cursor += 1
                mandatory_args['root_path'] = argv[argv_cursor]
            
            elif check_arg('-l', None, argv, argv_cursor) and not duplication_flags['seriesjson_flag']:
                mandatory_args['seriesjson_list'] = []
                argv_cursor += 1
                while argv[argv_cursor] not in arg_keys:
                    mandatory_args['seriesjson_list'].append(argv[argv_cursor])
                    argv_cursor += 1
                argv_cursor -= 1
                duplication_flags['seriesjson_flag'] = True
            elif check_arg('-w', 2, argv, argv_cursor) and not duplication_flags['seriesjson_flag']:
                argv_cursor += 1
                mandatory_args['seriesjson_list'] = argv[argv_cursor]
                duplication_flags['seriesjson_flag'] = True
            
            elif check_arg('-d', 2, argv, argv_cursor):
                argv_cursor += 1
                mandatory_args['data_path'] = argv[argv_cursor]
            
            elif check_arg('-o', 2, argv, argv_cursor):
                argv_cursor += 1
                mandatory_args['output_path'] = argv[argv_cursor]
            
            # optional arguments
            
            elif check_arg('-idx', 1, argv, argv_cursor):
                optional_args['use_idx'] = True
            
            elif check_arg('-title', 2, argv, argv_cursor):
                argv_cursor += 1
                optional_args['series_title'] = argv[argv_cursor]
            
            elif check_arg('-file', 2, argv, argv_cursor):
                argv_cursor += 1
                optional_args['filename'] = argv[argv_cursor]
            
            elif check_arg('-cover', 2, argv, argv_cursor):
                argv_cursor += 1
                optional_args['cover'] = argv[argv_cursor]
            
            elif check_arg(['-v','--verbose'], 1, argv, argv_cursor):
                optional_args['verbose'] = True
            
            argv_cursor += 1
        
        
        if 'verbose' in optional_args and optional_args['verbose']:
            _pprint(mandatory_args, 'mandatory_args =')
            _pprint(optional_args, 'optional_args =')
        
        for _,v in mandatory_args.items():
            if v is None:
                print('Missing mandatory arguments.')
                exit(-1)
        
        
        output_file = generate_epub(
            **mandatory_args,
            **optional_args,
        )
        print(f'Create EPUB: {output_file}')
        
    except KeyboardInterrupt:
        print()
        exit(-1)
    except Exception as err:
        print(f'Exception: {err}')
        exit(-1)
    
