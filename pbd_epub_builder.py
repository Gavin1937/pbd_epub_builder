#!/usr/bin/env python

import re
import json
from bs4 import BeautifulSoup
from ebooklib import epub
from typing import Union
from copy import deepcopy
from pathlib import Path, PurePath


def extract_series_json(seriesjson:Union[str,Path,list,dict]) -> dict:
    raw = None
    if isinstance(seriesjson, str) or isinstance(seriesjson, Path):
        with open(seriesjson, 'r', encoding='utf-8') as file:
            raw = json.load(file)
    if isinstance(seriesjson, dict):
        raw = [seriesjson]
    elif isinstance(seriesjson, list):
        raw = []
        if isinstance(seriesjson[0], str):
            for j in seriesjson:
                with open(j, 'r', encoding='utf-8') as file:
                    raw += json.load(file)
        elif isinstance(seriesjson[0], dict):
            raw = [*seriesjson]
    
    
    output = {
        'author_name': None,
        'series_id': None,
        'series_title': None,
        'novels': dict(),
    }
    
    # extract series info
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
    'parse txt novel content & return BeautifulSoup Object'
    
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
    novel_title_p = html.new_tag('p')
    if novel_index != -1:
        novel_title_p.string = f'{novel_index}. {seriesjson["novels"][novel_id]["novel_title"]}'
    else:
        novel_title_p.string = f'{seriesjson["novels"][novel_id]["novel_title"]}'
    meta_section.append(novel_title_p)
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


def generate_epub(seriesjson:Union[str,Path,list,dict], data_path:Union[str,Path], output_path:Union[str,Path], **kwargs):
    '''
    kwargs:
        use_idx     => bool, whether to add numerical index before novel title
    '''
    
    if isinstance(output_path, str):
        output_path = Path(output_path)
    if not output_path.exists():
        raise ValueError('Input "output_path" does not exists.')
    if isinstance(data_path, str):
        data_path = Path(data_path)
    if not data_path.exists():
        raise ValueError('Input "data_path" does not exists.')
    
    seriesjson = extract_series_json(seriesjson)
    
    book = epub.EpubBook()
    toc = []
    
    # add metadata
    book.set_title(seriesjson['series_title'])
    book.add_author(seriesjson['author_name'])
    
    # add novels
    for idx,(novel_id,novel_obj) in enumerate(seriesjson['novels'].items(), 1):
        # load novel content txt
        novel_file = data_path/f'{novel_obj["novel_id"]}.txt'
        if not novel_file.exists():
            raise ValueError(f'Novel File "{novel_file}" does not exists.')
        with open(novel_file, 'r', encoding='utf-8') as file:
            if 'use_idx' in kwargs and kwargs['use_idx']:
                novel_content_html = parse_novel_content(seriesjson, novel_id, idx, file.read(), 'image')
            else:
                novel_content_html = parse_novel_content(seriesjson, novel_id, -1, file.read(), 'image')
        novel_epub = epub.EpubHtml(title=novel_obj['novel_title'], file_name=f'{novel_id}.xhtml')
        novel_epub.content = str(novel_content_html)
        book.add_item(novel_epub)
        toc.append(novel_epub)
        
        # load novel images (cover)
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
    book.spine = ['nav', *toc]
    
    epub.write_epub(output_path/f'{seriesjson["series_title"]}.epub', book, {})



