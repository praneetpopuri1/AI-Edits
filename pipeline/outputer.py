import json
from json_helpers import extract_video_json

def get_segments_edit(name, output, segs):
    with open(output,'r',encoding="utf-8") as f:
        data = f.read()

    start_tag = "</think>"
    end_tag = "sucessfully"

    for i in range(len(segs["segments"])):
        start = data.find(start_tag)
        end = data.find(end_tag)
        seg_json = extract_video_json(data[start:])
        data = data[end:]
        with open(name + "segment" + i + ".json", 'w', encoding='utf-8') as f:
            json.dump(seg_json,f)

get_segments_edit("hasan_edl_","first_three_output.log", "../outputs/hasan_segments.json")
        

#what I need to do, get an edl per segment and then edit out the videos for each segment



    

 

    
