
# Build EPUB book for [novels downloaded by PixivBatchDownloader](https://github.com/xuejianxianzun/PixivBatchDownloader)


## Dependencies

### Python >= 3.8

### Other Dependencies

| Name           | Version   |
|----------------|-----------|
| EbookLib       | >= 0.18   |
| beautifulsoup4 | >= 4.12.2 |
| lxml           | >= 4.9.2  |

Install using command

```sh
pip install -r requirements.txt
```

## CLI Usage

```
INFO
    Author           - Gavin1937
    Version          - 2023.05.31.v01
    pdb_epub_builder - Build EPUB book for novels downloaded by PixivBatchDownloader(https://github.com/xuejianxianzun/PixivBatchDownloader)

SYNOPSIS
    python3 pdb_epub_builder.py ROOT_DIR [-l SERIES_JSON_LIST | -w SERIES_JSON_WILDCARD] -d DATA_PATH -o OUTPUT_PATH -idx
    
    you can set pdb_epub_builder.py to an executable file and use:
    ./pdb_epub_builder.py ROOT_DIR [-l SERIES_JSON_LIST | -w SERIES_JSON_WILDCARD] -d DATA_PATH -o OUTPUT_PATH -idx

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
    ROOT_DIR                    path to root directory of novel content, novel images, and seriesjson files
    
    -l SERIES_JSON_LIST         input a list of series json
                                you cannot use this option with -w
                                SERIES_JSON_LIST        a list of relative path to seriesjson files
    
    -w SERIES_JSON_WILDCARD     input a string wild card to match seriesjson files
                                you cannot use this option with -l
                                SERIES_JSON_WILDCARD    a single string of relative path with wild card to seriesjson file
                                                        only support wild card charater "*", represents zero or more characters
    
    -d DATA_PATH                input a relative path to directory contains all the txt file and images
    
    -o OUTPUT_PATH              input an output directory path
    
    -idx                        [OPTIONAL] flag to indicate whether to add numerical index before novel title (default False)

EXAMPLES
    
    build an epub from root directory "data",
    taking all json files and with data_path "data/contents". output to current directory
    
        python3 pbd_epub_builder.py data -l 'result1.json' 'result2.json' 'result3.json' -d contents -o ./
    
    build an epub from root directory "data",
    taking all json files matches wild card "result*.json" and with data_path "data/contents".
    output to current directory. and add numerical index before novel title.
    
        python3 pbd_epub_builder.py data -w result*.json -d contents -o ./ -idx
```

## API Usage

```py
from pbd_epub_builder import generate_epub

root_path = '/path/to/root_dir/'

seriesjson_list = ['relative_path/to/series2.json', 'relative_path/to/series2.json']
# or
seriesjson_list = 'relative_path/wild_card/to/series*.json'

data_path = 'relative_path/to/data/folder'

output_path = '/path/to/output/folder'

use_idx = False

generate_epub(
    root_path, seriesjson_list,
    data_path, output_path,
    use_idx=use_idx
)
```
