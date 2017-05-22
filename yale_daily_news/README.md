#### Yale Daily News Image Segmentation

This script uses [logic from the YDN client side application](http://digital.library.yale.edu/ui/cdm/default/collection/default/viewers/imageViewer/js/imageViewer.js?version=1423204221) to convert 'uc' unit rectangles from ALTO format XML into jp2 coordinates. The script loops over each newspaper issue in `yale_daily_news_data`, converts the rectangles for each image in that directory, and writes each of those cropped images to a new image file.

Usage:

```
cd yale_daily_news
pip install -r requirements.txt

# update `root_data_directory` path, then:
python segment_ydn_images.py
```